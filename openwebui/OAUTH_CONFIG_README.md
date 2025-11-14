# OAuth Configuration Management

This system allows you to manage OAuth settings (scopes, regions) through an external JSON configuration file.

## Configuration File

The main configuration file is located at: `oauth_config.json`

### Structure

```json
{
  "zoho": {
    "region": "eu",
    "scopes": [
      "ZohoPeople.employee.ALL",
      "ZohoPeople.forms.READ",
      "ZohoPeople.attendance.ALL",
      "ZohoPeople.leave.READ",
      "ZohoPeople.timetracker.ALL",
      "AaaServer.profile.READ",
      "email"
    ],
    "regions": {
      "us": { "auth_url": "...", "token_url": "...", ... },
      "eu": { "auth_url": "...", "token_url": "...", ... },
      "in": { "auth_url": "...", "token_url": "...", ... },
      "au": { "auth_url": "...", "token_url": "...", ... },
      "jp": { "auth_url": "...", "token_url": "...", ... }
    }
  },
  "google_drive": {
    "scopes": [
      "https://www.googleapis.com/auth/drive.readonly",
      "https://www.googleapis.com/auth/drive.metadata.readonly",
      "https://www.googleapis.com/auth/drive.file",
      "https://www.googleapis.com/auth/userinfo.email",
      "https://www.googleapis.com/auth/userinfo.profile"
    ]
  }
}
```

## Usage

### Changing Zoho Region

1. Edit `oauth_config.json`
2. Change the `zoho.region` value to one of: `us`, `eu`, `in`, `au`, `jp`
3. Reload configuration (see below)
4. Disconnect and reconnect Zoho service

### Changing Scopes

1. Edit `oauth_config.json`
2. Modify the `scopes` array for the desired service
3. Reload configuration (see below)
4. Disconnect and reconnect the service to get new permissions

### Reloading Configuration

**Method 1: API Call**
```bash
curl -X POST http://localhost:8000/api/v1/services/reload-config \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Method 2: Restart Backend**
```bash
./start-backend.sh
```

## Available Zoho Regions

- **US** (`us`): `accounts.zoho.com`
- **EU** (`eu`): `accounts.zoho.eu`
- **India** (`in`): `accounts.zoho.in`
- **Australia** (`au`): `accounts.zoho.com.au`
- **Japan** (`jp`): `accounts.zoho.jp`

## Environment Variables

You can override the config file path:

```bash
export OAUTH_CONFIG_PATH="/path/to/your/oauth_config.json"
```

## Example: Switching to US Region

1. Edit `oauth_config.json`:
```json
{
  "zoho": {
    "region": "us",
    "scopes": ["ZohoPeople.employee.ALL", "email"]
  }
}
```

2. Reload configuration:
```bash
curl -X POST http://localhost:8000/api/v1/services/reload-config \
  -H "Authorization: Bearer YOUR_TOKEN"
```

3. In the UI:
   - Go to Settings > External Tools
   - Click "Disconnect" for Zoho People
   - Click "Connect" to reconnect with new region/scopes

## Troubleshooting

### Configuration Not Loading
- Check file path: `oauth_config.json` should be in the project root
- Check JSON syntax: use a JSON validator
- Check logs for error messages during startup

### Region Change Not Working
- Make sure you disconnected and reconnected the service
- Check that the region exists in the `regions` object
- Verify the new region URLs are correct

### Scopes Not Applied
- Disconnect and reconnect the service after changing scopes
- Some scopes may require admin approval in Zoho
- Check the token response in logs to see actual granted scopes

## Security Notes

- Keep OAuth credentials secure in environment variables
- Don't commit the config file with sensitive data to version control
- Consider restricting the reload endpoint to admin users only