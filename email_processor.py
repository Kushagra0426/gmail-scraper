#!/usr/bin/env python3
"""
Email Rule Processor
Processes emails from PostgreSQL database based on JSON rules and performs actions via Gmail API.
"""

import os
import json
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables
load_dotenv()


class EmailRuleProcessor:
    """Processes emails based on rules and executes actions."""

    def __init__(self, rules_file='rules.json'):
        """
        Initialize the email processor.

        Args:
            rules_file: Path to JSON file containing rules
        """
        self.rules = self.load_rules(rules_file)
        self.db_conn = None
        self.gmail_service = None
        self.connect_database()

    def connect_database(self):
        """Establish connection to PostgreSQL database."""
        try:
            self.db_conn = psycopg2.connect(
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT', 5432),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                sslmode=os.getenv('DB_SSLMODE', 'require')
            )
            print("✓ Connected to PostgreSQL database")
        except Exception as e:
            print(f"✗ Error connecting to database: {e}")
            raise

    def authenticate_gmail(self):
        """Authenticate with Gmail API using token from database."""
        try:
            user_email = os.getenv('GMAIL_USER_EMAIL')
            if not user_email:
                raise ValueError("GMAIL_USER_EMAIL not set in .env")

            cursor = self.db_conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT token, refresh_token, token_uri, client_id,
                       client_secret, scopes, expiry
                FROM oauth_tokens
                WHERE user_email = %s
            """, (user_email,))

            result = cursor.fetchone()
            cursor.close()

            if not result:
                raise ValueError(f"No OAuth token found for {user_email}. Run gmail_fetch.py first.")

            # Reconstruct credentials
            creds = Credentials(
                token=result['token'],
                refresh_token=result['refresh_token'],
                token_uri=result['token_uri'],
                client_id=result['client_id'],
                client_secret=result['client_secret'],
                scopes=json.loads(result['scopes']) if result['scopes'] else None
            )
            if result['expiry']:
                creds.expiry = result['expiry']

            # Refresh if expired
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    print("Refreshing expired token...")
                    creds.refresh(Request())
                else:
                    raise ValueError("Credentials are invalid and cannot be refreshed")

            # We need modify scope, not just readonly
            # Build service with gmail.modify scope
            self.gmail_service = build('gmail', 'v1', credentials=creds)
            print("✓ Authenticated to Gmail API")

        except Exception as e:
            print(f"✗ Error authenticating: {e}")
            raise

    def load_rules(self, rules_file):
        """
        Load rules from JSON file.

        Args:
            rules_file: Path to JSON rules file

        Returns:
            dict: Loaded rules
        """
        try:
            with open(rules_file, 'r') as f:
                data = json.load(f)
            print(f"✓ Loaded {len(data.get('rules', []))} rules from {rules_file}")
            return data.get('rules', [])
        except FileNotFoundError:
            print(f"✗ Rules file not found: {rules_file}")
            return []
        except json.JSONDecodeError as e:
            print(f"✗ Error parsing JSON: {e}")
            return []

    def evaluate_condition(self, condition, email):
        """
        Evaluate a single condition against an email.

        Args:
            condition: Condition dict with field, predicate, value
            email: Email dict from database

        Returns:
            bool: True if condition matches
        """
        field = condition.get('field', '').lower()
        predicate = condition.get('predicate', '').lower()
        value = condition.get('value', '')

        # Get the field value from email
        email_value = None

        if field == 'from':
            email_value = email.get('sender', '').lower()
        elif field == 'to':
            email_value = email.get('recipient', '').lower()
        elif field == 'subject':
            email_value = email.get('subject', '').lower()
        elif field == 'message' or field == 'body':
            # Check both text and HTML body
            text_body = email.get('body_text', '') or ''
            html_body = email.get('body_html', '') or ''
            email_value = (text_body + ' ' + html_body).lower()
        elif field == 'date_received':
            return self.evaluate_date_condition(condition, email)
        else:
            print(f"Warning: Unknown field '{field}'")
            return False

        # String predicates
        value_lower = str(value).lower()

        if predicate == 'contains':
            return value_lower in email_value
        elif predicate == 'does_not_contain' or predicate == 'not_contains':
            return value_lower not in email_value
        elif predicate == 'equals':
            return email_value == value_lower
        elif predicate == 'does_not_equal' or predicate == 'not_equals':
            return email_value != value_lower
        else:
            print(f"Warning: Unknown predicate '{predicate}'")
            return False

    def evaluate_date_condition(self, condition, email):
        """
        Evaluate date-based condition.

        Args:
            condition: Condition dict with predicate and value
            email: Email dict from database

        Returns:
            bool: True if condition matches
        """
        predicate = condition.get('predicate', '').lower()
        value = condition.get('value', 0)
        unit = condition.get('unit', 'days').lower()

        date_received = email.get('date_received')
        if not date_received:
            return False

        # Ensure date_received is a datetime object
        if isinstance(date_received, str):
            try:
                date_received = datetime.fromisoformat(date_received)
            except:
                return False

        # Calculate the threshold date
        now = datetime.now(date_received.tzinfo) if date_received.tzinfo else datetime.now()

        if unit == 'days':
            threshold = now - timedelta(days=value)
        elif unit == 'months':
            threshold = now - timedelta(days=value * 30)  # Approximate
        else:
            print(f"Warning: Unknown unit '{unit}'")
            return False

        # Evaluate predicate
        if predicate == 'less_than':
            # Email is less than X days old (received after threshold)
            return date_received > threshold
        elif predicate == 'greater_than':
            # Email is greater than X days old (received before threshold)
            return date_received < threshold
        else:
            print(f"Warning: Unknown date predicate '{predicate}'")
            return False

    def evaluate_rule(self, rule, email):
        """
        Evaluate all conditions in a rule against an email.

        Args:
            rule: Rule dict with conditions and predicate
            email: Email dict from database

        Returns:
            bool: True if rule matches
        """
        predicate = rule.get('predicate', 'all').lower()
        conditions = rule.get('conditions', [])

        if not conditions:
            return False

        results = [self.evaluate_condition(cond, email) for cond in conditions]

        if predicate == 'all':
            return all(results)
        elif predicate == 'any':
            return any(results)
        else:
            print(f"Warning: Unknown rule predicate '{predicate}'")
            return False

    def execute_action(self, action, email):
        """
        Execute a single action on an email.

        Args:
            action: Action dict with type and parameters
            email: Email dict from database

        Returns:
            bool: True if action succeeded
        """
        action_type = action.get('type', '').lower()
        gmail_message_id = email.get('gmail_message_id')

        if not gmail_message_id:
            print("✗ No gmail_message_id found for email")
            return False

        try:
            if action_type == 'mark_read' or action_type == 'mark_as_read':
                return self.mark_as_read(gmail_message_id)

            elif action_type == 'mark_unread' or action_type == 'mark_as_unread':
                return self.mark_as_unread(gmail_message_id)

            elif action_type == 'move':
                mailbox = action.get('mailbox', 'INBOX')
                return self.move_message(gmail_message_id, mailbox)

            else:
                print(f"Warning: Unknown action type '{action_type}'")
                return False

        except HttpError as e:
            print(f"✗ Gmail API error: {e}")
            return False
        except Exception as e:
            print(f"✗ Error executing action: {e}")
            return False

    def mark_as_read(self, gmail_message_id):
        """Mark email as read."""
        try:
            self.gmail_service.users().messages().modify(
                userId='me',
                id=gmail_message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            print(f"  ✓ Marked as read: {gmail_message_id}")
            return True
        except Exception as e:
            print(f"  ✗ Failed to mark as read: {e}")
            return False

    def mark_as_unread(self, gmail_message_id):
        """Mark email as unread."""
        try:
            self.gmail_service.users().messages().modify(
                userId='me',
                id=gmail_message_id,
                body={'addLabelIds': ['UNREAD']}
            ).execute()
            print(f"  ✓ Marked as unread: {gmail_message_id}")
            return True
        except Exception as e:
            print(f"  ✗ Failed to mark as unread: {e}")
            return False

    def move_message(self, gmail_message_id, mailbox):
        """
        Move message to a different mailbox/label.

        Args:
            gmail_message_id: Gmail message ID
            mailbox: Target mailbox/label (INBOX, TRASH, etc.)
        """
        try:
            # Get current labels
            message = self.gmail_service.users().messages().get(
                userId='me',
                id=gmail_message_id,
                format='minimal'
            ).execute()

            current_labels = message.get('labelIds', [])

            # Prepare label changes
            add_labels = [mailbox.upper()]
            remove_labels = []

            # Remove conflicting labels
            if mailbox.upper() == 'TRASH':
                remove_labels = [l for l in current_labels if l in ['INBOX', 'SPAM']]
            elif mailbox.upper() == 'INBOX':
                remove_labels = [l for l in current_labels if l in ['TRASH', 'SPAM']]

            # Execute move
            self.gmail_service.users().messages().modify(
                userId='me',
                id=gmail_message_id,
                body={
                    'addLabelIds': add_labels,
                    'removeLabelIds': remove_labels
                }
            ).execute()
            print(f"  ✓ Moved to {mailbox}: {gmail_message_id}")
            return True
        except Exception as e:
            print(f"  ✗ Failed to move message: {e}")
            return False

    def get_emails_from_db(self, limit=100):
        """
        Fetch emails from database for processing.

        Args:
            limit: Maximum number of emails to fetch

        Returns:
            list: List of email dicts
        """
        try:
            cursor = self.db_conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT
                    id, gmail_message_id, thread_id, subject, sender,
                    recipient, cc, bcc, date_received, snippet,
                    body_text, body_html, labels, is_read, is_starred
                FROM emails
                ORDER BY date_received DESC
                LIMIT %s
            """, (limit,))

            emails = cursor.fetchall()
            cursor.close()
            print(f"✓ Fetched {len(emails)} emails from database")
            return emails

        except Exception as e:
            print(f"✗ Error fetching emails: {e}")
            return []

    def process_emails(self, limit=100):
        """
        Process emails against all rules.

        Args:
            limit: Maximum number of emails to process
        """
        if not self.rules:
            print("No rules to process")
            return

        print(f"\n{'='*80}")
        print(f"Processing emails with {len(self.rules)} rules")
        print(f"{'='*80}\n")

        # Authenticate Gmail
        self.authenticate_gmail()

        # Get emails
        emails = self.get_emails_from_db(limit)

        if not emails:
            print("No emails to process")
            return

        # Process each email
        total_actions = 0

        for email in emails:
            email_id = email.get('gmail_message_id', 'unknown')
            subject = email.get('subject', 'No Subject')[:60]
            sender = email.get('sender', 'Unknown')[:40]

            # Check each rule
            for rule_idx, rule in enumerate(self.rules, 1):
                rule_desc = rule.get('description', f'Rule {rule_idx}')

                # Evaluate rule
                if self.evaluate_rule(rule, email):
                    print(f"\n✓ Rule matched: '{rule_desc}'")
                    print(f"  Email: {subject}")
                    print(f"  From: {sender}")
                    print(f"  Actions:")

                    # Execute actions
                    actions = rule.get('actions', [])
                    for action in actions:
                        if self.execute_action(action, email):
                            total_actions += 1

        print(f"\n{'='*80}")
        print(f"Processing complete: {total_actions} actions executed")
        print(f"{'='*80}\n")

    def close(self):
        """Close database connection."""
        if self.db_conn:
            self.db_conn.close()
            print("✓ Database connection closed")


def main():
    """Main function."""
    print("="*80)
    print("Email Rule Processor")
    print("="*80)
    print()

    # Initialize processor
    try:
        processor = EmailRuleProcessor('rules.json')

        # Process emails
        processor.process_emails(limit=100)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        processor.close()


if __name__ == '__main__':
    main()
