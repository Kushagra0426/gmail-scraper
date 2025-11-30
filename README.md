# Gmail API Email Fetcher with PostgreSQL Storage

Authenticate with Google's Gmail API using OAuth 2.0, fetch emails from your inbox, store them in PostgreSQL, and process them with automated rules.

## Prerequisites

- Python 3.7 or higher
- PostgreSQL database (local or cloud-hosted)
- A Google account with Gmail
- Google Cloud Project with Gmail API enabled

---

## Initial Setup (One-Time)

### Step 1: Create PostgreSQL Database

Create a new PostgreSQL database for storing emails:

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE gmail_storage;

# Exit
\q
```

Or use your cloud provider's console (AWS RDS, Google Cloud SQL, Azure Database, etc.)

### Step 2: Execute Database Schema

Apply the database schema by running the `schema.sql` file:

```bash
# Using psql with connection parameters
psql -h your-host -U your-username -d gmail_storage -f schema.sql

# OR using connection string
psql "postgresql://username:password@host:port/gmail_storage?sslmode=require" -f schema.sql

# For local database
psql -U postgres -d gmail_storage -f schema.sql
```

This creates three tables:
- **oauth_tokens** - Stores OAuth 2.0 credentials
- **emails** - Stores Gmail messages with full content
- **attachments** - Ready for future attachment storage

### Step 3: Configure Environment Variables

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

### Step 4: Create Google Cloud Project and Enable Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click on it and press "Enable"

### Step 5: Create OAuth 2.0 Credentials

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

### Step 6: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `google-auth-oauthlib` - OAuth authentication
- `google-auth-httplib2` - HTTP library for Google APIs
- `google-api-python-client` - Gmail API client
- `psycopg2-binary` - PostgreSQL adapter
- `python-dotenv` - Environment variable management

---

## How to Run: Email Fetcher

The email fetcher downloads emails from Gmail and stores them in your PostgreSQL database.

### Steps to Fetch Emails

**Step 1: Run the fetcher script**

```bash
python gmail_fetch.py
```

**Step 2: First-time authentication (if prompted)**

When you run the script for the first time:
1. A browser window will open automatically
2. Sign in with your Google account
3. You may see a warning "Google hasn't verified this app"
   - Click "Advanced"
   - Click "Go to [App Name] (unsafe)"
4. Grant the requested permissions (modify Gmail access)
5. The script will save the authentication token in the PostgreSQL database

**Step 3: Wait for completion**

The script will:
- Connect to PostgreSQL database
- Authenticate with Gmail API
- Fetch emails from your inbox
- Store emails in the `emails` table
- Display progress and results

**Output Example:**
```
Gmail API Email Fetcher with PostgreSQL Storage
================================================================================
Successfully connected to PostgreSQL database
Successfully authenticated to Gmail API

Found 10 messages in inbox:
--------------------------------------------------------------------------------

Email ID: 18d4a5b2c9f1e3a7
From: user@example.com
Date: Mon, 15 Jan 2024 10:30:00 +0000
Subject: Meeting Reminder
Preview: Don't forget about our meeting tomorrow at 2 PM...
Stored in database: ✓
--------------------------------------------------------------------------------

Total emails processed and stored: 10
```

### Customization Options

**Fetch more emails:**

Edit `gmail_fetch.py` line 421:
```python
emails_count = fetch_and_store_emails(service, db_manager, max_results=50)
```

**Fetch from different labels:**

Edit `gmail_fetch.py` line 303:
```python
results = service.users().messages().list(
    userId='me',
    labelIds=['SENT'],  # Change to SENT, IMPORTANT, DRAFTS, etc.
    maxResults=max_results
).execute()
```

---

## How to Run: Email Processor

The email processor applies automated rules to emails stored in your database.

### Steps to Process Emails

**Step 1: Ensure emails are in database**

Make sure you've run `gmail_fetch.py` at least once to have emails in the database.

**Step 2: Configure rules**

Edit the `rules.json` file to define your processing rules:

```bash
nano rules.json
# or use your preferred text editor
```

Example rule:
```json
{
  "description": "Mark newsletters as read",
  "predicate": "all",
  "conditions": [
    {
      "field": "from",
      "predicate": "contains",
      "value": "newsletter"
    }
  ],
  "actions": [
    {
      "type": "mark_read"
    }
  ]
}
```

See **EMAIL_PROCESSOR_README.md** for complete rule syntax and examples.

**Step 3: Run the processor**

```bash
python email_processor.py
```

**Step 4: Review results**

The script will:
- Load rules from `rules.json`
- Connect to PostgreSQL database
- Authenticate with Gmail API
- Fetch emails from database
- Evaluate each rule against each email
- Execute actions for matching emails
- Display detailed results

**Output Example:**
```
================================================================================
Email Rule Processor
================================================================================

✓ Loaded 5 rules from rules.json
✓ Connected to PostgreSQL database
✓ Authenticated to Gmail API
✓ Fetched 100 emails from database

✓ Rule matched: 'Mark newsletters as read'
  Email: Weekly Newsletter - January 2024
  From: newsletter@example.com
  Actions:
  ✓ Marked as read: abc123xyz

✓ Rule matched: 'Archive old promotional emails'
  Email: Special Offer - 50% Off!
  From: promo@store.com
  Actions:
  ✓ Marked as read: def456uvw
  ✓ Moved to TRASH: def456uvw

================================================================================
Processing complete: 3 actions executed
================================================================================
```

### Available Rule Options

**Fields:**
- `from` - Email sender
- `to` - Email recipient
- `subject` - Email subject
- `message` - Email body content
- `date_received` - Email date/time

**String Predicates:**
- `contains` - Field contains value
- `does_not_contain` - Field doesn't contain value
- `equals` - Exact match
- `does_not_equal` - Not equal

**Date Predicates:**
- `less_than` - Email newer than X days/months
- `greater_than` - Email older than X days/months

**Actions:**
- `mark_read` - Mark email as read
- `mark_unread` - Mark email as unread
- `move` - Move to mailbox (INBOX, TRASH, etc.)

**Rule Predicates:**
- `all` - All conditions must match (AND)
- `any` - At least one condition must match (OR)

---

## Typical Workflow

### Daily Email Management

```bash
# 1. Fetch new emails from Gmail
python gmail_fetch.py

# 2. Process emails with your rules
python email_processor.py

# 3. Query database to view results (optional)
psql -d gmail_storage -c "SELECT COUNT(*) FROM emails;"
```

### Setting Up Automation

You can automate the workflow with a cron job (Linux/Mac) or Task Scheduler (Windows):

```bash
# Add to crontab (runs every hour)
0 * * * * cd /path/to/HappyFox && python gmail_fetch.py && python email_processor.py
```

---

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

---

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

-- Emails from last week
SELECT sender, subject, date_received
FROM emails
WHERE date_received >= NOW() - INTERVAL '7 days'
ORDER BY date_received DESC;
```

---

## Files in Project

- `gmail_fetch.py` - Fetch and store emails from Gmail
- `email_processor.py` - Process emails based on rules
- `rules.json` - Rule definitions (JSON format)
- `schema.sql` - PostgreSQL database schema
- `requirements.txt` - Python dependencies
- `.env` - Database configuration (you create this)
- `.env.example` - Environment template
- `credentials.json` - Google OAuth credentials (you download this)
- `EMAIL_PROCESSOR_README.md` - Detailed email processor documentation
- `RULES_REFERENCE.md` - Quick reference for rule syntax

---

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

---

## Security Notes

- The script uses `gmail.modify` scope to allow reading emails and performing actions (mark as read/unread, move messages)
- OAuth tokens are stored securely in PostgreSQL database
- **Never commit** `credentials.json` or `.env` files to version control
- Use SSL/TLS for database connections (`DB_SSLMODE=require`)
- Add sensitive files to `.gitignore`:
  ```
  credentials.json
  .env
  token.pickle
  ```

---

## Troubleshooting

### Database Connection Error
**Problem:** Cannot connect to PostgreSQL database

**Solutions:**
- Verify database credentials in `.env` file
- Check if PostgreSQL server is running
- Test connection: `psql "postgresql://user:pass@host:port/dbname"`
- Verify firewall rules allow database connections

### Schema Error
**Problem:** Tables don't exist or schema errors

**Solutions:**
- Make sure you ran `schema.sql` to create tables
- Verify tables exist: `psql -d gmail_storage -c "\dt"`
- Re-run schema: `psql -d gmail_storage -f schema.sql`

### OAuth Authentication Failed
**Problem:** Cannot authenticate with Gmail

**Solutions:**
- Ensure `credentials.json` exists in project directory
- Check Gmail API is enabled in Google Cloud Console
- Verify OAuth consent screen is configured
- Make sure your email is added as a test user
- Try deleting token and re-authenticating:
  ```sql
  DELETE FROM oauth_tokens WHERE user_email = 'your-email@gmail.com';
  ```

### Token Expired
**Problem:** OAuth token has expired

**Solutions:**
- The script automatically refreshes expired tokens
- If refresh fails, delete token from database and re-authenticate:
  ```sql
  DELETE FROM oauth_tokens WHERE user_email = 'your-email@gmail.com';
  ```
- Run `python gmail_fetch.py` again

### No Emails Found
**Problem:** Script runs but no emails are fetched

**Solutions:**
- Check that your Gmail account has emails in INBOX
- Verify the label specified in the code
- Check Google API quotas in Cloud Console
- Try increasing `max_results` in the script

### Rules Not Working
**Problem:** Email processor doesn't match or execute rules

**Solutions:**
- Verify JSON syntax in `rules.json` is valid
- Check field names are spelled correctly
- Ensure predicates match available options
- Test with simpler rules first
- Review processor output for error messages
- Make sure emails exist in database first

### Insufficient Permissions Error
**Problem:** Gmail API returns permission denied

**Solutions:**
- Ensure you're using `gmail.modify` scope (not `gmail.readonly`)
- Delete existing token and re-authenticate
- Check OAuth consent screen has correct scopes

---

## Example Rule Scenarios

### Scenario 1: Auto-Archive Old Newsletters

```json
{
  "description": "Archive old newsletters",
  "predicate": "any",
  "conditions": [
    {"field": "from", "predicate": "contains", "value": "newsletter"},
    {"field": "subject", "predicate": "contains", "value": "unsubscribe"}
  ],
  "actions": [
    {"type": "mark_read"},
    {"type": "move", "mailbox": "TRASH"}
  ]
}
```

### Scenario 2: Flag Important Work Emails

```json
{
  "description": "Keep work emails unread",
  "predicate": "all",
  "conditions": [
    {"field": "from", "predicate": "contains", "value": "@company.com"},
    {"field": "date_received", "predicate": "less_than", "value": 7, "unit": "days"}
  ],
  "actions": [
    {"type": "mark_unread"}
  ]
}
```

### Scenario 3: Clean Up Promotions

```json
{
  "description": "Delete old promotional emails",
  "predicate": "all",
  "conditions": [
    {"field": "from", "predicate": "contains", "value": "promo"},
    {"field": "date_received", "predicate": "greater_than", "value": 30, "unit": "days"}
  ],
  "actions": [
    {"type": "move", "mailbox": "TRASH"}
  ]
}
```

---

## API Documentation

For more information, see:
- [Gmail API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python)
- [Gmail API Reference](https://developers.google.com/gmail/api/reference/rest)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
