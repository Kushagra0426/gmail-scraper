# Gmail API Email Fetcher

This Python script authenticates with Google's Gmail API using OAuth 2.0 and fetches emails from your inbox.

## Prerequisites

- Python 3.7 or higher
- A Google account with Gmail
- Google Cloud Project with Gmail API enabled

## Setup Instructions

### 1. Create a Google Cloud Project and Enable Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click on it and press "Enable"

### 2. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" user type
   - Fill in the required fields (app name, user support email, developer email)
   - Add your email as a test user in the "Test users" section
   - Save and continue
4. Back in "Create OAuth client ID":
   - Application type: "Desktop app"
   - Name: "Gmail API Fetcher" (or any name)
   - Click "Create"
5. Download the credentials:
   - Click the download button (⬇) next to your newly created OAuth 2.0 Client ID
   - Save the file as `credentials.json` in the same directory as `gmail_fetch.py`

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### 4. Run the Script

```bash
python gmail_fetch.py
```

## First Time Authentication

When you run the script for the first time:

1. A browser window will open automatically
2. Sign in with your Google account
3. You may see a warning "Google hasn't verified this app" - click "Advanced" and then "Go to [App Name] (unsafe)"
4. Grant the requested permissions (read-only access to Gmail)
5. The script will save an authentication token in `token.pickle` for future use

## Files Created

- `token.pickle` - Stores your authentication token (keep this secure and private)
- `credentials.json` - OAuth client credentials (keep this secure and private)

**IMPORTANT:** Add both files to `.gitignore` to prevent committing them to version control!

## Script Features

- OAuth 2.0 authentication (secure, token-based)
- Fetches emails from inbox
- Displays email metadata: ID, sender, date, subject, and preview
- Token caching for subsequent runs (no need to re-authenticate each time)
- Automatic token refresh when expired

## Customization

You can modify the `max_results` parameter in the `main()` function to fetch more or fewer emails:

```python
emails = fetch_emails(service, max_results=20)  # Fetch 20 emails instead of 10
```

## Security Notes

- The script uses read-only scope (`gmail.readonly`)
- Never share your `credentials.json` or `token.pickle` files
- Add them to `.gitignore`:
  ```
  credentials.json
  token.pickle
  ```

## Troubleshooting

**Error: "credentials.json not found"**
- Make sure you downloaded the OAuth credentials and saved them as `credentials.json`

**Error: "Access blocked: This app's request is invalid"**
- Ensure you've added your email as a test user in the OAuth consent screen

**Error: "The user has not granted the app"**
- Complete the OAuth flow and grant the necessary permissions

## API Documentation

For more information, see the [Gmail API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python)
