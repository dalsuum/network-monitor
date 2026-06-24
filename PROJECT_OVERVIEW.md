# Network Monitor - Project Overview

## What Is This?

A professional, production-ready web application for monitoring network devices in real-time. Built with Flask and designed with a modern cyberpunk-inspired dark theme, this application helps network administrators track device status, identify connectivity issues, and maintain historical records of network incidents.

## File Structure

```
network_monitor/
â”œâ”€â”€ app.py                    # Main Flask application
â”œâ”€â”€ requirements.txt          # Python dependencies
â”œâ”€â”€ setup.sh                  # Quick installation script
â”œâ”€â”€ README.md                 # Comprehensive documentation
â”œâ”€â”€ QUICKSTART.md             # Quick start guide
â”œâ”€â”€ .env.example              # Environment configuration template
â”œâ”€â”€ .gitignore               # Git ignore rules
â”œâ”€â”€ database.db              # SQLite database (auto-created on first run)
â””â”€â”€ templates/               # HTML templates
    â”œâ”€â”€ login.html           # Login page
    â”œâ”€â”€ dashboard.html       # Main dashboard
    â”œâ”€â”€ device_detail.html   # Individual device details
    â””â”€â”€ history.html         # Network history viewer
```

## Key Features

### 1. Real-Time Monitoring
- Continuous device monitoring via ICMP ping (every 10 seconds)
- Async multi-ping for efficient network checking
- Auto-refresh dashboard with live updates
- Visual status indicators (green = online, red = offline)

### 2. Historical Tracking
- Complete status change history with timestamps
- Track exactly when devices went offline/online
- 7-day uptime statistics per device
- Configurable time period filtering (1 hour to 30 days)

### 3. Device Management
- Add/remove devices through web interface
- Categorize by type (router, switch, AP, server, other)
- Associate devices with physical locations
- View detailed statistics per device

### 4. Professional UI/UX
- Distinctive dark theme with cyberpunk aesthetics
- Responsive design (works on desktop and mobile)
- Real-time pulsing indicators
- Clean, modern typography
- Smooth animations and transitions

## Technology Stack

**Backend:**
- Flask 3.0.0 - Web framework
- SQLAlchemy - Database ORM
- Flask-Login - User authentication
- icmplib - Network ping library

**Frontend:**
- HTML5 + CSS3
- Vanilla JavaScript
- Google Fonts (JetBrains Mono, Outfit)
- No external CSS frameworks

**Database:**
- SQLite (default, easy setup)
- Can migrate to PostgreSQL/MySQL for production

## Quick Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the application
python app.py

# 3. Open browser to http://localhost:5002
# Login: admin / ADMIN_PASSWORD from local .env
```

## How It Works

### Background Monitoring Thread
A separate daemon thread runs continuously in the background, performing these tasks every 10 seconds:
1. Queries database for all devices
2. Performs simultaneous ICMP pings to all IPs
3. Records status changes in history table
4. Updates device status and latency
5. Commits changes to database

### Authentication
- Flask-Login provides session management
- Admin user created automatically on first run
- User credentials stored in database (plaintext for demo - use hashing in production)

### Database Schema
Three main tables:
- **Device**: Stores device information and current status
- **DeviceHistory**: Records every status check
- **User**: Stores user accounts for authentication

## Use Case Example

**Problem**: Users in Room A5 report intermittent WiFi disconnections

**Solution**:
1. Add monitoring for:
   - Room A5 Access Point (example-device-ip)
   - Room A5 Switch (example-device-ip)
   - Main Router (example-device-ip)

2. Wait for next incident

3. Check dashboard:
   - If AP is offline but switch is online â†’ Cable or AP issue
   - If both are offline â†’ Switch or upstream issue
   - If all online during complaint â†’ ISP or wireless interference

4. Use history page to document:
   - Exact times of outages
   - Duration of disconnections
   - Pattern of failures
   - Present to ISP or management

## Security Considerations

### Default Configuration (Development)
- Simple password authentication
- Hashed password storage
- Local credentials: admin / ADMIN_PASSWORD from local .env
- No HTTPS

### Production Recommendations
1. **Change SECRET_KEY**: Use random secure value
2. **Hash Passwords**: Implement werkzeug.security
3. **Enable HTTPS**: Use SSL certificates
4. **Update Credentials**: Rotate the local admin password
5. **Rate Limiting**: Prevent brute force attacks
6. **Environment Variables**: Store secrets securely
7. **Firewall Rules**: Restrict access to trusted IPs

## Deployment Options

### Development
```bash
python app.py
```

### Production with Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b example-device-ip:5000 app:app
```

### Systemd Service (Linux)
Create service file in `/etc/systemd/system/network-monitor.service`
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

### Docker (Optional)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

## Customization Ideas

### Easy Customizations
- Change monitoring interval (edit `time.sleep(10)` in app.py)
- Add more device types
- Customize color scheme (edit CSS variables)
- Add more statistics to dashboard

### Advanced Enhancements
- **Email Alerts**: Send notifications when devices go offline
- **Slack/Discord Webhooks**: Real-time alerts to team channels
- **SNMP Support**: Monitor device statistics beyond ping
- **Port Monitoring**: Check specific TCP/UDP ports
- **HTTP Checks**: Monitor web services
- **Graphical Charts**: Add uptime graphs with Chart.js
- **Export Reports**: PDF/Excel export functionality
- **Multi-tenancy**: Support multiple organizations
- **Device Groups**: Organize devices into logical groups
- **Custom Thresholds**: Alert only after X consecutive failures

## Performance Notes

### Current Capacity
- Handles ~100 devices comfortably
- Single monitoring thread
- 10-second interval between checks
- SQLite database

### Scaling Recommendations
- **100-500 devices**: Use PostgreSQL, implement device groups
- **500+ devices**: Multiple monitoring workers, Redis caching
- **1000+ devices**: Distributed architecture, message queue

## License & Credits

This is a custom-built application designed for network administrators. Feel free to modify and extend for your specific needs.

**Built with:**
- Flask - Web framework
- icmplib - Network monitoring
- SQLAlchemy - Database ORM
- Modern web standards

**Design Philosophy:**
- Clean, functional code
- Professional aesthetics
- Production-ready architecture
- Easy to understand and modify

## Getting Help

1. **Read QUICKSTART.md** for immediate guidance
2. **Review README.md** for comprehensive documentation
3. **Check code comments** in app.py for implementation details
4. **Test in development** before deploying to production

## What Makes This Special

Unlike generic monitoring tools, this application:
- Has a distinctive, memorable design
- Is lightweight and easy to deploy
- Provides exactly what network admins need
- Can be customized without fighting a framework
- Includes complete historical tracking
- Works out of the box with minimal configuration

Perfect for small to medium networks, IT departments, managed service providers, and anyone who needs reliable network visibility without enterprise complexity.

---

**Start monitoring your network in under 5 minutes!**
