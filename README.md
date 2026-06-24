# Network Monitor - Professional Network Monitoring Web Application

A sleek, production-ready Flask web application for real-time network device monitoring with historical tracking and incident reporting.

## Features

### ðŸŽ¯ Core Functionality
- **Real-time Device Monitoring**: Automated ping checks every 10 seconds using efficient async ICMP
- **Multi-Device Support**: Monitor routers, switches, access points, servers, and other network devices
- **Status Tracking**: Live status updates (Online/Offline) with latency measurements
- **Historical Records**: Complete status change history with timestamps
- **Incident Reporting**: Track and view network incidents over configurable time periods

### ðŸ“Š Dashboard Features
- **Live Statistics**: Total devices, online/offline counts, and overall uptime percentage
- **Device Management**: Add, view, and delete network devices through the web interface
- **Recent Incidents**: Quick view of devices that went offline in the last 24 hours
- **Auto-refresh**: Dashboard automatically refreshes every 10 seconds for real-time updates

### ðŸ” Advanced Monitoring
- **Device Details**: Individual device pages with 7-day uptime statistics and full history
- **Flexible History View**: Filter by device and time period (1 hour to 30 days)
- **Device Categorization**: Organize devices by type (router, switch, AP, server, other)
- **Location Tracking**: Associate devices with physical locations (e.g., "Room A5")

### ðŸŽ¨ Design
- **Modern UI**: Distinctive dark theme with cyberpunk-inspired aesthetics
- **Responsive Layout**: Works seamlessly on desktop and mobile devices
- **Real-time Updates**: Live status indicators with pulsing animations
- **Professional Typography**: Custom font combinations for readability and style

## Use Cases

### Troubleshooting Network Issues
When users report connectivity problems (like "Room A5 keeps disconnecting"), you can:
1. Check the dashboard to see if the AP or switch is offline
2. View the device history to see exactly when it went down
3. Generate reports showing the ISP or management when issues occurred
4. Identify patterns in network outages

### Proactive Monitoring
- Monitor critical infrastructure 24/7
- Get immediate visibility into network health
- Track uptime statistics for SLA compliance
- Identify devices with frequent connectivity issues

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- Network access to devices you want to monitor
- Root/admin privileges may be required for ICMP on some systems

### Quick Start

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Run the Application**
```bash
python app.py
```

3. **Access the Web Interface**
- Open your browser to: `http://localhost:5002`
- Login as `admin` using the `ADMIN_PASSWORD` value from your local `.env` file.

### First-Time Setup

1. **Login** with your local admin password
2. **Add Your First Device**:
   - Click "Add Device" on the dashboard
   - Enter device name (e.g., "FortiGate Firewall")
   - Enter the device management IP address
   - Select device type
   - Optional: Add location information
3. **Monitor**: The system will automatically start monitoring the device

## Configuration

### Security Settings

**IMPORTANT**: Do not commit `.env`, real credentials, logs, or database files.

To create a new user, you can modify the `create_default_user()` function in `app.py` or add users directly to the database.

**Production Security Recommendations**:
- Set `SECRET_KEY` in `.env` to a random secure value
- Keep password hashing enabled
- Use environment variables for sensitive configuration
- Enable HTTPS for production deployment
- Implement rate limiting for login attempts

### Monitoring Interval

The default monitoring interval is 10 seconds. To change this:

Edit line 119 in `app.py`:
```python
time.sleep(10)  # Change to desired interval in seconds
```

### History Retention

By default, all history is retained indefinitely. To implement automatic cleanup:

Add this function to `app.py` and call it periodically:
```python
def cleanup_old_history(days=30):
    """Delete history older than specified days"""
    cutoff = datetime.utcnow() - timedelta(days=days)
    DeviceHistory.query.filter(DeviceHistory.timestamp < cutoff).delete()
    db.session.commit()
```

## Technical Architecture

### Technology Stack
- **Backend**: Flask (Python web framework)
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: Flask-Login
- **Network Monitoring**: icmplib (async ICMP ping library)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript

### Database Schema

**Device Table**
- id, name, ip_address, device_type, location
- last_status, latency, last_check
- created_at

**DeviceHistory Table**
- id, device_id (FK), status, latency
- timestamp

**User Table**
- id, username, password, email
- is_admin, created_at

### Background Monitoring

The application uses a background thread to continuously monitor devices without blocking the web interface. Status changes are recorded in the history table for later analysis.

## API Endpoints

The application includes a JSON API endpoint for integration:

**GET /api/status**
Returns current status of all devices in JSON format:
```json
{
  "devices": [
    {
      "id": 1,
      "name": "Switch A5",
      "ip_address": "example-device-ip",
      "status": "Online",
      "latency": 2.45,
      "last_check": "2026-01-30T10:30:45"
    }
  ],
  "timestamp": "2026-01-30T10:30:45"
}
```

## Troubleshooting

### ICMP Permissions

If you get permission errors when running pings:

**Linux**:
```bash
# Option 1: Run with sudo (not recommended for production)
sudo python app.py

# Option 2: Set capabilities on Python binary
sudo setcap cap_net_raw+ep $(which python3)
```

**Windows**: Run terminal as Administrator

### Port Already in Use

If port 5000 is already in use, change it in `app.py`:
```python
app.run(host='example-device-ip', port=5001, debug=False, threaded=True)
```

### Database Locked Errors

SQLite may have locking issues under heavy load. For production, consider migrating to PostgreSQL or MySQL.

## Production Deployment

### Using Gunicorn (Linux)

```bash
# Install Gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -b example-device-ip:5000 app:app
```

### Using systemd (Linux)

Create `/etc/systemd/system/network-monitor.service`:
```ini
[Unit]
Description=Network Monitor
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/network_monitor
ExecStart=/usr/bin/python3 app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable network-monitor
sudo systemctl start network-monitor
```

### Nginx Reverse Proxy

Example Nginx configuration:
```nginx
server {
    listen 80;
    server_name monitor.example.com;
    
    location / {
        proxy_pass http://example-device-ip:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Advanced Features

### Email Alerts (Future Enhancement)

To add email alerts when devices go offline, you can extend the `record_status_change()` function:

```python
def send_alert_email(device, status):
    # Use smtplib or a service like SendGrid
    pass
```

### Webhook Integration

Add webhook notifications to integrate with Slack, Discord, or other services:

```python
import requests

def send_webhook(device, status):
    webhook_url = "https://hooks.slack.com/your-webhook"
    payload = {
        "text": f"ðŸ”´ {device.name} is now {status}"
    }
    requests.post(webhook_url, json=payload)
```

### Custom Monitoring Checks

Beyond ICMP pings, you can add:
- TCP port checks
- HTTP/HTTPS endpoint monitoring
- SNMP queries
- Custom protocol checks

## Performance Considerations

- **Scalability**: Current design handles ~100 devices comfortably
- **For 100+ devices**: Consider implementing device groups with staggered checks
- **Database**: SQLite is fine for small deployments; use PostgreSQL for 1000+ devices
- **Monitoring Thread**: Single thread is sufficient for most use cases

## Contributing

Suggestions for improvement:
- Add SNMP support for device statistics
- Implement device groups/tags
- Add graphical uptime charts
- Export reports to PDF/Excel
- Multi-user support with role-based access
- Custom alert thresholds per device
- Mobile app companion

## License

This application is provided as-is for educational and production use.

## Support

For issues or questions:
- Check the troubleshooting section
- Review the Flask and icmplib documentation
- Ensure your firewall allows ICMP traffic

---

**Built for network administrators who need reliable, real-time visibility into their infrastructure.**
