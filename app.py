import os
import re
import io
import csv
import time
import click
import logging
import secrets
import shutil
import subprocess
import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
import paramiko
from flask import (
    Flask, render_template, request, redirect, url_for,
    jsonify, flash, send_file, session, abort
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from flask_socketio import SocketIO
from icmplib import multiping
from openpyxl import Workbook
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash

# ==================== CONFIGURATION ====================

# Load .env file (python-dotenv handles quotes, comments, multi-line)
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Configure logging once — before anything else logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}

# Secret key
_env_secret = os.environ.get('SECRET_KEY')
if _env_secret:
    app.config['SECRET_KEY'] = _env_secret
else:
    app.config['SECRET_KEY'] = secrets.token_hex(32)
    logger.warning('Using ephemeral SECRET_KEY — set SECRET_KEY env var for persistent sessions.')

app.config['SESSION_COOKIE_NAME'] = 'network_admin_session'

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
socketio = SocketIO(app, async_mode='threading')

# Timezone configuration
APP_TIMEZONE = os.environ.get('APP_TIMEZONE', 'UTC')
try:
    app_tz = ZoneInfo(APP_TIMEZONE)
except Exception:
    app_tz = ZoneInfo('UTC')


# ==================== HELPERS ====================

def to_iso_with_tz(dt):
    """Convert a datetime to ISO string in the configured app timezone."""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(app_tz).isoformat()


def format_dt(dt, fmt='%Y-%m-%d %H:%M:%S'):
    """Format a datetime for display in the configured app timezone."""
    if not dt:
        return ''
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(app_tz).strftime(fmt)


# Register Jinja filter
app.jinja_env.filters['format_dt'] = format_dt

PUTTY_CANDIDATES = (
    os.environ.get('PUTTY_PATH'),
    os.path.join(os.path.dirname(__file__), 'tools', 'putty.exe'),
    r'C:\Program Files\PuTTY\putty.exe',
    r'C:\Program Files (x86)\PuTTY\putty.exe',
)

# Regex for valid IPv4
_IPV4_RE = re.compile(
    r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
)


def validate_ipv4(ip_address):
    """Return True if ip_address is a valid IPv4 address string."""
    m = _IPV4_RE.match(ip_address)
    if not m:
        return False
    return all(0 <= int(octet) <= 255 for octet in m.groups())


def find_putty_executable():
    """Find PuTTY from env, bundled tools folder, PATH, or standard install paths."""
    path_putty = shutil.which('putty')
    if path_putty:
        return path_putty
    for candidate in PUTTY_CANDIDATES:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def launch_ssh_terminal(ip_address):
    """Open an interactive SSH terminal on the machine running this Flask app."""
    putty_path = find_putty_executable()
    if putty_path:
        subprocess.Popen([putty_path, '-ssh', ip_address, '-P', '22'])
        return 'PuTTY'

    ssh_path = shutil.which('ssh')
    if ssh_path and os.name == 'nt':
        cmd = f'set /p SSHUSER=SSH user: && "{ssh_path}" !SSHUSER!@{ip_address}'
        subprocess.Popen(
            ['cmd.exe', '/v:on', '/k', cmd],
            creationflags=getattr(subprocess, 'CREATE_NEW_CONSOLE', 0),
        )
        return 'Windows SSH'

    if ssh_path:
        subprocess.Popen([ssh_path, ip_address])
        return 'SSH'

    return None


def parse_int_field(value, default, minimum=None, maximum=None):
    """Parse an optional integer form value with bounds and a safe default."""
    if value in (None, ''):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


DEFAULT_SIGNAL_THRESHOLD_DBM = parse_int_field(
    os.environ.get('DEFAULT_SIGNAL_THRESHOLD_DBM'), -75, -100, -30
)
DEFAULT_LINK_QUALITY_THRESHOLD = parse_int_field(
    os.environ.get('DEFAULT_LINK_QUALITY_THRESHOLD'), 50, 1, 100
)
DEFAULT_SNR_THRESHOLD_DB = parse_int_field(
    os.environ.get('DEFAULT_SNR_THRESHOLD_DB'), 20, 1, 60
)


def is_safe_redirect_url(target):
    """Only allow redirects to relative URLs on the same host."""
    if not target:
        return False
    # Must start with / and must not start with // (protocol-relative)
    return target.startswith('/') and not target.startswith('//')


# ==================== CSRF ====================

def generate_csrf_token():
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token


@app.before_request
def verify_csrf():
    if request.method == 'POST':
        token = session.get('_csrf_token', None)
        form_token = (
            request.form.get('csrf_token')
            or request.headers.get('X-CSRF-Token')
        )
        if not token or not form_token or not secrets.compare_digest(token, form_token):
            abort(400, description='Invalid CSRF token')


# Expose csrf_token() in templates
app.jinja_env.globals['csrf_token'] = generate_csrf_token


# ==================== DATABASE MODELS ====================

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    ip_address = db.Column(db.String(50), unique=True, nullable=False)
    device_type = db.Column(db.String(20), default="other")
    site = db.Column(db.String(80), default="Default Site")
    location = db.Column(db.String(100), default="")
    zone = db.Column(db.String(50), default="")
    monitor_profile = db.Column(db.String(30), default="ping")
    last_status = db.Column(db.String(20), default="Unknown")
    latency = db.Column(db.Float, default=0.0)
    is_monitored = db.Column(db.Boolean, default=True, nullable=False)
    wireless_info = db.Column(db.String(100), default="")
    signal_threshold_dbm = db.Column(db.Integer, default=DEFAULT_SIGNAL_THRESHOLD_DBM)
    link_quality_threshold = db.Column(db.Integer, default=DEFAULT_LINK_QUALITY_THRESHOLD)
    snr_threshold_db = db.Column(db.Integer, default=DEFAULT_SNR_THRESHOLD_DB)
    last_check = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship to history
    history = db.relationship(
        'DeviceHistory', backref='device', lazy=True,
        cascade='all, delete-orphan'
    )
    events = db.relationship(
        'DeviceEvent', backref='device', lazy=True,
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Device {self.name} ({self.ip_address})>'


class DeviceHistory(db.Model):
    __table_args__ = (
        db.Index('ix_device_history_device_id', 'device_id'),
        db.Index('ix_device_history_timestamp', 'timestamp'),
        # Composite index for the monitoring query pattern
        db.Index('ix_device_history_device_timestamp', 'device_id', 'timestamp'),
    )

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    latency = db.Column(db.Float, default=0.0)
    timestamp = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self):
        return f'<History {self.device_id} - {self.status} at {self.timestamp}>'


class DeviceEvent(db.Model):
    __table_args__ = (
        db.Index('ix_device_event_device_timestamp', 'device_id', 'timestamp'),
        db.Index('ix_device_event_event_type', 'event_type'),
        db.Index('ix_device_event_severity', 'severity'),
    )

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    event_type = db.Column(db.String(30), default='Ping', nullable=False)
    severity = db.Column(db.String(20), default='info', nullable=False)
    latency_ms = db.Column(db.Float, nullable=True)
    raw_payload = db.Column(db.Text, nullable=True)
    timestamp = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self):
        return f'<DeviceEvent {self.event_type}/{self.severity} for {self.device_id}>'


class IncidentReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    issue_type = db.Column(db.String(50), nullable=False)
    details = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    device = db.relationship('Device', backref=db.backref('incidents', lazy=True, cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<Incident {self.issue_type} for {self.device_id} at {self.timestamp}>'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    is_admin = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


@login_manager.user_loader
def load_user(user_id):
    # Use db.session.get() — Query.get() is deprecated in SQLAlchemy 2.x
    return db.session.get(User, int(user_id))


# ==================== ROUTES ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            # S1: Prevent open redirect — only allow safe relative URLs
            if next_page and is_safe_redirect_url(next_page):
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    devices = Device.query.order_by(Device.site, Device.zone, Device.name).all()

    total_devices = len(devices)
    online_devices = sum(1 for d in devices if d.last_status == "Online")
    offline_devices = sum(1 for d in devices if d.last_status == "Offline")
    unknown_devices = sum(1 for d in devices if d.last_status == "Unknown")

    # Recent incidents (offline in last 24h)
    last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    last_24h_naive = last_24h.replace(tzinfo=None)
    recent_incidents = DeviceHistory.query.filter(
        DeviceHistory.status == "Offline",
        DeviceHistory.timestamp >= last_24h_naive
    ).order_by(DeviceHistory.timestamp.desc()).limit(10).all()

    # Active issue device IDs: Offline OR recent AP threshold violation (last 30 min)
    last_30m_naive = (datetime.now(timezone.utc) - timedelta(minutes=30)).replace(tzinfo=None)
    recent_incident_device_ids = set(
        r.device_id for r in IncidentReport.query.filter(
            IncidentReport.timestamp >= last_30m_naive
        ).with_entities(IncidentReport.device_id).all()
    )
    active_issue_ids = {
        d.id for d in devices
        if d.last_status == "Offline" or d.id in recent_incident_device_ids
    }

    # Group devices by site and zone so the same deployment can cover locations.
    zones = {}
    for device in devices:
        site_name = device.site if device.site else "Default Site"
        zone_name = device.zone if device.zone else "No Zone"
        group_name = f"{site_name} / {zone_name}"
        if group_name not in zones:
            zones[group_name] = []
        zones[group_name].append(device)

    all_sites = sorted(set((d.site or "Default Site") for d in devices))
    all_zones = sorted(set(d.zone for d in devices if d.zone))

    stats = {
        'total': total_devices,
        'online': online_devices,
        'offline': offline_devices,
        'unknown': unknown_devices,
        'uptime_percent': round(
            (online_devices / total_devices * 100) if total_devices > 0 else 0, 1
        )
    }

    return render_template(
        'dashboard.html',
        devices=devices,
        zones=zones,
        all_sites=all_sites,
        all_zones=all_zones,
        stats=stats,
        recent_incidents=recent_incidents,
        active_issue_ids=active_issue_ids,
        default_signal_threshold_dbm=DEFAULT_SIGNAL_THRESHOLD_DBM,
        default_link_quality_threshold=DEFAULT_LINK_QUALITY_THRESHOLD,
        default_snr_threshold_db=DEFAULT_SNR_THRESHOLD_DB,
    )


@app.route('/add_device', methods=['POST'])
@login_required
def add_device():
    try:
        name = request.form.get('name', '').strip()
        ip_address = request.form.get('ip', '').strip()
        device_type = request.form.get('device_type', 'other')
        site = request.form.get('site', '').strip() or 'Default Site'
        location = request.form.get('location', '').strip()
        zone = request.form.get('zone', '').strip()
        monitor_profile = request.form.get('monitor_profile', '').strip() or 'ping'
        signal_threshold_dbm = parse_int_field(
            request.form.get('signal_threshold_dbm'), DEFAULT_SIGNAL_THRESHOLD_DBM, -100, -30
        )
        link_quality_threshold = parse_int_field(
            request.form.get('link_quality_threshold'), DEFAULT_LINK_QUALITY_THRESHOLD, 1, 100
        )
        snr_threshold_db = parse_int_field(
            request.form.get('snr_threshold_db'), DEFAULT_SNR_THRESHOLD_DB, 1, 60
        )

        if not name:
            flash('Device name is required', 'error')
            return redirect(url_for('dashboard'))

        if not ip_address:
            flash('IP address is required', 'error')
            return redirect(url_for('dashboard'))

        # Extracted IP validation helper
        if not validate_ipv4(ip_address):
            flash('Invalid IP address format', 'error')
            return redirect(url_for('dashboard'))

        existing = Device.query.filter_by(ip_address=ip_address).first()
        if existing:
            flash(f'Device with IP {ip_address} already exists: {existing.name}', 'error')
            return redirect(url_for('dashboard'))

        new_device = Device(
            name=name,
            ip_address=ip_address,
            device_type=device_type,
            site=site,
            location=location,
            zone=zone,
            monitor_profile=monitor_profile,
            signal_threshold_dbm=signal_threshold_dbm,
            link_quality_threshold=link_quality_threshold,
            snr_threshold_db=snr_threshold_db,
            is_monitored=request.form.get('is_monitored', 'on') == 'on',
        )

        db.session.add(new_device)
        db.session.commit()

        flash(
            f'Device "{name}" added successfully to {site} / {zone if zone else "No Zone"}',
            'success',
        )

    except Exception as e:
        db.session.rollback()
        flash(f'Error adding device: {str(e)}', 'error')

    return redirect(url_for('dashboard'))


@app.route('/delete_device/<int:device_id>', methods=['POST'])
@login_required
def delete_device(device_id):
    device = Device.query.get_or_404(device_id)
    db.session.delete(device)
    db.session.commit()
    flash(f'Device {device.name} deleted successfully', 'success')
    return redirect(url_for('dashboard'))


@app.route('/edit_device/<int:device_id>', methods=['GET', 'POST'])
@login_required
def edit_device(device_id):
    device = Device.query.get_or_404(device_id)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        ip_address = request.form.get('ip', '').strip()
        device_type = request.form.get('device_type', 'other')
        site = request.form.get('site', '').strip() or 'Default Site'
        location = request.form.get('location', '').strip()
        zone = request.form.get('zone', '').strip()
        monitor_profile = request.form.get('monitor_profile', '').strip() or 'ping'
        signal_threshold_dbm = parse_int_field(
            request.form.get('signal_threshold_dbm'), DEFAULT_SIGNAL_THRESHOLD_DBM, -100, -30
        )
        link_quality_threshold = parse_int_field(
            request.form.get('link_quality_threshold'), DEFAULT_LINK_QUALITY_THRESHOLD, 1, 100
        )
        snr_threshold_db = parse_int_field(
            request.form.get('snr_threshold_db'), DEFAULT_SNR_THRESHOLD_DB, 1, 60
        )

        if not name:
            flash('Device name is required', 'error')
            return redirect(url_for('edit_device', device_id=device.id))

        if not ip_address:
            flash('IP address is required', 'error')
            return redirect(url_for('edit_device', device_id=device.id))

        # Extracted IP validation helper
        if not validate_ipv4(ip_address):
            flash('Invalid IP address format', 'error')
            return redirect(url_for('edit_device', device_id=device.id))

        existing = Device.query.filter(
            Device.ip_address == ip_address, Device.id != device.id
        ).first()
        if existing:
            flash(f'Device with IP {ip_address} already exists: {existing.name}', 'error')
            return redirect(url_for('edit_device', device_id=device.id))

        device.name = name
        device.ip_address = ip_address
        device.device_type = device_type
        device.site = site
        device.location = location
        device.zone = zone
        device.monitor_profile = monitor_profile
        device.signal_threshold_dbm = signal_threshold_dbm
        device.link_quality_threshold = link_quality_threshold
        device.snr_threshold_db = snr_threshold_db
        device.is_monitored = request.form.get('is_monitored') == 'on'
        db.session.commit()
        flash(f'Device {device.name} updated successfully', 'success')
        return redirect(url_for('dashboard'))

    return render_template('device_edit.html', device=device)


@app.route('/ping_device/<int:device_id>')
@login_required
def ping_device(device_id):
    device = Device.query.get_or_404(device_id)
    try:
        result = poll_device(device)
        db.session.commit()
        emit_status_update([device], datetime.now(timezone.utc))
        if result['status'] == 'Online':
            flash(
                f"Ping {device.ip_address} succeeded ({result['latency']} ms avg)",
                'success',
            )
        else:
            flash(f'Ping {device.ip_address} failed: host unreachable', 'error')
    except Exception as e:
        flash(f'Ping failed for {device.ip_address}: {str(e)}', 'error')
    return redirect(url_for('dashboard'))


@app.route('/api/ping_device/<int:device_id>')
@login_required
def api_ping_device(device_id):
    device = Device.query.get_or_404(device_id)
    try:
        result = poll_device(device)
        db.session.commit()
        emit_status_update([device], datetime.now(timezone.utc))
        return jsonify({
            'success': True,
            'status': result['status'],
            'latency': result['latency'],
            'ip': device.ip_address,
            'name': device.name,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'ip': device.ip_address, 'name': device.name}), 500


@app.route('/ssh_device/<int:device_id>', methods=['GET', 'POST'])
@login_required
def ssh_device(device_id):
    device = Device.query.get_or_404(device_id)
    launcher = launch_ssh_terminal(device.ip_address)
    if launcher:
        flash(f'Opened {launcher} for SSH to {device.ip_address}.', 'success')
    else:
        flash(
            'No SSH terminal found. Install PuTTY, set PUTTY_PATH, place putty.exe in tools, '
            'or enable the Windows OpenSSH Client.',
            'error',
        )
    return redirect(url_for('dashboard'))
    # S4: Sanitize SSH user — strip anything except [a-zA-Z0-9._-]


@app.route('/https_device/<int:device_id>')
@login_required
def https_device(device_id):
    device = Device.query.get_or_404(device_id)
    return redirect(f'https://{device.ip_address}', code=302)


@app.route('/device/<int:device_id>')
@login_required
def device_detail(device_id):
    device = Device.query.get_or_404(device_id)

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    seven_days_ago_naive = seven_days_ago.replace(tzinfo=None)
    history = DeviceHistory.query.filter(
        DeviceHistory.device_id == device_id,
        DeviceHistory.timestamp >= seven_days_ago_naive
    ).order_by(DeviceHistory.timestamp.desc()).all()
    events = DeviceEvent.query.filter(
        DeviceEvent.device_id == device_id,
        DeviceEvent.timestamp >= seven_days_ago_naive
    ).order_by(DeviceEvent.timestamp.desc()).limit(100).all()

    if history:
        online_count = sum(1 for h in history if h.status == "Online")
        uptime_percent = round((online_count / len(history) * 100), 2)
    else:
        uptime_percent = 0

    return render_template(
        'device_detail.html',
        device=device,
        history=history,
        events=events,
        uptime_percent=uptime_percent,
    )


@app.route('/history')
@login_required
def history():
    device_id = request.args.get('device_id', type=int)
    hours = request.args.get('hours', 24, type=int)

    time_ago = datetime.now(timezone.utc) - timedelta(hours=hours)
    time_ago_naive = time_ago.replace(tzinfo=None)
    query = DeviceHistory.query.filter(DeviceHistory.timestamp >= time_ago_naive)

    if device_id:
        query = query.filter(DeviceHistory.device_id == device_id)

    history_records = query.order_by(DeviceHistory.timestamp.desc()).all()
    devices = Device.query.all()

    return render_template(
        'history.html',
        history=history_records,
        devices=devices,
        selected_device=device_id,
        selected_hours=hours,
    )


@app.route('/reports')
@login_required
def reports():
    incidents = IncidentReport.query.order_by(IncidentReport.timestamp.desc()).limit(200).all()
    return render_template('reports.html', incidents=incidents)


@app.route('/simulator')
@login_required
def simulator():
    return render_template('simulator.html')


@app.route('/api/status')
@login_required
def api_status():
    """API endpoint for real-time status updates."""
    devices = Device.query.all()
    last_30m_naive = (datetime.now(timezone.utc) - timedelta(minutes=30)).replace(tzinfo=None)
    incident_ids = set(
        r.device_id for r in IncidentReport.query.filter(
            IncidentReport.timestamp >= last_30m_naive
        ).with_entities(IncidentReport.device_id).all()
    )
    return jsonify({
        'devices': [{
            'id': d.id,
            'name': d.name,
            'ip_address': d.ip_address,
            'device_type': d.device_type,
            'site': getattr(d, 'site', 'Default Site'),
            'status': d.last_status,
            'latency': d.latency,
            'is_monitored': d.is_monitored,
            'monitor_profile': getattr(d, 'monitor_profile', 'ping'),
            'wireless_info': getattr(d, 'wireless_info', ''),
            'last_check': to_iso_with_tz(d.last_check) if d.last_check else None,
            'has_issue': d.last_status == 'Offline' or d.id in incident_ids,
        } for d in devices],
        'timestamp': to_iso_with_tz(datetime.now(timezone.utc)),
    })


@app.route('/api/events')
@login_required
def api_events():
    """Return recent monitoring events, optionally filtered by device."""
    device_id = request.args.get('device_id', type=int)
    limit = min(max(request.args.get('limit', 100, type=int), 1), 500)

    query = DeviceEvent.query
    if device_id:
        query = query.filter(DeviceEvent.device_id == device_id)

    events = query.order_by(DeviceEvent.timestamp.desc()).limit(limit).all()
    return jsonify({
        'events': [{
            'id': e.id,
            'device_id': e.device_id,
            'device_name': e.device.name if e.device else '',
            'event_type': e.event_type,
            'severity': e.severity,
            'latency_ms': e.latency_ms,
            'raw_payload': e.raw_payload,
            'timestamp': to_iso_with_tz(e.timestamp),
        } for e in events],
        'timestamp': to_iso_with_tz(datetime.now(timezone.utc)),
    })


# ==================== EXPORT ====================

# Safety cap for export row count
MAX_EXPORT_ROWS = 50000


@app.route('/export/<what>.<fmt>')
@login_required
def export_report(what, fmt):
    """Export devices, history, or incident reports as xlsx or pdf."""
    if what not in ('devices', 'history', 'reports') or fmt not in ('xlsx', 'pdf'):
        abort(404)

    if what == 'devices':
        devices = Device.query.order_by(Device.site, Device.zone, Device.name).all()
        rows = [{
            'id': d.id,
            'name': d.name,
            'ip_address': d.ip_address,
            'type': d.device_type,
            'site': getattr(d, 'site', 'Default Site'),
            'zone': d.zone,
            'location': d.location,
            'monitor_profile': getattr(d, 'monitor_profile', 'ping'),
            'status': d.last_status,
            'latency': d.latency,
            'wireless': getattr(d, 'wireless_info', ''),
            'signal_threshold_dbm': getattr(d, 'signal_threshold_dbm', -75),
            'link_quality_threshold': getattr(d, 'link_quality_threshold', 50),
            'snr_threshold_db': getattr(d, 'snr_threshold_db', 20),
            'last_check': to_iso_with_tz(d.last_check) if d.last_check else '',
        } for d in devices]
        filename_base = 'devices_report'
    elif what == 'history':
        # P2: Cap export row count to prevent OOM
        history_data = (
            DeviceHistory.query
            .order_by(DeviceHistory.timestamp.desc())
            .limit(MAX_EXPORT_ROWS)
            .all()
        )
        rows = [{
            'id': h.id,
            'device_id': h.device_id,
            'device_name': h.device.name if h.device else '',
            'status': h.status,
            'latency': h.latency,
            'timestamp': h.timestamp.isoformat(),
        } for h in history_data]
        filename_base = 'history_report'
    else:
        report_data = (
            IncidentReport.query
            .order_by(IncidentReport.timestamp.desc())
            .limit(MAX_EXPORT_ROWS)
            .all()
        )
        rows = [{
            'id': r.id,
            'device_id': r.device_id,
            'device_name': r.device.name if r.device else '',
            'ip_address': r.device.ip_address if r.device else '',
            'issue_type': r.issue_type,
            'details': r.details or '',
            'timestamp': r.timestamp.isoformat(),
        } for r in report_data]
        filename_base = 'incident_reports'

    # XLSX using openpyxl
    if fmt == 'xlsx':
        wb = Workbook()
        ws = wb.active
        if rows:
            headers = list(rows[0].keys())
            ws.append(headers)
            for r in rows:
                ws.append([r.get(h, '') for h in headers])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        return send_file(
            bio,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'{filename_base}.xlsx',
        )

    # PDF using ReportLab
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet

    bio = io.BytesIO()
    doc = SimpleDocTemplate(bio, pagesize=letter)
    elements = []
    style_sheet = getSampleStyleSheet()
    elements.append(
        Paragraph(f"{filename_base.replace('_', ' ').title()}", style_sheet['Heading2'])
    )
    elements.append(Spacer(1, 12))

    headers = list(rows[0].keys()) if rows else []
    data = [headers]
    for r in rows:
        data.append([str(r.get(h, '')) for h in headers])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f1628')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))

    elements.append(table)
    doc.build(elements)
    bio.seek(0)
    return send_file(
        bio, mimetype='application/pdf',
        as_attachment=True, download_name=f'{filename_base}.pdf',
    )


# Server-side export form (non-JS fallback)
@app.route('/export_page')
@login_required
def export_page():
    return render_template('export_form.html')


@app.route('/export_submit', methods=['GET', 'POST'])
@login_required
def export_submit():
    what = request.values.get('what')
    fmt = request.values.get('fmt')
    if what not in ('devices', 'history', 'reports') or fmt not in ('xlsx', 'pdf'):
        flash('Invalid export selection', 'error')
        return redirect(url_for('dashboard'))
    return redirect(url_for('export_report', what=what, fmt=fmt))


# ==================== BACKGROUND MONITORING ====================

# Global variable to store monitoring status
monitoring_active = True

# History auto-prune: delete records older than this many days
HISTORY_RETENTION_DAYS = int(os.environ.get('HISTORY_RETENTION_DAYS', 30))
PING_INTERVAL_SECONDS = int(os.environ.get('PING_INTERVAL', 10))
PING_COUNT = int(os.environ.get('PING_COUNT', 3))
PING_TIMEOUT_SECONDS = int(os.environ.get('PING_TIMEOUT', 2))
# Run pruning every N monitoring cycles (each cycle ≈ 10s)
_PRUNE_EVERY_N_CYCLES = max(1, int(3600 / max(PING_INTERVAL_SECONDS, 1)))


def record_status_change(device, new_status, latency, now_utc, last_histories):
    """Record a status change in history.

    Uses pre-fetched last_histories dict to avoid per-device queries (P1).
    """
    last_history = last_histories.get(device.id)

    should_record = False

    if not last_history:
        should_record = True
    else:
        last_ts = last_history.timestamp
        if last_ts is None:
            should_record = True
        else:
            if last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=timezone.utc)
            else:
                last_ts = last_ts.astimezone(timezone.utc)

            if last_history.status != new_status:
                should_record = True
            elif (now_utc - last_ts) > timedelta(minutes=1):
                should_record = True

    if should_record:
        history_entry = DeviceHistory(
            device_id=device.id,
            status=new_status,
            latency=latency,
            timestamp=now_utc,
        )
        db.session.add(history_entry)


def _prune_old_history():
    """Delete monitoring records older than HISTORY_RETENTION_DAYS."""
    if HISTORY_RETENTION_DAYS <= 0:
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=HISTORY_RETENTION_DAYS)
    cutoff_naive = cutoff.replace(tzinfo=None)
    deleted_history = (
        db.session.query(DeviceHistory)
        .filter(DeviceHistory.timestamp < cutoff_naive)
        .delete()
    )
    deleted_events = (
        db.session.query(DeviceEvent)
        .filter(DeviceEvent.timestamp < cutoff_naive)
        .delete()
    )
    deleted = deleted_history + deleted_events
    if deleted:
        db.session.commit()
        logger.info(
            f'Auto-pruned {deleted_history} history records and '
            f'{deleted_events} device events older than {HISTORY_RETENTION_DAYS} days.'
        )


def get_latest_histories(device_ids):
    """Return the newest DeviceHistory row per device id."""
    if not device_ids:
        return {}

    from sqlalchemy import func
    latest_subq = (
        db.session.query(
            DeviceHistory.device_id,
            func.max(DeviceHistory.timestamp).label('max_ts'),
        )
        .filter(DeviceHistory.device_id.in_(device_ids))
        .group_by(DeviceHistory.device_id)
        .subquery()
    )
    latest_records = (
        db.session.query(DeviceHistory)
        .join(
            latest_subq,
            (DeviceHistory.device_id == latest_subq.c.device_id)
            & (DeviceHistory.timestamp == latest_subq.c.max_ts),
        )
        .all()
    )
    return {rec.device_id: rec for rec in latest_records}


def record_device_event(device, event_type, severity, latency, payload, now_utc):
    event = DeviceEvent(
        device_id=device.id,
        event_type=event_type,
        severity=severity,
        latency_ms=latency,
        raw_payload=payload,
        timestamp=now_utc,
    )
    db.session.add(event)


def apply_ping_result(device, is_alive, avg_rtt, now_utc, last_histories):
    new_status = "Online" if is_alive else "Offline"
    new_latency = round(avg_rtt, 2) if is_alive else 0.0
    severity = "info" if is_alive else "down"
    payload = "Ping successful" if is_alive else "Device unreachable or ICMP blocked"

    record_status_change(device, new_status, new_latency, now_utc, last_histories)
    record_device_event(device, "Ping", severity, new_latency if is_alive else None, payload, now_utc)

    device.last_status = new_status
    device.latency = new_latency
    device.last_check = now_utc

    return {'status': new_status, 'latency': new_latency, 'severity': severity}


def poll_device(device):
    """Poll one device and stage database updates for caller commit."""
    now_utc = datetime.now(timezone.utc)
    results = multiping(
        [device.ip_address],
        count=PING_COUNT,
        interval=0.2,
        timeout=PING_TIMEOUT_SECONDS,
        privileged=False,
    )
    result = results[0]
    return apply_ping_result(
        device,
        result.is_alive,
        result.avg_rtt if result.is_alive else 0.0,
        now_utc,
        get_latest_histories([device.id]),
    )


def emit_status_update(devices, now_utc):
    payload = {
        'devices': [{
            'id': d.id,
            'name': d.name,
            'ip_address': d.ip_address,
            'device_type': d.device_type,
            'site': getattr(d, 'site', 'Default Site'),
            'status': d.last_status,
            'latency': d.latency,
            'is_monitored': d.is_monitored,
            'monitor_profile': getattr(d, 'monitor_profile', 'ping'),
            'wireless_info': getattr(d, 'wireless_info', ''),
            'last_check': to_iso_with_tz(d.last_check) if d.last_check else None,
        } for d in devices],
        'timestamp': to_iso_with_tz(now_utc),
    }
    socketio.emit('status_update', payload)


def start_ap_monitoring():
    """Background thread that monitors AP devices via SSH."""
    global monitoring_active
    
    ap_username = os.environ.get('AP_USERNAME')
    ap_password = os.environ.get('AP_PASSWORD')
    
    if not ap_username or not ap_password:
        logger.warning('AP_USERNAME or AP_PASSWORD not set. AP SSH monitoring disabled.')
        return

    logger.info('[*] AP SSH monitoring started...')
    
    while monitoring_active:
        try:
            with app.app_context():
                devices = Device.query.filter(
                    Device.is_monitored.is_(True),
                    or_(
                        Device.monitor_profile == 'wireless_ap',
                        Device.device_type.in_(['ap', 'outdoor_ap']),
                    ),
                ).all()
                
                for device in devices:
                    if not monitoring_active:
                        break
                        
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    try:
                        logger.info(f'Connecting to AP {device.name} ({device.ip_address}) via SSH...')
                        client.connect(device.ip_address, username=ap_username, password=ap_password, timeout=10, disabled_algorithms={'pubkeys': ['rsa-sha2-512', 'rsa-sha2-256']})
                        
                        commands = ["uptime", "iwconfig"]
                        results = []
                        for cmd in commands:
                            stdin, stdout, stderr = client.exec_command(cmd)
                            out = stdout.read().decode('utf-8', errors='ignore').strip()
                            if out:
                                results.append(f"--- {cmd} ---\n{out}")
                                
                        if results:
                            out_combined = "\n".join(results)
                            log_msg = f"\n[{datetime.now(timezone.utc).isoformat()}] AP Stats for {device.name} ({device.ip_address}):\n{out_combined}\n"
                            
                            with open('ap_metrics.log', 'a') as f:
                                f.write(log_msg)
                            logger.info(f'Successfully logged AP metrics for {device.name}')
                            
                            import re
                            mode_match = re.search(r'Mode:([A-Za-z]+)', out_combined)
                            rate_match = re.search(r'Bit Rate=([\d.]+\s*[A-Za-z/]+)', out_combined)
                            signal_match = re.search(r'Signal level[:=]\s*(-\d+\s*dBm)', out_combined)
                            noise_match = re.search(r'Noise level[:=]\s*(-\d+\s*dBm)', out_combined)
                            link_match = re.search(r'Link Quality=([\d/]+)', out_combined)
                            info_parts = []
                            if mode_match:
                                info_parts.append(f"Mode: {mode_match.group(1)}")
                            if rate_match:
                                info_parts.append(f"Rate: {rate_match.group(1)}")
                            if signal_match:
                                info_parts.append(f"Sig: {signal_match.group(1)}")
                            if noise_match:
                                info_parts.append(f"Noise: {noise_match.group(1)}")
                            if link_match:
                                info_parts.append(f"Link: {link_match.group(1)}")
                            if info_parts:
                                device.wireless_info = " | ".join(info_parts)
                                db.session.commit()
                                
                                # Anomaly Detection
                                issue_found = None
                                details = None
                                mode_val = mode_match.group(1).strip().lower() if mode_match else ''
                                sig_val = None
                                noise_val = None
                                rate_val = None
                                signal_threshold = device.signal_threshold_dbm or DEFAULT_SIGNAL_THRESHOLD_DBM
                                link_threshold = device.link_quality_threshold or DEFAULT_LINK_QUALITY_THRESHOLD
                                snr_threshold = device.snr_threshold_db or DEFAULT_SNR_THRESHOLD_DB

                                if rate_match:
                                    rate_number = re.search(r'[\d.]+', rate_match.group(1))
                                    if rate_number:
                                        try:
                                            rate_val = float(rate_number.group(0))
                                        except ValueError:
                                            rate_val = None

                                if noise_match:
                                    try:
                                        noise_val = int(noise_match.group(1).replace('dBm', '').strip())
                                    except ValueError:
                                        noise_val = None
                                
                                if signal_match:
                                    try:
                                        sig_val = int(signal_match.group(1).replace('dBm', '').strip())
                                        if sig_val < signal_threshold:
                                            issue_found = "Low Signal"
                                            details = (
                                                f"Signal dropped to {sig_val} dBm "
                                                f"(threshold {signal_threshold} dBm)"
                                            )
                                    except ValueError:
                                        pass

                                snr_val = (
                                    sig_val - noise_val
                                    if sig_val is not None and noise_val is not None
                                    else None
                                )

                                if snr_val is not None and snr_val < snr_threshold and not issue_found:
                                    issue_found = "Low SNR"
                                    details = f"SNR dropped to {snr_val} dB (threshold {snr_threshold} dB)"
                                
                                if link_match and not issue_found:
                                    link_str = link_match.group(1)
                                    if '/' in link_str:
                                        try:
                                            num, den = link_str.split('/')
                                            link_pct = (int(num) / int(den)) * 100
                                            if link_pct < link_threshold:
                                                master_with_good_rf = (
                                                    mode_val == 'master'
                                                    and sig_val is not None and sig_val >= -70
                                                    and snr_val is not None and snr_val >= 25
                                                    and (rate_val is None or rate_val >= 100)
                                                )
                                                if master_with_good_rf:
                                                    logger.info(
                                                        f"Ignoring master-side Link Quality {link_str} for "
                                                        f"{device.name}; RF is healthy "
                                                        f"(signal {sig_val} dBm, noise {noise_val} dBm, "
                                                        f"SNR {snr_val} dB, rate {rate_val or 'unknown'} Mb/s)."
                                                    )
                                                else:
                                                    issue_found = "Poor Link Quality"
                                                    details = (
                                                        f"Link Quality dropped to {link_str} "
                                                        f"(threshold {link_threshold}/100)"
                                                    )
                                        except (ValueError, ZeroDivisionError):
                                            pass
                                            
                                if issue_found:
                                    thirty_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=30)
                                    thirty_mins_ago_naive = thirty_mins_ago.replace(tzinfo=None)
                                    recent = IncidentReport.query.filter(
                                        IncidentReport.device_id == device.id,
                                        IncidentReport.issue_type == issue_found,
                                        IncidentReport.timestamp >= thirty_mins_ago_naive
                                    ).first()
                                    if not recent:
                                        new_incident = IncidentReport(
                                            device_id=device.id,
                                            issue_type=issue_found,
                                            details=details
                                        )
                                        db.session.add(new_incident)
                                        db.session.commit()
                                        logger.warning(f"Generated IncidentReport for {device.name}: {issue_found} - {details}")
                            
                    except Exception as e:
                        logger.error(f'SSH Error for {device.name} ({device.ip_address}): {e}')
                    finally:
                        client.close()
                        
        except Exception as e:
            logger.error(f'[!] AP Monitoring error: {e}')
            
        # Sleep for 60 seconds (in small increments to allow fast shutdown)
        for _ in range(60):
            if not monitoring_active:
                break
            time.sleep(1)

def start_monitoring():
    """Background thread that continuously monitors all devices."""
    global monitoring_active

    logger.info('[*] Network monitoring started...')
    cycle_count = 0

    with app.app_context():
        while monitoring_active:
            try:
                devices = Device.query.filter_by(is_monitored=True).all()

                if devices:
                    ips = [d.ip_address for d in devices]

                    # Perform multi-ping
                    results = multiping(
                        ips,
                        count=PING_COUNT,
                        interval=0.2,
                        timeout=PING_TIMEOUT_SECONDS,
                        privileged=False,
                    )

                    now_utc = datetime.now(timezone.utc)
                    device_ids = [d.id for d in devices]
                    last_histories = get_latest_histories(device_ids)

                    # Update device status
                    for i, res in enumerate(results):
                        device = devices[i]
                        apply_ping_result(
                            device,
                            res.is_alive,
                            res.avg_rtt if res.is_alive else 0.0,
                            now_utc,
                            last_histories,
                        )

                    db.session.commit()
                    logger.info(
                        f'[OK] Checked {len(devices)} devices at '
                        f'{now_utc.strftime("%H:%M:%S")}'
                    )

                    # Emit real-time update via SocketIO
                    try:
                        emit_status_update(devices, now_utc)
                    except Exception as _e:
                        logger.warning(f'Socket emit error: {_e}')

                # P6: Periodic history auto-pruning
                cycle_count += 1
                if cycle_count % _PRUNE_EVERY_N_CYCLES == 0:
                    _prune_old_history()

                time.sleep(PING_INTERVAL_SECONDS)

            except Exception as e:
                logger.error(f'[!] Monitoring error: {e}')
                db.session.rollback()
                time.sleep(PING_INTERVAL_SECONDS)


# ==================== ADMIN ROUTES ====================

def create_default_user():
    """Create default admin user on first run. ADMIN_PASSWORD is only used at creation time."""
    with app.app_context():
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_pw = os.environ.get('ADMIN_PASSWORD') or secrets.token_urlsafe(16)
            hashed = generate_password_hash(admin_pw)
            new_user = User(
                username='admin', password=hashed,
                email='admin@network.local', is_admin=True,
            )
            db.session.add(new_user)
            db.session.commit()
            logger.info('Default admin user created.')
            print('[OK] Default user created (username: admin).')
            print(f'  Admin password: {admin_pw}')


def ensure_database_schema():
    """Apply lightweight upgrades for existing SQLite/MySQL databases."""
    from sqlalchemy import inspect

    db.create_all()
    inspector = inspect(db.engine)
    if 'device' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('device')}
    with db.engine.begin() as conn:
        if 'site' not in columns:
            conn.exec_driver_sql("ALTER TABLE device ADD COLUMN site VARCHAR(80) DEFAULT 'Default Site'")
        if 'zone' not in columns:
            conn.exec_driver_sql("ALTER TABLE device ADD COLUMN zone VARCHAR(50) DEFAULT ''")
        if 'monitor_profile' not in columns:
            conn.exec_driver_sql("ALTER TABLE device ADD COLUMN monitor_profile VARCHAR(30) DEFAULT 'ping'")
        if 'wireless_info' not in columns:
            conn.exec_driver_sql("ALTER TABLE device ADD COLUMN wireless_info VARCHAR(100) DEFAULT ''")
        if 'signal_threshold_dbm' not in columns:
            conn.exec_driver_sql(
                f"ALTER TABLE device ADD COLUMN signal_threshold_dbm INTEGER DEFAULT {DEFAULT_SIGNAL_THRESHOLD_DBM}"
            )
        if 'link_quality_threshold' not in columns:
            conn.exec_driver_sql(
                f"ALTER TABLE device ADD COLUMN link_quality_threshold INTEGER DEFAULT {DEFAULT_LINK_QUALITY_THRESHOLD}"
            )
        if 'snr_threshold_db' not in columns:
            conn.exec_driver_sql(
                f"ALTER TABLE device ADD COLUMN snr_threshold_db INTEGER DEFAULT {DEFAULT_SNR_THRESHOLD_DB}"
            )
        if 'is_monitored' not in columns:
            conn.exec_driver_sql("ALTER TABLE device ADD COLUMN is_monitored BOOLEAN DEFAULT 1 NOT NULL")


@app.cli.command('network:poll-devices')
@click.option('--include-paused', is_flag=True, help='Poll devices even when monitoring is disabled.')
def poll_devices_command(include_paused):
    """Poll monitored devices once and write history/events."""
    ensure_database_schema()
    query = Device.query
    if not include_paused:
        query = query.filter_by(is_monitored=True)
    devices = query.order_by(Device.site, Device.zone, Device.name).all()

    if not devices:
        click.echo('No devices to poll.')
        return

    ips = [d.ip_address for d in devices]
    results = multiping(
        ips,
        count=PING_COUNT,
        interval=0.2,
        timeout=PING_TIMEOUT_SECONDS,
        privileged=False,
    )
    now_utc = datetime.now(timezone.utc)
    last_histories = get_latest_histories([d.id for d in devices])

    for device, result in zip(devices, results):
        poll_result = apply_ping_result(
            device,
            result.is_alive,
            result.avg_rtt if result.is_alive else 0.0,
            now_utc,
            last_histories,
        )
        click.echo(f"{device.name} ({device.ip_address}): {poll_result['status']} {poll_result['latency']} ms")

    db.session.commit()
    click.echo(f'Polled {len(devices)} device(s).')


@app.route('/admin/history_manage')
@login_required
def admin_history_manage():
    if not getattr(current_user, 'is_admin', False):
        abort(403)
    return render_template('admin_history_manage.html')


def _build_csv_bytes(rows):
    """Build a CSV file in memory and return a BytesIO ready for send_file.

    A7: Uses TextIOWrapper over BytesIO to avoid writing str to bytes stream.
    """
    bio = io.BytesIO()
    text_wrapper = io.TextIOWrapper(bio, encoding='utf-8', newline='')
    writer = csv.writer(text_wrapper)
    writer.writerow(['id', 'device_id', 'device_name', 'status', 'latency', 'timestamp'])
    for h in rows:
        writer.writerow([
            h.id, h.device_id,
            h.device.name if h.device else '',
            h.status, h.latency,
            h.timestamp.isoformat() if h.timestamp else '',
        ])
    text_wrapper.flush()
    text_wrapper.detach()  # Detach so closing bio doesn't close the wrapper
    bio.seek(0)
    return bio


def _build_reports_csv_bytes(rows):
    bio = io.BytesIO()
    text_wrapper = io.TextIOWrapper(bio, encoding='utf-8', newline='')
    writer = csv.writer(text_wrapper)
    writer.writerow(['id', 'device_id', 'device_name', 'ip_address', 'issue_type', 'details', 'timestamp'])
    for r in rows:
        writer.writerow([
            r.id,
            r.device_id,
            r.device.name if r.device else '',
            r.device.ip_address if r.device else '',
            r.issue_type,
            r.details or '',
            r.timestamp.isoformat() if r.timestamp else '',
        ])
    text_wrapper.flush()
    text_wrapper.detach()
    bio.seek(0)
    return bio


@app.route('/admin/clear_reports', methods=['POST'])
@login_required
def admin_clear_reports():
    if not getattr(current_user, 'is_admin', False):
        abort(403)

    backup = request.form.get('backup')
    if backup:
        rows = IncidentReport.query.order_by(IncidentReport.timestamp.desc()).all()
        bio = _build_reports_csv_bytes(rows)
        deleted = db.session.query(IncidentReport).delete()
        db.session.commit()
        if deleted:
            return send_file(
                bio, mimetype='text/csv',
                as_attachment=True, download_name='incident_reports_backup.csv',
            )
        flash('No reports to backup; report table is already empty.', 'success')
        return redirect(url_for('reports'))

    deleted = db.session.query(IncidentReport).delete()
    db.session.commit()
    flash(f'Deleted {deleted} incident report records.', 'success')
    return redirect(url_for('reports'))


@app.route('/admin/clear_history', methods=['POST'])
@login_required
def admin_clear_history():
    if not getattr(current_user, 'is_admin', False):
        abort(403)

    action = request.form.get('action')
    backup = request.form.get('backup')

    if action == 'clear_all':
        confirm = request.form.get('confirm')
        if not confirm:
            count = db.session.query(DeviceHistory).count()
            return render_template(
                'confirm_delete.html', count=count, action='clear_all'
            )

        if backup:
            rows = DeviceHistory.query.order_by(DeviceHistory.timestamp.desc()).all()
            if rows:
                bio = _build_csv_bytes(rows)
                db.session.query(DeviceHistory).delete()
                db.session.commit()
                return send_file(
                    bio, mimetype='text/csv',
                    as_attachment=True, download_name='history_backup_all.csv',
                )
            else:
                db.session.query(DeviceHistory).delete()
                db.session.commit()
                flash('No history to backup; performed delete.', 'success')
                return redirect(url_for('dashboard'))

        deleted = db.session.query(DeviceHistory).delete()
        db.session.commit()
        flash(f'Deleted {deleted} history records.', 'success')
        return redirect(url_for('dashboard'))

    elif action == 'clear_range':
        start = request.form.get('start')
        end = request.form.get('end')
        if not start or not end:
            flash('Start and end are required for range deletion.', 'error')
            return redirect(url_for('admin_history_manage'))
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
        except Exception:
            flash('Invalid date format. Use the picker.', 'error')
            return redirect(url_for('admin_history_manage'))

        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=app_tz)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=app_tz)
        start_utc = start_dt.astimezone(timezone.utc).replace(tzinfo=None)
        end_utc = end_dt.astimezone(timezone.utc).replace(tzinfo=None)

        confirm = request.form.get('confirm')
        if not confirm:
            count = DeviceHistory.query.filter(
                DeviceHistory.timestamp >= start_utc,
                DeviceHistory.timestamp <= end_utc,
            ).count()
            return render_template(
                'confirm_delete.html', count=count,
                action='clear_range', start=start, end=end,
            )

        if backup:
            rows = (
                DeviceHistory.query
                .filter(
                    DeviceHistory.timestamp >= start_utc,
                    DeviceHistory.timestamp <= end_utc,
                )
                .order_by(DeviceHistory.timestamp.desc())
                .all()
            )
            if rows:
                bio = _build_csv_bytes(rows)
                (
                    db.session.query(DeviceHistory)
                    .filter(
                        DeviceHistory.timestamp >= start_utc,
                        DeviceHistory.timestamp <= end_utc,
                    )
                    .delete()
                )
                db.session.commit()
                return send_file(
                    bio, mimetype='text/csv',
                    as_attachment=True, download_name='history_backup_range.csv',
                )
            else:
                (
                    db.session.query(DeviceHistory)
                    .filter(
                        DeviceHistory.timestamp >= start_utc,
                        DeviceHistory.timestamp <= end_utc,
                    )
                    .delete()
                )
                db.session.commit()
                flash('No history to backup in range; performed delete.', 'success')
                return redirect(url_for('dashboard'))

        deleted = (
            db.session.query(DeviceHistory)
            .filter(
                DeviceHistory.timestamp >= start_utc,
                DeviceHistory.timestamp <= end_utc,
            )
            .delete()
        )
        db.session.commit()
        flash(f'Deleted {deleted} history records between {start} and {end}.', 'success')
        return redirect(url_for('dashboard'))

    else:
        flash('Unknown action', 'error')
        return redirect(url_for('admin_history_manage'))


@app.route('/admin/reset_password', methods=['POST'])
@login_required
def admin_reset_password():
    if not getattr(current_user, 'is_admin', False):
        abort(403)

    username = request.form.get('username', '').strip()
    new_password = request.form.get('password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()

    if not username or not new_password or not confirm_password:
        flash('Username and password fields are required.', 'error')
        return redirect(url_for('admin_history_manage'))

    if new_password != confirm_password:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('admin_history_manage'))

    user = User.query.filter_by(username=username).first()
    if not user:
        flash(f'User "{username}" not found.', 'error')
        return redirect(url_for('admin_history_manage'))

    user.password = generate_password_hash(new_password)
    db.session.commit()
    flash(f'Password reset successfully for user {user.username}.', 'success')
    return redirect(url_for('admin_history_manage'))


# ==================== INITIALIZATION ====================

if __name__ == '__main__':
    with app.app_context():
        ensure_database_schema()
        create_default_user()

        # A8: Accurate startup message — don't claim default password if env overrides it
        admin_pw_display = os.environ.get('ADMIN_PASSWORD')
        print("=" * 60)
        print("[*] Network Monitor Starting...")
        print("=" * 60)
        if admin_pw_display:
            print("Credentials: admin / (set via ADMIN_PASSWORD env var)")
        else:
            print("Credentials: admin / (generated — see output above)")
        print("Access at: http://localhost:5002")
        print("=" * 60)

    # Start monitoring in background thread
    monitor_thread = threading.Thread(target=start_monitoring, daemon=True)
    monitor_thread.start()

    # Start AP SSH monitoring in background thread
    ap_monitor_thread = threading.Thread(target=start_ap_monitoring, daemon=True)
    ap_monitor_thread.start()

    socketio.run(
        app,
        host=os.environ.get('HOST') or 'localhost',
        port=int(os.environ.get('PORT', 5002)),
        debug=False,
        allow_unsafe_werkzeug=True,
    )
