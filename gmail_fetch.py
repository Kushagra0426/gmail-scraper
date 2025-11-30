#!/usr/bin/env python3
"""
Gmail API Email Fetcher with PostgreSQL Storage
Authenticates using OAuth 2.0, fetches emails from Gmail inbox, and stores them in PostgreSQL.
"""

import os
import json
from datetime import datetime
from email.utils import parsedate_to_datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables
load_dotenv()

# Gmail API scopes
# Use gmail.modify to allow marking as read/unread and moving messages
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


class DatabaseManager:
    """Manages PostgreSQL database connections and operations."""

    def __init__(self):
        """Initialize database connection."""
        self.conn = None
        self.connect()

    def connect(self):
        """Establish connection to PostgreSQL database."""
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT', 5432),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                sslmode=os.getenv('DB_SSLMODE', 'require')
            )
            print("Successfully connected to PostgreSQL database")
        except Exception as e:
            print(f"Error connecting to database: {e}")
            raise

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            print("Database connection closed")

    def save_token(self, user_email, creds):
        """
        Save OAuth token to database.

        Args:
            user_email: User's email address
            creds: Google OAuth credentials object
        """
        try:
            cursor = self.conn.cursor()

            # Convert credentials to dictionary
            token_data = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': json.dumps(creds.scopes) if creds.scopes else None,
                'expiry': creds.expiry
            }

            # Insert or update token
            cursor.execute("""
                INSERT INTO oauth_tokens (user_email, token, refresh_token, token_uri,
                                         client_id, client_secret, scopes, expiry)
                VALUES (%(user_email)s, %(token)s, %(refresh_token)s, %(token_uri)s,
                       %(client_id)s, %(client_secret)s, %(scopes)s, %(expiry)s)
                ON CONFLICT (user_email)
                DO UPDATE SET
                    token = EXCLUDED.token,
                    refresh_token = EXCLUDED.refresh_token,
                    token_uri = EXCLUDED.token_uri,
                    client_id = EXCLUDED.client_id,
                    client_secret = EXCLUDED.client_secret,
                    scopes = EXCLUDED.scopes,
                    expiry = EXCLUDED.expiry,
                    updated_at = CURRENT_TIMESTAMP
            """, {'user_email': user_email, **token_data})

            self.conn.commit()
            print(f"Token saved to database for {user_email}")

        except Exception as e:
            self.conn.rollback()
            print(f"Error saving token: {e}")
            raise
        finally:
            cursor.close()

    def get_token(self, user_email):
        """
        Retrieve OAuth token from database.

        Args:
            user_email: User's email address

        Returns:
            Credentials object or None
        """
        try:
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT token, refresh_token, token_uri, client_id,
                       client_secret, scopes, expiry
                FROM oauth_tokens
                WHERE user_email = %s
            """, (user_email,))

            result = cursor.fetchone()
            cursor.close()

            if result:
                # Reconstruct credentials object
                creds = Credentials(
                    token=result['token'],
                    refresh_token=result['refresh_token'],
                    token_uri=result['token_uri'],
                    client_id=result['client_id'],
                    client_secret=result['client_secret'],
                    scopes=json.loads(result['scopes']) if result['scopes'] else None
                )
                # Set expiry if it exists
                if result['expiry']:
                    creds.expiry = result['expiry']

                return creds

            return None

        except Exception as e:
            print(f"Error retrieving token: {e}")
            return None

    def save_email(self, email_data):
        """
        Save email to database.

        Args:
            email_data: Dictionary containing email information
        """
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                INSERT INTO emails (gmail_message_id, thread_id, subject, sender,
                                   recipient, cc, bcc, date_received, snippet,
                                   body_text, body_html, labels, is_read, is_starred)
                VALUES (%(gmail_message_id)s, %(thread_id)s, %(subject)s, %(sender)s,
                       %(recipient)s, %(cc)s, %(bcc)s, %(date_received)s, %(snippet)s,
                       %(body_text)s, %(body_html)s, %(labels)s, %(is_read)s, %(is_starred)s)
                ON CONFLICT (gmail_message_id)
                DO UPDATE SET
                    subject = EXCLUDED.subject,
                    snippet = EXCLUDED.snippet,
                    labels = EXCLUDED.labels,
                    is_read = EXCLUDED.is_read,
                    is_starred = EXCLUDED.is_starred,
                    updated_at = CURRENT_TIMESTAMP
            """, email_data)

            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            print(f"Error saving email {email_data.get('gmail_message_id')}: {e}")
        finally:
            cursor.close()


def authenticate_gmail(db_manager, user_email):
    """
    Authenticates the user and returns Gmail API service object.
    Uses database for token storage instead of pickle files.

    Args:
        db_manager: DatabaseManager instance
        user_email: User's email address

    Returns:
        service: Authorized Gmail API service instance
    """
    creds = None

    # Try to get credentials from database
    creds = db_manager.get_token(user_email)

    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            try:
                creds.refresh(Request())
                db_manager.save_token(user_email, creds)
            except Exception as e:
                print(f"Error refreshing token: {e}")
                creds = None

        if not creds:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "credentials.json not found. Please download it from Google Cloud Console."
                )

            print("Starting OAuth authentication flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

            # Save the credentials to database
            db_manager.save_token(user_email, creds)

    try:
        service = build('gmail', 'v1', credentials=creds)
        print("Successfully authenticated to Gmail API")
        return service
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def parse_email_date(date_string):
    """
    Parse email date string to datetime object.

    Args:
        date_string: Email date string

    Returns:
        datetime object or None
    """
    try:
        return parsedate_to_datetime(date_string)
    except Exception:
        return None


def get_email_body(payload):
    """
    Extract email body from message payload.

    Args:
        payload: Email message payload

    Returns:
        tuple: (text_body, html_body)
    """
    text_body = None
    html_body = None

    if 'parts' in payload:
        for part in payload['parts']:
            mime_type = part.get('mimeType', '')
            if mime_type == 'text/plain' and 'data' in part.get('body', {}):
                import base64
                text_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
            elif mime_type == 'text/html' and 'data' in part.get('body', {}):
                import base64
                html_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
    elif 'body' in payload and 'data' in payload['body']:
        import base64
        data = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        mime_type = payload.get('mimeType', '')
        if mime_type == 'text/plain':
            text_body = data
        elif mime_type == 'text/html':
            html_body = data

    return text_body, html_body


def fetch_and_store_emails(service, db_manager, max_results=10):
    """
    Fetches emails from the user's inbox and stores them in the database.

    Args:
        service: Authorized Gmail API service instance
        db_manager: DatabaseManager instance
        max_results: Maximum number of emails to fetch (default: 10)

    Returns:
        int: Number of emails processed
    """
    try:
        # Call the Gmail API to fetch messages from inbox
        results = service.users().messages().list(
            userId='me',
            labelIds=['INBOX'],
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            print("No messages found in inbox.")
            return 0

        print(f"\nFound {len(messages)} messages in inbox:")
        print("-" * 80)

        emails_processed = 0

        for msg in messages:
            try:
                # Fetch the full message details
                message = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()

                # Extract headers
                headers = message['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
                recipient = next((h['value'] for h in headers if h['name'].lower() == 'to'), '')
                cc = next((h['value'] for h in headers if h['name'].lower() == 'cc'), None)
                bcc = next((h['value'] for h in headers if h['name'].lower() == 'bcc'), None)
                date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), None)

                # Parse date
                date_received = parse_email_date(date_str) if date_str else None

                # Extract body
                text_body, html_body = get_email_body(message['payload'])

                # Extract labels and flags
                labels = message.get('labelIds', [])
                is_read = 'UNREAD' not in labels
                is_starred = 'STARRED' in labels

                # Prepare email data for database
                email_data = {
                    'gmail_message_id': message['id'],
                    'thread_id': message.get('threadId'),
                    'subject': subject,
                    'sender': sender,
                    'recipient': recipient,
                    'cc': cc,
                    'bcc': bcc,
                    'date_received': date_received,
                    'snippet': message.get('snippet', ''),
                    'body_text': text_body,
                    'body_html': html_body,
                    'labels': labels,
                    'is_read': is_read,
                    'is_starred': is_starred
                }

                # Save to database
                db_manager.save_email(email_data)

                # Print email details
                print(f"\nEmail ID: {email_data['gmail_message_id']}")
                print(f"From: {email_data['sender']}")
                print(f"Date: {date_str}")
                print(f"Subject: {email_data['subject']}")
                print(f"Preview: {email_data['snippet'][:100]}...")
                print(f"Stored in database: ✓")
                print("-" * 80)

                emails_processed += 1

            except Exception as e:
                print(f"Error processing message {msg['id']}: {e}")
                continue

        return emails_processed

    except HttpError as error:
        print(f"An error occurred while fetching emails: {error}")
        return 0


def main():
    """
    Main function to authenticate and fetch emails.
    """
    print("Gmail API Email Fetcher with PostgreSQL Storage")
    print("=" * 80)

    # Get user email from environment
    user_email = os.getenv('GMAIL_USER_EMAIL')
    if not user_email:
        print("Error: GMAIL_USER_EMAIL not set in .env file")
        return

    # Initialize database manager
    try:
        db_manager = DatabaseManager()
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        print("Please check your .env file and database configuration")
        return

    try:
        # Authenticate and get service object
        service = authenticate_gmail(db_manager, user_email)

        if service is None:
            print("Failed to authenticate. Exiting.")
            return

        # Fetch and store emails (change max_results as needed)
        emails_count = fetch_and_store_emails(service, db_manager, max_results=10)

        print(f"\n\nTotal emails processed and stored: {emails_count}")

    finally:
        # Close database connection
        db_manager.close()


if __name__ == '__main__':
    main()
