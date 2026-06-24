# Network Monitor - Architecture Overview

## System Architecture Diagram

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                        User's Browser                        â”‚
â”‚                     (http://localhost:5000)                  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                         â”‚ HTTP Requests
                         â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                      Flask Web Server                        â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚  â”‚                     Routes Layer                       â”‚  â”‚
â”‚  â”‚  /login  /dashboard  /device/<id>  /history  /api/*  â”‚  â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â”‚                       â–¼                                      â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚  â”‚               Authentication Layer                     â”‚  â”‚
â”‚  â”‚              (Flask-Login)                             â”‚  â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â”‚                       â–¼                                      â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚  â”‚                Business Logic                          â”‚  â”‚
â”‚  â”‚  - Device Management                                   â”‚  â”‚
â”‚  â”‚  - Status Updates                                      â”‚  â”‚
â”‚  â”‚  - History Recording                                   â”‚  â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                         â”‚
                         â–¼
         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
         â”‚    SQLAlchemy ORM Layer       â”‚
         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                         â”‚
                         â–¼
         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
         â”‚     SQLite Database           â”‚
         â”‚                               â”‚
         â”‚  Tables:                      â”‚
         â”‚  - Device                     â”‚
         â”‚  - DeviceHistory              â”‚
         â”‚  - User                       â”‚
         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                  Background Monitor Thread                   â”‚
â”‚                     (Runs continuously)                      â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚  â”‚  1. Query all devices from database                   â”‚  â”‚
â”‚  â”‚  2. Multi-ping all IPs simultaneously (icmplib)       â”‚  â”‚
â”‚  â”‚  3. Record status changes to DeviceHistory            â”‚  â”‚
â”‚  â”‚  4. Update Device table with latest status            â”‚  â”‚
â”‚  â”‚  5. Sleep 10 seconds                                  â”‚  â”‚
â”‚  â”‚  6. Repeat                                            â”‚  â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                         â”‚
                         â–¼
         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
         â”‚      Network Devices          â”‚
         â”‚                               â”‚
         â”‚  example-device-ip  (Router)        â”‚
         â”‚  example-device-ip (Switch)        â”‚
         â”‚  example-device-ip (AP)            â”‚
         â”‚  ...                          â”‚
         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Data Flow

### 1. User Login Flow
```
Browser â†’ /login â†’ Flask-Login â†’ Authenticate â†’ Session Cookie â†’ Redirect to /dashboard
```

### 2. View Dashboard Flow
```
Browser â†’ /dashboard â†’ @login_required â†’ Query Devices â†’ Render Template â†’ HTML Response
```

### 3. Add Device Flow
```
Browser â†’ POST /add_device â†’ Validate Input â†’ Create Device Record â†’ Save to DB â†’ Redirect
```

### 4. Background Monitoring Flow
```
Loop:
  Query DB for Devices
  â†“
  Multi-ping all IPs (parallel)
  â†“
  Compare with previous status
  â†“
  If changed: Record in DeviceHistory
  â†“
  Update Device.last_status
  â†“
  Commit to DB
  â†“
  Sleep 10 seconds
```

## Database Schema

### Device Table
```sql
CREATE TABLE device (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    ip_address VARCHAR(50) UNIQUE NOT NULL,
    device_type VARCHAR(20) DEFAULT 'other',
    location VARCHAR(100),
    last_status VARCHAR(20) DEFAULT 'Unknown',
    latency FLOAT DEFAULT 0.0,
    last_check DATETIME,
    created_at DATETIME
);
```

### DeviceHistory Table
```sql
CREATE TABLE device_history (
    id INTEGER PRIMARY KEY,
    device_id INTEGER REFERENCES device(id),
    status VARCHAR(20) NOT NULL,
    latency FLOAT DEFAULT 0.0,
    timestamp DATETIME NOT NULL
);
```

### User Table
```sql
CREATE TABLE user (
    id INTEGER PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password VARCHAR(120) NOT NULL,
    email VARCHAR(120),
    is_admin BOOLEAN DEFAULT TRUE,
    created_at DATETIME
);
```

## Component Breakdown

### 1. Flask Application (app.py)
**Responsibilities:**
- Route handling
- Request/response processing
- Template rendering
- Database operations
- Background thread management

**Key Functions:**
- `login()` - Handle user authentication
- `dashboard()` - Main monitoring view
- `add_device()` - Device creation
- `device_detail()` - Individual device view
- `history()` - Historical data view
- `start_monitoring()` - Background monitoring thread

### 2. Templates (templates/*.html)
**login.html:**
- Authentication form
- Styled login interface
- Flash message display

**dashboard.html:**
- Statistics cards
- Device table
- Add device form
- Recent incidents
- Auto-refresh (10s)

**device_detail.html:**
- Device information
- 7-day uptime stats
- Status history table
- Detailed metrics

**history.html:**
- Filterable history view
- Device and time filters
- Complete event log

### 3. Database Layer (SQLAlchemy)
**Models:**
- `Device` - Network device configuration and current state
- `DeviceHistory` - Historical status records
- `User` - User accounts for authentication

**Relationships:**
- Device â†’ DeviceHistory (one-to-many)
- Cascading deletes (removing device removes its history)

### 4. Network Monitoring (icmplib)
**icmplib.multiping():**
- Sends ICMP echo requests
- Handles multiple targets simultaneously
- Returns statistics (is_alive, avg_rtt)
- Non-blocking operation

**Configuration:**
- count: 3 pings per device
- interval: 0.2s between pings
- timeout: 2s per ping
- privileged: False (no root required)

## Security Architecture

### Authentication Flow
```
1. User submits credentials
2. Flask-Login validates against User table
3. Session cookie created
4. @login_required decorator protects routes
5. Session maintained until logout
```

### Current Security Measures
- Session-based authentication
- Login required for all pages except /login
- SQL injection protection via SQLAlchemy ORM
- XSS protection via Jinja2 auto-escaping

### Production Security Requirements
- HTTPS/TLS encryption
- Password hashing (bcrypt/Argon2)
- CSRF tokens
- Rate limiting
- Secure session cookies
- Environment-based secrets

## Performance Characteristics

### Threading Model
- Main thread: Flask web server
- Background thread: Monitoring daemon
- Thread-safe database access via SQLAlchemy

### Database Queries
- Dashboard: 1 query (all devices) + 1 query (recent incidents)
- Device Detail: 1 query (device) + 1 query (history with filter)
- History: 1-2 queries (filtered history + device list)

### Network Performance
- Parallel pings reduce total check time
- 100 devices Ã— 3 pings = ~2-3 seconds total
- 10-second interval allows for scale

### Optimization Opportunities
1. Add database indexes on device_id and timestamp
2. Implement Redis caching for frequently accessed data
3. Paginate history table for large datasets
4. Use connection pooling for database
5. Add CDN for static assets

## Extensibility Points

### Easy Extensions
1. **Add new device types**: Update device_type field options
2. **Custom intervals**: Modify sleep time in monitoring loop
3. **Additional metrics**: Extend Device model with new fields
4. **Theme customization**: Edit CSS variables

### Advanced Extensions
1. **Alert System**: Hook into `record_status_change()` function
2. **API Integration**: Add REST API endpoints
3. **Webhook Support**: Call external services on status changes
4. **Multi-user**: Extend User model with roles/permissions
5. **Device Groups**: Add DeviceGroup model with many-to-many
6. **Advanced Monitoring**: Integrate SNMP, HTTP checks
7. **Reporting**: Generate PDF reports from history data

## Deployment Architecture

### Development
```
Python Development Server (app.run())
â””â”€â”€ Single process
    â””â”€â”€ Main thread + Monitor thread
```

### Production (Recommended)
```
Nginx (Reverse Proxy, SSL)
    â””â”€â”€ Gunicorn (WSGI Server, 4 workers)
        â””â”€â”€ Flask Application
            â””â”€â”€ Monitor Thread (runs in worker 1)
            â””â”€â”€ PostgreSQL Database
```

### High Availability
```
Load Balancer
    â”œâ”€â”€ Server 1: Nginx â†’ Gunicorn â†’ Flask
    â”œâ”€â”€ Server 2: Nginx â†’ Gunicorn â†’ Flask
    â””â”€â”€ Shared PostgreSQL Database
    
Monitor Thread: Runs on Server 1 only (use leader election)
```

## File Organization

```
network_monitor/
â”œâ”€â”€ app.py                  # Main application code
â”œâ”€â”€ requirements.txt        # Dependencies
â”œâ”€â”€ templates/              # HTML templates
â”‚   â”œâ”€â”€ login.html
â”‚   â”œâ”€â”€ dashboard.html
â”‚   â”œâ”€â”€ device_detail.html
â”‚   â””â”€â”€ history.html
â”œâ”€â”€ static/                 # Static assets (none yet)
â”œâ”€â”€ database.db             # SQLite database (created at runtime)
â”œâ”€â”€ README.md               # Documentation
â”œâ”€â”€ QUICKSTART.md           # Quick start guide
â””â”€â”€ .env.example            # Configuration template
```

## Error Handling Strategy

### Application Level
- Try-catch blocks around database operations
- Flash messages for user feedback
- Graceful degradation on monitoring errors

### Database Level
- Transaction rollback on errors
- SQLAlchemy session management
- Connection retry logic

### Network Level
- Timeout handling in icmplib
- Graceful handling of unreachable devices
- Error logging for debugging

## Monitoring & Logging

### Current Logging
- Console output for monitoring thread
- Database write confirmation
- Error messages on exceptions

### Production Logging Recommendations
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('network_monitor.log'),
        logging.StreamHandler()
    ]
)
```

## Technology Decisions

**Why Flask?**
- Lightweight and flexible
- Easy to understand and modify
- Great for small to medium applications
- Excellent documentation

**Why SQLite?**
- Zero configuration
- Single file database
- Perfect for development and small deployments
- Keeps this deployment free of MySQL, PHP, Laravel, and queue-service requirements

**Why icmplib?**
- Pure Python (no external dependencies)
- High-level async API
- Doesn't require root (unprivileged mode)
- Fast parallel pinging

**Why no JavaScript framework?**
- Keeps code simple and maintainable
- Faster initial load
- Easier for non-JS developers to modify
- Vanilla JS is sufficient for features

---

This architecture is designed to be simple enough for one person to understand and maintain, yet robust enough for production use in small to medium networks.
