#!/usr/bin/env python3
"""
Gmail API Email Fetcher
Authenticates using OAuth 2.0 and fetches emails from Gmail inbox.
"""

import os.path
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def authenticate_gmail():
    """
    Authenticates the user and returns Gmail API service object.

    Returns:
        service: Authorized Gmail API service instance
    """
    creds = None

    # The file token.pickle stores the user's access and refresh tokens
    # It is created automatically when the authorization flow completes for the first time
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "credentials.json not found. Please download it from Google Cloud Console."
                )

            print("Starting OAuth authentication flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
            print("Token saved to token.pickle")

    try:
        service = build('gmail', 'v1', credentials=creds)
        print("Successfully authenticated to Gmail API")
        return service
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def fetch_emails(service, max_results=10):
    """
    Fetches emails from the user's inbox.

    Args:
        service: Authorized Gmail API service instance
        max_results: Maximum number of emails to fetch (default: 10)

    Returns:
        list: List of email messages with their details
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
            return []

        print(f"\nFound {len(messages)} messages in inbox:")
        print("-" * 80)

        email_list = []

        for msg in messages:
            # Fetch the full message details
            message = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()

            # Extract headers
            headers = message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')

            # Extract snippet (preview text)
            snippet = message.get('snippet', '')

            email_data = {
                'id': msg['id'],
                'subject': subject,
                'from': sender,
                'date': date,
                'snippet': snippet
            }

            email_list.append(email_data)

            # Print email details
            print(f"\nEmail ID: {email_data['id']}")
            print(f"From: {email_data['from']}")
            print(f"Date: {email_data['date']}")
            print(f"Subject: {email_data['subject']}")
            print(f"Preview: {email_data['snippet'][:100]}...")
            print("-" * 80)

        return email_list

    except HttpError as error:
        print(f"An error occurred while fetching emails: {error}")
        return []


def main():
    """
    Main function to authenticate and fetch emails.
    """
    print("Gmail API Email Fetcher")
    print("=" * 80)

    # Authenticate and get service object
    service = authenticate_gmail()

    if service is None:
        print("Failed to authenticate. Exiting.")
        return

    # Fetch emails (change max_results as needed)
    emails = fetch_emails(service, max_results=10)

    print(f"\n\nTotal emails fetched: {len(emails)}")


if __name__ == '__main__':
    main()
