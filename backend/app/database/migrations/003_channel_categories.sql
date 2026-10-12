ALTER TABLE channels ADD COLUMN category VARCHAR NOT NULL DEFAULT 'cfds';
CREATE INDEX IF NOT EXISTS ix_channels_category ON channels (category);
