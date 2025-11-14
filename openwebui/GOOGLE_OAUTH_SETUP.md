# Google OAuth Setup Guide

This guide will help you set up Google sign-in for your OpenWebUI instance.

## Quick Setup (Basic Google OAuth)

### 1. Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Enable the Google+ API (if using older scopes) or just OAuth will work for basic sign-in
4. Go to **APIs & Services** > **Credentials**
5. Click **Create Credentials** > **OAuth 2.0 Client IDs**
6. Choose **Web application**
7. Add authorized redirect URIs:
   - For local development: `http://localhost:3000/oauth/google/callback`
   - For production: `https://yourdomain.com/oauth/google/callback`
8. Copy the **Client ID** and **Client Secret**

### 2. Configure OpenWebUI

Edit your `.env` file and add:

```bash
# Google OAuth Credentials
GOOGLE_CLIENT_ID='your-google-client-id-here'
GOOGLE_CLIENT_SECRET='your-google-client-secret-here'
GOOGLE_REDIRECT_URI='http://localhost:3000/oauth/google/callback'

# OAuth Settings
ENABLE_OAUTH_SIGNUP=true
OAUTH_ALLOWED_DOMAINS='*'  # Allow all domains, or specify: 'company.com'
OAUTH_MERGE_ACCOUNTS_BY_EMAIL=true
```

### 3. Restart OpenWebUI

After updating the `.env` file, restart your OpenWebUI instance:

```bash
# If using Docker
docker-compose down && docker-compose up -d

# If running locally
# Stop the process and start again
```

### 4. Test Google Sign-In

1. Go to your OpenWebUI login page
2. You should now see a "Continue with Google" button
3. Click it to test the Google OAuth flow

## Advanced Setup (Corporate Authentication)

If you want to restrict access to only your company's Google Workspace users and assign roles based on Google Groups, see the existing `CORPORATE_SETUP.md` file for detailed instructions.

## Configuration Options

### OAuth Settings

- `OAUTH_ALLOWED_DOMAINS`: Restrict to specific email domains (e.g., 'company.com')
- `OAUTH_MERGE_ACCOUNTS_BY_EMAIL`: Merge OAuth accounts with existing email accounts
- `ENABLE_OAUTH_SIGNUP`: Allow new user registration via OAuth

### Google-Specific Settings

- `GOOGLE_OAUTH_SCOPE`: OAuth scopes (default: 'openid email profile')
- `GOOGLE_REDIRECT_URI`: Must match the redirect URI in Google Cloud Console

## Troubleshooting

### Common Issues

1. **"Redirect URI mismatch"**
   - Make sure `GOOGLE_REDIRECT_URI` matches exactly what you configured in Google Cloud Console
   - Include the protocol (http/https) and port if applicable

2. **"OAuth provider not configured"**
   - Ensure both `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set
   - Restart the application after setting environment variables

3. **"Access denied"**
   - Check `OAUTH_ALLOWED_DOMAINS` setting
   - Verify the user's email domain is allowed

### Logs

Check the application logs for detailed error messages:

```bash
# Docker logs
docker-compose logs open-webui

# Or check the backend logs specifically
docker-compose logs backend
```

## Security Considerations

1. **Never commit OAuth credentials** to version control
2. **Use HTTPS in production** for the redirect URI
3. **Restrict allowed domains** if you want to limit access
4. **Keep OAuth secrets secure** and rotate them periodically

## Production Deployment

For production deployments:

1. Update `GOOGLE_REDIRECT_URI` to use your production domain with HTTPS
2. Consider using `OAUTH_ALLOWED_DOMAINS` to restrict to your organization
3. Set up proper secret management instead of plain text in `.env`
4. Configure SSL/TLS termination properly

Example production configuration:

```bash
GOOGLE_CLIENT_ID='your-production-client-id'
GOOGLE_CLIENT_SECRET='your-production-client-secret'
GOOGLE_REDIRECT_URI='https://yourdomain.com/oauth/google/callback'
OAUTH_ALLOWED_DOMAINS='yourcompany.com'
```