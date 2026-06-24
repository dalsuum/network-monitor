# Quick Start Guide

## Get Running in 3 Steps

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

Or use the setup script:
```bash
chmod +x setup.sh
./setup.sh
```

### Step 2: Start the Application
```bash
python app.py
```

You should see:
```
============================================================
ðŸŒ Network Monitor Starting...
============================================================
Credentials: admin / value from ADMIN_PASSWORD in .env
Access at: http://localhost:5002
============================================================
```

### Step 3: Open Your Browser
Navigate to: `http://localhost:5002`

Login with:
- **Username**: admin
- **Password**: value from your local `.env` `ADMIN_PASSWORD`

## Adding Your First Device

1. Click the **"+ Add Device"** button
2. Fill in the form:
   - **Device Name**: "FortiGate Router" (or your device name)
   - **IP Address**: the device management IP
   - **Type**: Select from dropdown (router, switch, ap, server, other)
   - **Location**: "Main Server Room" (optional)
3. Click **"Add"**

The device will appear in the table and monitoring starts automatically!

## Understanding the Dashboard

### Statistics Cards
- **Total Devices**: Number of configured devices
- **Online**: Devices currently responding to pings
- **Offline**: Devices not responding
- **Uptime**: Overall network health percentage

### Device Table
Each row shows:
- **Device Name** (click to see detailed history)
- **IP Address**
- **Type** (router, switch, ap, etc.)
- **Location**
- **Status** (Online/Offline with green/red indicator)
- **Latency** (ping response time in milliseconds)
- **Actions** (Delete button)

### Auto-Refresh
The dashboard automatically refreshes every 10 seconds to show the latest status.

## Viewing Device History

Click on any device name to see:
- 7-day uptime percentage
- Current latency
- Complete status change history
- Exact timestamps of when device went offline/online

## Filtering History

1. Go to **History** in the navigation
2. Use filters to:
   - Select specific device or "All Devices"
   - Choose time period (1 hour to 30 days)
3. Click **"Apply Filters"**

## Example: Troubleshooting Room A5

**Scenario**: Users in Room A5 report internet dropping for ~10 minutes

**Steps**:
1. Add devices to monitor:
   - "Room A5 AP" â†’ IP: example-device-ip
   - "Switch A5" â†’ IP: example-device-ip
   - "Main Router" â†’ IP: example-device-ip

2. Wait for the next disconnect

3. Check Dashboard:
   - If **AP is Offline** but **Switch is Online** â†’ Problem is the AP or cable to AP
   - If **both are Offline** â†’ Problem is upstream (switch or router)
   - If **all are Online** during complaint â†’ Problem might be ISP or Wi-Fi interference

4. Use History page to show management:
   - Filter by "Room A5 AP"
   - Select "Last 7 Days"
   - Export or screenshot the outage times

## Tips for Success

### Best Practices
- Add all critical infrastructure first (router, core switches)
- Use descriptive names: "2nd Floor Switch A" instead of "Switch 1"
- Fill in locations to help troubleshooting
- Check dashboard regularly for offline devices

### Monitoring Strategy
- **High Priority**: Routers, firewalls, core switches â†’ Check these first
- **Medium Priority**: Access layer switches, main APs
- **Low Priority**: Individual endpoints, printers

### What to Monitor
âœ… **Do Monitor**:
- Routers and firewalls
- Network switches
- Wireless access points
- Servers
- Critical infrastructure

âŒ **Don't Monitor**:
- Individual user PCs (use device types for infrastructure)
- Temporary devices
- Guest network devices

## Common Issues

### "Permission denied" when running
**Linux**: 
```bash
sudo python app.py
# Or set capabilities:
sudo setcap cap_net_raw+ep $(which python3)
```

**Windows**: Run Command Prompt as Administrator

### Device shows as "Unknown"
- Wait 10 seconds for first check
- Verify the IP address is correct
- Check firewall isn't blocking ICMP

### Can't access from other computers
Change the host in app.py:
```python
socketio.run(app, host='example-device-ip', port=5002)
```
Then access via the server address and configured port.

## Next Steps

Once you're comfortable with basic monitoring:
- Review the full README.md for advanced features
- Set up production deployment with Gunicorn
- Configure nginx reverse proxy
- Implement custom alerts
- Add more devices to your network

## Need Help?

- Check the main README.md for detailed documentation
- Review troubleshooting section
- Verify network connectivity to devices
- Ensure ICMP (ping) is allowed through firewalls

---

**You're now monitoring your network! ðŸŽ‰**
