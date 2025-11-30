-- Gmail Email Storage Schema
-- PostgreSQL Database Schema for storing Gmail emails and OAuth tokens

-- Table to store OAuth credentials/tokens
CREATE TABLE IF NOT EXISTS oauth_tokens (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) UNIQUE NOT NULL,
    token TEXT NOT NULL,
    refresh_token TEXT,
    token_uri TEXT,
    client_id TEXT,
    client_secret TEXT,
    scopes TEXT,
    expiry TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table to store email messages
CREATE TABLE IF NOT EXISTS emails (
    id SERIAL PRIMARY KEY,
    gmail_message_id VARCHAR(255) UNIQUE NOT NULL,
    thread_id VARCHAR(255),
    subject TEXT,
    sender VARCHAR(500),
    recipient VARCHAR(500),
    cc TEXT,
    bcc TEXT,
    date_received TIMESTAMP,
    snippet TEXT,
    body_text TEXT,
    body_html TEXT,
    labels TEXT[],
    is_read BOOLEAN DEFAULT FALSE,
    is_starred BOOLEAN DEFAULT FALSE,
    has_attachments BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table to store email attachments
CREATE TABLE IF NOT EXISTS attachments (
    id SERIAL PRIMARY KEY,
    email_id INTEGER REFERENCES emails(id) ON DELETE CASCADE,
    gmail_message_id VARCHAR(255) NOT NULL,
    attachment_id VARCHAR(255) NOT NULL,
    filename VARCHAR(500),
    mime_type VARCHAR(100),
    size_bytes INTEGER,
    data BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_emails_gmail_message_id ON emails(gmail_message_id);
CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails(sender);
CREATE INDEX IF NOT EXISTS idx_emails_date_received ON emails(date_received DESC);
CREATE INDEX IF NOT EXISTS idx_emails_labels ON emails USING GIN(labels);
CREATE INDEX IF NOT EXISTS idx_attachments_email_id ON attachments(email_id);
CREATE INDEX IF NOT EXISTS idx_oauth_tokens_user_email ON oauth_tokens(user_email);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers to automatically update updated_at
CREATE TRIGGER update_emails_updated_at
    BEFORE UPDATE ON emails
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_oauth_tokens_updated_at
    BEFORE UPDATE ON oauth_tokens
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE oauth_tokens IS 'Stores OAuth 2.0 tokens for Gmail API authentication';
COMMENT ON TABLE emails IS 'Stores Gmail messages with metadata and content';
COMMENT ON TABLE attachments IS 'Stores email attachments';

COMMENT ON COLUMN oauth_tokens.token IS 'OAuth access token';
COMMENT ON COLUMN oauth_tokens.refresh_token IS 'OAuth refresh token for renewing access';
COMMENT ON COLUMN oauth_tokens.expiry IS 'Token expiration timestamp';
COMMENT ON COLUMN emails.gmail_message_id IS 'Unique message ID from Gmail API';
COMMENT ON COLUMN emails.thread_id IS 'Gmail conversation thread ID';
COMMENT ON COLUMN emails.labels IS 'Array of Gmail labels (INBOX, SENT, etc.)';
