import sqlite3
from pathlib import Path
from typing import Generator

from app.core.config import settings


def get_database_path() -> Path:
    """
    Convertit l'URL SQLite configurée dans VYRA
    en chemin réel vers le fichier de base de données.
    """
    database_url = settings.database_url

    if not database_url.startswith("sqlite:///"):
        raise ValueError(
            "VYRA V1 utilise SQLite. "
            "La database_url doit commencer par 'sqlite:///'."
        )

    database_path = database_url.replace("sqlite:///", "", 1)

    path = Path(database_path)

    if not path.is_absolute():
        path = Path.cwd() / path

    path.parent.mkdir(parents=True, exist_ok=True)

    return path


def create_connection() -> sqlite3.Connection:
    """
    Crée une connexion SQLite configurée pour VYRA.
    """
    database_path = get_database_path()

    connection = sqlite3.connect(
        database_path,
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """
    Fournit une connexion à la base de données
    aux routes et services FastAPI.
    """
    connection = create_connection()

    try:
        yield connection
    finally:
        connection.close()


def _create_tables(connection: sqlite3.Connection) -> None:
    """
    Crée les tables principales de VYRA V1.
    """

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL COLLATE NOCASE UNIQUE,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL DEFAULT '',
            phone TEXT,
            business_name TEXT,
            business_description TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            is_verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_login_at TEXT
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL DEFAULT '',
            company_name TEXT,
            email TEXT,
            phone TEXT,
            position TEXT,
            status TEXT NOT NULL DEFAULT 'new',
            source TEXT NOT NULL DEFAULT 'manual',
            notes TEXT,
            is_archived INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_contacted_at TEXT,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            contact_id INTEGER NOT NULL,
            channel TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            subject TEXT,
            summary TEXT,
            ai_enabled INTEGER NOT NULL DEFAULT 1,
            is_archived INTEGER NOT NULL DEFAULT 0,
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
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'received',
            is_ai_generated INTEGER NOT NULL DEFAULT 0,
            requires_human_validation INTEGER NOT NULL DEFAULT 0,
            is_approved INTEGER NOT NULL DEFAULT 0,
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
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            contact_id INTEGER,
            conversation_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            priority TEXT NOT NULL DEFAULT 'normal',
            due_at TEXT,
            reminder_enabled INTEGER NOT NULL DEFAULT 0,
            reminder_at TEXT,
            reminder_sent INTEGER NOT NULL DEFAULT 0,
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
        );

        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            contact_id INTEGER,
            conversation_id INTEGER,
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
        );
        """
    )


def _create_indexes(connection: sqlite3.Connection) -> None:
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
    Initialise complètement la base SQLite de VYRA V1.

    Cette fonction est appelée au démarrage de FastAPI
    depuis app/main.py.
    """

    connection = create_connection()

    try:
        _create_tables(connection)
        _create_indexes(connection)
        connection.commit()
    finally:
        connection.close()