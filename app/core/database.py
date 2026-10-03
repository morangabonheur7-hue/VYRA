from typing import Generator

import psycopg
from psycopg.rows import dict_row

from app.core.config import settings


def get_database_url() -> str:
    """
    Récupère l'URL PostgreSQL de Supabase.
    """
    database_url = settings.database_url

    if not database_url:
        raise ValueError(
            "DATABASE_URL n'est pas configurée."
        )

    if not database_url.startswith(("postgresql://", "postgres://")):
        raise ValueError(
            "VYRA utilise maintenant PostgreSQL. "
            "DATABASE_URL doit être une URL PostgreSQL."
        )

    return database_url


def create_connection():
    """
    Crée une connexion PostgreSQL vers Supabase.
    """
    connection = psycopg.connect(
        get_database_url(),
        row_factory=dict_row,
    )

    return connection


def get_db() -> Generator:
    """
    Fournit une connexion PostgreSQL
    aux routes et services FastAPI.
    """
    connection = create_connection()

    try:
        yield connection
    finally:
        connection.close()


def _create_tables(connection) -> None:
    """
    Crée les tables principales de VYRA V1.
    """

    queries = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL DEFAULT '',
            phone TEXT,
            business_name TEXT,
            business_description TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            is_verified BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_login_at TEXT
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS contacts (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL DEFAULT '',
            company_name TEXT,
            email TEXT,
            phone TEXT,
            position TEXT,
            status TEXT NOT NULL DEFAULT 'new',
            source TEXT NOT NULL DEFAULT 'manual',
            notes TEXT,
            is_archived BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_contacted_at TEXT,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS conversations (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            contact_id BIGINT NOT NULL,
            channel TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            subject TEXT,
            summary TEXT,
            ai_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            is_archived BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_message_at TEXT,
            closed_at TEXT,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            FOREIGN KEY (contact_id)
                REFERENCES contacts(id)
                ON DELETE CASCADE
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS messages (
            id BIGSERIAL PRIMARY KEY,
            conversation_id BIGINT NOT NULL,
            sender TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'received',
            is_ai_generated BOOLEAN NOT NULL DEFAULT FALSE,
            requires_human_validation BOOLEAN NOT NULL DEFAULT FALSE,
            is_approved BOOLEAN NOT NULL DEFAULT FALSE,
            approved_at TEXT,
            external_message_id TEXT,
            metadata TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            sent_at TEXT,
            delivered_at TEXT,
            read_at TEXT,

            FOREIGN KEY (conversation_id)
                REFERENCES conversations(id)
                ON DELETE CASCADE
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS tasks (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            contact_id BIGINT,
            conversation_id BIGINT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            priority TEXT NOT NULL DEFAULT 'normal',
            due_at TEXT,
            reminder_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            reminder_at TEXT,
            reminder_sent BOOLEAN NOT NULL DEFAULT FALSE,
            completed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            FOREIGN KEY (contact_id)
                REFERENCES contacts(id)
                ON DELETE SET NULL,

            FOREIGN KEY (conversation_id)
                REFERENCES conversations(id)
                ON DELETE SET NULL
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS memories (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            contact_id BIGINT,
            conversation_id BIGINT,
            memory_type TEXT NOT NULL,
            content TEXT NOT NULL,
            importance INTEGER NOT NULL DEFAULT 1,
            metadata TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            FOREIGN KEY (contact_id)
                REFERENCES contacts(id)
                ON DELETE SET NULL,

            FOREIGN KEY (conversation_id)
                REFERENCES conversations(id)
                ON DELETE SET NULL
        )
        """,
    ]

    for query in queries:
        connection.execute(query)


def _create_indexes(connection) -> None:
    """
    Crée les index nécessaires aux recherches fréquentes.
    """

    indexes = [
        """
        CREATE INDEX IF NOT EXISTS idx_contacts_user_id
        ON contacts(user_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_contacts_email
        ON contacts(email)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_contacts_phone
        ON contacts(phone)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_contacts_status
        ON contacts(status)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_contacts_archived
        ON contacts(is_archived)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_conversations_user_id
        ON conversations(user_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_conversations_contact_id
        ON conversations(contact_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_conversations_status
        ON conversations(status)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_conversations_archived
        ON conversations(is_archived)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
        ON messages(conversation_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_messages_status
        ON messages(status)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_messages_created_at
        ON messages(created_at)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_tasks_user_id
        ON tasks(user_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_tasks_contact_id
        ON tasks(contact_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_tasks_status
        ON tasks(status)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_memories_user_id
        ON memories(user_id)
        """,
    ]

    for query in indexes:
        connection.execute(query)


def initialize_database() -> None:
    """
    Initialise la base PostgreSQL de VYRA.
    """
    connection = create_connection()

    try:
        _create_tables(connection)
        _create_indexes(connection)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
