CREATE TABLE IF NOT EXISTS telegram_publications (
    id INTEGER PRIMARY KEY,
    account_id VARCHAR NOT NULL,
    source_channel_id VARCHAR NOT NULL,
    source_message_id VARCHAR NOT NULL,
    destination_chat_id VARCHAR NOT NULL,
    random_id BIGINT NOT NULL,
    body TEXT NOT NULL,
    status VARCHAR NOT NULL,
    error_type VARCHAR,
    created_at DATETIME NOT NULL,
    sent_at DATETIME,
    CONSTRAINT uq_telegram_publication_source_destination UNIQUE (
        account_id, source_channel_id, source_message_id, destination_chat_id
    )
);