from typing import Generator

import psycopg
from psycopg.rows import dict_row

from app.core.config import settings


def get_database_url() -> str:
    database_url = settings.database_url

    if not database_url:
        raise ValueError("DATABASE_URL n'est pas configurée.")

    if not database_url.startswith(
        ("postgresql://", "postgres://")
    ):
        raise ValueError(
            "VYRA utilise PostgreSQL. "
            "DATABASE_URL doit être une URL PostgreSQL."
        )

    return database_url


def create_connection():
    return psycopg.connect(
        get_database_url(),
        row_factory=dict_row,
    )


def get_db() -> Generator:
    connection = create_connection()

    try:
        yield connection
    finally:
        connection.close()


def _create_tables(connection) -> None:
    queries = [

        # ============================================================
        # USERS
        # ============================================================

        """
        CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT,
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

        # ============================================================
        # COMPANIES
        # ============================================================

        """
        CREATE TABLE IF NOT EXISTS companies (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            sector TEXT,
            description TEXT,
            country TEXT,
            city TEXT,
            address TEXT,
            phone TEXT,
            email TEXT,
            website TEXT,
            default_language TEXT NOT NULL DEFAULT 'fr',
            timezone TEXT NOT NULL DEFAULT 'UTC',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,

        # ============================================================
        # COMPANY PRODUCTS
        # ============================================================

        """
        CREATE TABLE IF NOT EXISTS company_products (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            price NUMERIC,
            currency TEXT,
            availability TEXT,
            metadata TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id)
                REFERENCES companies(id)
                ON DELETE CASCADE
        )
        """,

        # ============================================================
        # COMPANY SERVICES
        # ============================================================

        """
        CREATE TABLE IF NOT EXISTS company_services (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            price NUMERIC,
            currency TEXT,
            duration TEXT,
            availability TEXT,
            metadata TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id)
                REFERENCES companies(id)
                ON DELETE CASCADE
        )
        """,

        # ============================================================
        # COMPANY RULES
        # ============================================================

        """
        CREATE TABLE IF NOT EXISTS company_rules (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT NOT NULL,
            rule_type TEXT NOT NULL,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 1,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id)
                REFERENCES companies(id)
                ON DELETE CASCADE
        )
        """,

        # ============================================================
        # CONTACTS
        # ============================================================

        """
        CREATE TABLE IF NOT EXISTS contacts (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT,
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
            FOREIGN KEY (company_id)
                REFERENCES companies(id)
                ON DELETE CASCADE,
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
        """,

        # ============================================================
        # PROSPECT PROFILES
        # ============================================================

        """
        CREATE TABLE IF NOT EXISTS prospect_profiles (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT NOT NULL,
            contact_id BIGINT NOT NULL,
            intent TEXT,
            budget NUMERIC,
            currency TEXT,
            location TEXT,
            product_interest TEXT,
            urgency TEXT,
            qualification_status TEXT NOT NULL DEFAULT 'unqualified',
            notes TEXT,
            metadata TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id)
                REFERENCES companies(id)
                ON DELETE CASCADE,
            FOREIGN KEY (contact_id)
                REFERENCES contacts(id)
                ON DELETE CASCADE
        )
        """,

        # ============================================================
        # PROSPECT INTENTS
        # ============================================================

        """
        CREATE TABLE IF NOT EXISTS prospect_intents (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT NOT NULL,
            contact_id BIGINT NOT NULL,
            conversation_id BIGINT,
            intent TEXT NOT NULL,
            confidence NUMERIC,
            extracted_data TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id)
                REFERENCES companies(id)
                ON DELETE CASCADE,
            FOREIGN KEY (contact_id)
                REFERENCES contacts(id)
                ON DELETE CASCADE
        )
        """,

        # ============================================================
        # PROSPECT SCORES
        # ============================================================

        """
        CREATE TABLE IF NOT EXISTS prospect_scores (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT NOT NULL,
            contact_id BIGINT NOT NULL,
            score NUMERIC NOT NULL DEFAULT 0,
            category TEXT,
            reasons TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id)
                REFERENCES companies(id)
                ON DELETE CASCADE,
            FOREIGN KEY (contact_id)
                REFERENCES contacts(id)
                ON DELETE CASCADE
        )
        """,

        # ============================================================
        # CONVERSATIONS
        # ============================================================

        """
        CREATE TABLE IF NOT EXISTS conversations (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT,
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
            FOREIGN KEY (company_id)
                REFERENCES companies(id)
                ON DELETE CASCADE,
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,
            FOREIGN KEY (contact_id)
                REFERENCES contacts(id)
                ON DELETE CASCADE
        )
        """,

        # ============================================================
        # MESSAGES
        # ============================================================

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

        # ============================================================
        # MEMORIES
        # ============================================================

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

        # ============================================================
        # TASKS
        # ============================================================

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

        # ============================================================
        # FOLLOWUPS
        # ============================================================

        """
        CREATE TABLE IF NOT EXISTS followups (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT NOT NULL,
            contact_id BIGINT NOT NULL,
            conversation_id BIGINT NOT NULL,
            scheduled_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            reason TEXT,
            message TEXT,
            attempts INTEGER NOT NULL DEFAULT 0,
            last_attempt_at TEXT,
            completed_at TEXT,
            cancelled_at TEXT,
            metadata TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id)
                REFERENCES companies(id)
                ON DELETE CASCADE,
            FOREIGN KEY (contact_id)
                REFERENCES contacts(id)
                ON DELETE CASCADE,
            FOREIGN KEY (conversation_id)
                REFERENCES conversations(id)
                ON DELETE CASCADE
        )
        """,

        # ============================================================
        # FOLLOWUP RULES
        # ============================================================

        """
        CREATE TABLE IF NOT EXISTS followup_rules (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT NOT NULL,
            name TEXT NOT NULL,
            trigger TEXT NOT NULL,
            delay_minutes INTEGER NOT NULL,
            max_attempts INTEGER NOT NULL DEFAULT 1,
            instructions TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id)
                REFERENCES companies(id)
                ON DELETE CASCADE
        )
        """,

        # ============================================================
        # AI DECISIONS
        # ============================================================

        """
        CREATE TABLE IF NOT EXISTS ai_decisions (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT NOT NULL,
            conversation_id BIGINT,
            contact_id BIGINT,
            decision_type TEXT NOT NULL,
            decision TEXT NOT NULL,
            reasoning TEXT,
            confidence NUMERIC,
            metadata TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id)
                REFERENCES companies(id)
                ON DELETE CASCADE
        )
        """,

        # ============================================================
        # AI ACTIONS
        # ============================================================

        """
        CREATE TABLE IF NOT EXISTS ai_actions (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT NOT NULL,
            conversation_id BIGINT,
            contact_id BIGINT,
            action_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            payload TEXT,
            error TEXT,
            executed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id)
                REFERENCES companies(id)
                ON DELETE CASCADE
        )
        """,

        # ============================================================
        # ESCALATIONS
        # ============================================================

        """
        CREATE TABLE IF NOT EXISTS escalations (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT NOT NULL,
            conversation_id BIGINT NOT NULL,
            contact_id BIGINT NOT NULL,
            reason TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'normal',
            status TEXT NOT NULL DEFAULT 'open',
            assigned_user_id BIGINT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            resolved_at TEXT,
            FOREIGN KEY (company_id)
                REFERENCES companies(id)
                ON DELETE CASCADE,
            FOREIGN KEY (conversation_id)
                REFERENCES conversations(id)
                ON DELETE CASCADE,
            FOREIGN KEY (contact_id)
                REFERENCES contacts(id)
                ON DELETE CASCADE,
            FOREIGN KEY (assigned_user_id)
                REFERENCES users(id)
                ON DELETE SET NULL
        )
        """,

        # ============================================================
        # INTEGRATIONS
        # ============================================================

        """
        CREATE TABLE IF NOT EXISTS integrations (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT NOT NULL,
            provider TEXT NOT NULL,
            type TEXT NOT NULL,
            credentials TEXT,
            configuration TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id)
                REFERENCES companies(id)
                ON DELETE CASCADE
        )
        """,

        # ============================================================
        # WEBHOOK EVENTS
        # ============================================================

        """
        CREATE TABLE IF NOT EXISTS webhook_events (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT,
            provider TEXT NOT NULL,
            external_event_id TEXT NOT NULL,
            event_type TEXT,
            payload TEXT,
            status TEXT NOT NULL DEFAULT 'received',
            attempts INTEGER NOT NULL DEFAULT 0,
            error TEXT,
            processed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id)
                REFERENCES companies(id)
                ON DELETE CASCADE,
            UNIQUE (
                company_id,
                provider,
                external_event_id
            )
        )
        """,
    ]

    for query in queries:
        connection.execute(query)


def _migrate_existing_tables(connection) -> None:
    migrations = [

        # ============================================================
        # EXISTING USERS TABLE
        # ============================================================

        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS company_id BIGINT
        """,

        # ============================================================
        # EXISTING CONTACTS TABLE
        # ============================================================

        """
        ALTER TABLE contacts
        ADD COLUMN IF NOT EXISTS company_id BIGINT
        """,

        # ============================================================
        # EXISTING CONVERSATIONS TABLE
        # ============================================================

        """
        ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS company_id BIGINT
        """,
    ]

    for query in migrations:
        connection.execute(query)


def _create_indexes(connection) -> None:
    indexes = [

        # Users
        """
        CREATE INDEX IF NOT EXISTS idx_users_company_id
        ON users(company_id)
        """,

        # Companies
        """
        CREATE INDEX IF NOT EXISTS idx_companies_active
        ON companies(is_active)
        """,

        # Products
        """
        CREATE INDEX IF NOT EXISTS idx_products_company_id
        ON company_products(company_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_products_active
        ON company_products(is_active)
        """,

        # Services
        """
        CREATE INDEX IF NOT EXISTS idx_services_company_id
        ON company_services(company_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_services_active
        ON company_services(is_active)
        """,

        # Rules
        """
        CREATE INDEX IF NOT EXISTS idx_rules_company_id
        ON company_rules(company_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_rules_active
        ON company_rules(is_active)
        """,

        # Contacts
        """
        CREATE INDEX IF NOT EXISTS idx_contacts_company_id
        ON contacts(company_id)
        """,

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

        # Prospect profiles
        """
        CREATE INDEX IF NOT EXISTS idx_prospect_profiles_company_id
        ON prospect_profiles(company_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_prospect_profiles_contact_id
        ON prospect_profiles(contact_id)
        """,

        # Prospect intents
        """
        CREATE INDEX IF NOT EXISTS idx_prospect_intents_company_id
        ON prospect_intents(company_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_prospect_intents_contact_id
        ON prospect_intents(contact_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_prospect_intents_conversation_id
        ON prospect_intents(conversation_id)
        """,

        # Prospect scores
        """
        CREATE INDEX IF NOT EXISTS idx_prospect_scores_company_id
        ON prospect_scores(company_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_prospect_scores_contact_id
        ON prospect_scores(contact_id)
        """,

        # Conversations
        """
        CREATE INDEX IF NOT EXISTS idx_conversations_company_id
        ON conversations(company_id)
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

        # Messages
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
        CREATE INDEX IF NOT EXISTS idx_messages_external_id
        ON messages(external_message_id)
        """,

        # Memories
        """
        CREATE INDEX IF NOT EXISTS idx_memories_user_id
        ON memories(user_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_memories_contact_id
        ON memories(contact_id)
        """,

        # Tasks
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

        # Followups
        """
        CREATE INDEX IF NOT EXISTS idx_followups_company_id
        ON followups(company_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_followups_contact_id
        ON followups(contact_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_followups_status
        ON followups(status)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_followups_scheduled_at
        ON followups(scheduled_at)
        """,

        # Followup rules
        """
        CREATE INDEX IF NOT EXISTS idx_followup_rules_company_id
        ON followup_rules(company_id)
        """,

        # AI decisions
        """
        CREATE INDEX IF NOT EXISTS idx_ai_decisions_company_id
        ON ai_decisions(company_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_ai_decisions_conversation_id
        ON ai_decisions(conversation_id)
        """,

        # AI actions
        """
        CREATE INDEX IF NOT EXISTS idx_ai_actions_company_id
        ON ai_actions(company_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_ai_actions_status
        ON ai_actions(status)
        """,

        # Escalations
        """
        CREATE INDEX IF NOT EXISTS idx_escalations_company_id
        ON escalations(company_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_escalations_status
        ON escalations(status)
        """,

        # Integrations
        """
        CREATE INDEX IF NOT EXISTS idx_integrations_company_id
        ON integrations(company_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_integrations_provider
        ON integrations(provider)
        """,

        # Webhook events
        """
        CREATE INDEX IF NOT EXISTS idx_webhook_events_company_id
        ON webhook_events(company_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_webhook_events_status
        ON webhook_events(status)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_webhook_events_created_at
        ON webhook_events(created_at)
        """,
    ]

    for query in indexes:
        connection.execute(query)


def initialize_database() -> None:
    connection = create_connection()

    try:
        _create_tables(connection)
        _migrate_existing_tables(connection)
        _create_indexes(connection)
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
