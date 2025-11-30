# Gmail API Email Fetcher with PostgreSQL Storage

This Python script authenticates with Google's Gmail API using OAuth 2.0, fetches emails from your inbox, and stores them in a PostgreSQL database. OAuth tokens are also stored in the database instead of local files.

## Prerequisites

- Python 3.7 or higher
- PostgreSQL database (local or cloud-hosted)
- A Google account with Gmail
- Google Cloud Project with Gmail API enabled

## Setup Instructions

### 1. Create a PostgreSQL Database

Create a new PostgreSQL database for storing emails:

```sql
-- Connect to PostgreSQL
psql -U postgres

-- Create database
CREATE DATABASE gmail_storage;

-- Exit
\q
```

Or use your cloud provider's console (AWS RDS, Google Cloud SQL, Azure Database, etc.)

### 2. Execute Database Schema

Apply the database schema by running the `schema.sql` file:

```bash
# Using psql with connection parameters
psql -h your-host -U your-username -d gmail_storage -f schema.sql

# OR using connection string
psql "postgresql://username:password@host:port/gmail_storage?sslmode=require" -f schema.sql

# For local database
psql -U postgres -d gmail_storage -f schema.sql
```

This will create three tables:
- **oauth_tokens** - Stores OAuth 2.0 credentials
- **emails** - Stores Gmail messages with full content
- **attachments** - Ready for future attachment storage

### 3. Configure Environment Variables

Create a `.env` file in the project directory:

```bash
cp .env.example .env
```

Edit the `.env` file with your database credentials:

```env
# PostgreSQL Database Configuration
DB_HOST=your-database-host.com
DB_PORT=5432
DB_NAME=gmail_storage
DB_USER=your_username
DB_PASSWORD=your_password
DB_SSLMODE=require

# Gmail User Email
GMAIL_USER_EMAIL=your-email@gmail.com
```

**Configuration Notes:**
- For local PostgreSQL: Set `DB_HOST=localhost` and `DB_SSLMODE=disable`
- For cloud databases: Use your provider's hostname and set `DB_SSLMODE=require`

### 4. Create a Google Cloud Project and Enable Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click on it and press "Enable"

### 5. Create OAuth 2.0 Credentials

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
   - Save the file as `credentials.json` in the project directory

### 6. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `google-auth-oauthlib` - OAuth authentication
- `google-auth-httplib2` - HTTP library for Google APIs
- `google-api-python-client` - Gmail API client
- `psycopg2-binary` - PostgreSQL adapter
- `python-dotenv` - Environment variable management

### 7. Run the Script

```bash
python gmail_fetch.py
```

## First Time Authentication

When you run the script for the first time:

1. A browser window will open automatically
2. Sign in with your Google account
3. You may see a warning "Google hasn't verified this app" - click "Advanced" and then "Go to [App Name] (unsafe)"
4. Grant the requested permissions (read-only access to Gmail)
5. The script will save the authentication token **in the PostgreSQL database** (not in a local file)
6. Emails will be fetched and stored in the `emails` table

## What Gets Stored

### OAuth Tokens Table
- Access token and refresh token
- Token expiration time
- OAuth client credentials
- Automatic token refresh

### Emails Table
- Gmail message ID, thread ID
- Subject, sender, recipient, CC, BCC
- Email date and timestamp
- Email body (both text and HTML)
- Gmail labels (INBOX, SENT, etc.)
- Read/unread and starred status
- Email preview snippet

## Script Features

- **OAuth 2.0 authentication** (secure, token-based)
- **Database storage** for tokens (no local pickle files)
- **PostgreSQL storage** for all emails
- **Automatic token refresh** when expired
- **Full email content** (headers, body, metadata)
- **Duplicate prevention** (uses gmail_message_id)
- **Multi-user support** (can store tokens for multiple accounts)

## Querying Stored Emails

Once emails are stored, you can query them using SQL:

```sql
-- View all emails
SELECT sender, subject, date_received
FROM emails
ORDER BY date_received DESC
LIMIT 10;

-- Find unread emails
SELECT sender, subject, snippet
FROM emails
WHERE is_read = FALSE;

-- Search by sender
SELECT subject, date_received
FROM emails
WHERE sender LIKE '%@example.com%';

-- Search by subject
SELECT sender, subject, snippet
FROM emails
WHERE subject ILIKE '%invoice%';

-- Count total emails
SELECT COUNT(*) FROM emails;
```

## Customization

### Fetch More Emails

Edit `gmail_fetch.py` line 421:

```python
emails_count = fetch_and_store_emails(service, db_manager, max_results=50)
```

### Fetch from Different Labels

Edit `gmail_fetch.py` line 303:

```python
results = service.users().messages().list(
    userId='me',
    labelIds=['SENT'],  # Change to SENT, IMPORTANT, DRAFTS, etc.
    maxResults=max_results
).execute()
```

## Security Notes

- The script uses read-only scope (`gmail.readonly`)
- OAuth tokens are stored securely in PostgreSQL
- **Never commit** `credentials.json` or `.env` files to version control
- Use SSL/TLS for database connections (`DB_SSLMODE=require`)
- Add sensitive files to `.gitignore`:
  ```
  credentials.json
  .env
  token.pickle
  ```

## Troubleshooting

### Database Connection Error
- Verify database credentials in `.env` file
- Check if PostgreSQL server is running
- Test connection: `psql "postgresql://user:pass@host:port/dbname"`
- Verify firewall rules allow database connections

### Schema Error
- Make sure you ran `schema.sql` to create tables
- Verify tables exist: `psql -d gmail_storage -c "\dt"`

### OAuth Authentication Failed
- Ensure `credentials.json` exists in project directory
- Check Gmail API is enabled in Google Cloud Console
- Verify OAuth consent screen is configured
- Make sure your email is added as a test user

### Token Expired
- The script automatically refreshes expired tokens
- If refresh fails, delete token from database and re-authenticate:
  ```sql
  DELETE FROM oauth_tokens WHERE user_email = 'your-email@gmail.com';
  ```

### No Emails Found
- Check that your Gmail account has emails in INBOX
- Verify the label specified in the code
- Check Google API quotas

## Files in Project

- `gmail_fetch.py` - Main Python script
- `schema.sql` - PostgreSQL database schema
- `requirements.txt` - Python dependencies
- `.env` - Database configuration (you create this)
- `.env.example` - Environment template
- `credentials.json` - Google OAuth credentials (you download this)

## Database Schema

### oauth_tokens Table
```
- id, user_email, token, refresh_token
- token_uri, client_id, client_secret
- scopes, expiry, created_at, updated_at
```

### emails Table
```
- id, gmail_message_id, thread_id
- subject, sender, recipient, cc, bcc
- date_received, snippet
- body_text, body_html
- labels, is_read, is_starred
- has_attachments, created_at, updated_at
```

### attachments Table
```
- id, email_id, gmail_message_id
- attachment_id, filename, mime_type
- size_bytes, data, created_at
```

## API Documentation

For more information, see:
- [Gmail API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python)
- [Gmail API Reference](https://developers.google.com/gmail/api/reference/rest)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
