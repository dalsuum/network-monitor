# Upgrade Guide - Version 2.0

## What's New in Version 2.0

### ðŸŽ¯ Major Features

1. **Zone Support** - Organize devices by zones (Zone A, Zone B, etc.)
2. **Fixed Form Submission** - Add device form now works correctly
3. **Manual Refresh** - Replaced auto-refresh with manual refresh button
4. **Better Device Grouping** - Devices are now grouped and displayed by zone
5. **Zone Autocomplete** - Type-ahead suggestions when entering zones

### ðŸ”§ Bug Fixes

- Fixed: Add device form causing page refresh loop
- Fixed: Devices not being added to database
- Improved: IP address validation
- Improved: Better error messages

## Upgrading from Version 1.0

### For New Installations

Just run the application normally:
```bash
python app.py
```

### For Existing Installations (with existing database)

Run the application normally:
```bash
python app.py
```

The application applies lightweight SQLite schema upgrades automatically on startup. No manual migration script is required.

## Using Zones

### Adding Devices to Zones

1. Click **"+ Add Device"** on the dashboard
2. Fill in device details
3. Enter a **Zone** name (e.g., "Zone A", "Building 1", "Floor 2")
4. Click **Add**

### Zone Features

- **Autocomplete**: When typing a zone name, you'll see suggestions from existing zones
- **Flexible Naming**: Use any naming convention (Zone A/B/C, Floor 1/2/3, Building names, etc.)
- **Grouping**: Dashboard automatically groups devices by zone
- **Optional**: Zones are optional - devices without a zone will appear in "No Zone"

### Example Zone Organization

**By Physical Location:**
- Zone A, Zone B, Zone C
- Building 1, Building 2
- Floor 1, Floor 2, Floor 3

**By Function:**
- Production Network
- Guest Network
- Management Network

**By Department:**
- IT Department
- Sales Department
- Warehouse

## New Dashboard Layout

Devices are now organized in collapsible zone sections:

```
ðŸ“Š Statistics (Total, Online, Offline, Uptime)

ðŸ”„ Refresh | + Add Device

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
Zone A
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
Device | IP | Type | Location | Status | Latency | Actions
...

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
Zone B
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
Device | IP | Type | Location | Status | Latency | Actions
...

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
No Zone
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
(Devices without assigned zone)
```

## Manual Refresh

The auto-refresh feature has been removed to prevent form submission issues. Instead:

- Click the **ðŸ”„ Refresh** button to update device status
- The monitoring thread still runs in the background every 10 seconds
- Just refresh the page manually when you want to see the latest status

## Breaking Changes

None! The upgrade is fully backward compatible:
- Existing devices will work without any zone assigned
- All existing data is preserved
- Database schema is extended, not replaced

## Recommended Workflow

### Initial Setup

1. **Install/Upgrade** the application
2. **Plan your zones** - decide on a naming convention
3. **Add new devices** with zones
4. **Update existing devices** from the Edit Device page

### Daily Use

1. Open dashboard
2. Check status by zone
3. Click ðŸ”„ Refresh to see latest status
4. Click device names for detailed history
5. Add new devices as needed

## Tips

### Bulk Zone Assignment

If you need to assign zones to many existing devices, use the Edit Device page or run a local SQLite update against your private database. Do not publish real device addresses.

### Zone Naming Best Practices

- **Be consistent**: Pick a naming scheme and stick to it
- **Keep it short**: "Zone A" is better than "Building A Zone 1"
- **Use hierarchy if needed**: "B1-F1" for Building 1, Floor 1
- **Match physical layout**: Use names that match your network diagram

## Troubleshooting

### "Column zone does not exist" error

Restart the application so the automatic schema upgrade can run. If the error persists, confirm the app has write access to `instance/database.db`.

### Devices not grouped correctly

- Make sure zone names are exactly the same (case-sensitive)
- Check for extra spaces in zone names
- Refresh the page

### Form still not working

1. Clear browser cache
2. Make sure you're using the latest version of all files
3. Check browser console for JavaScript errors (F12)

## Support

If you encounter any issues:
1. Check this upgrade guide
2. Review the main README.md
3. Check the browser console for errors (F12 â†’ Console tab)
4. Verify all files are updated to version 2.0

---

**Enjoy the new zone feature! Now you can organize your network monitoring by physical location, department, or any way that makes sense for your infrastructure.**
