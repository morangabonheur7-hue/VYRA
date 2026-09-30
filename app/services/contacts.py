import sqlite3
from typing import Any

from app.core.errors import (
    ConflictError,
    ContactNotFoundError,
    DatabaseError,
)
from app.models.contact import Contact, ContactSource, ContactStatus
from app.schemas.contact import ContactCreate, ContactUpdate


class ContactService:
    """
    Service métier responsable des contacts VYRA.

    Il centralise les opérations liées aux contacts
    afin que les routes API restent simples.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create_contact(
        self,
        *,
        user_id: int,
        data: ContactCreate,
    ) -> Contact:
        """
        Crée un nouveau contact pour un utilisateur.
        """

        self._ensure_user_exists(user_id)

        if self._contact_exists(
            user_id=user_id,
            email=str(data.email) if data.email else None,
            phone=data.phone,
        ):
            raise ConflictError(
                "Un contact avec cet email ou ce numéro existe déjà."
            )

        contact = Contact(
            user_id=user_id,
            first_name=data.first_name,
            last_name=data.last_name,
            company_name=data.company_name,
            email=str(data.email) if data.email else None,
            phone=data.phone,
            position=data.position,
            status=data.status,
            source=data.source,
            notes=data.notes,
        )

        query = """
            INSERT INTO contacts (
                user_id,
                first_name,
                last_name,
                company_name,
                email,
                phone,
                position,
                status,
                source,
                notes,
                is_archived,
                created_at,
                updated_at,
                last_contacted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        values = (
            contact.user_id,
            contact.first_name,
            contact.last_name,
            contact.company_name,
            contact.email,
            contact.phone,
            contact.position,
            contact.status.value,
            contact.source.value,
            contact.notes,
            int(contact.is_archived),
            contact.created_at.isoformat(),
            contact.updated_at.isoformat(),
            (
                contact.last_contacted_at.isoformat()
                if contact.last_contacted_at
                else None
            ),
        )

        try:
            cursor = self.connection.execute(query, values)
            self.connection.commit()
            contact.id = cursor.lastrowid
            return contact

        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise ConflictError(
                "Impossible de créer ce contact.",
                details={"database_error": str(exc)},
            ) from exc

        except sqlite3.Error as exc:
            self.connection.rollback()
            raise DatabaseError(
                "Une erreur est survenue lors de la création du contact."
            ) from exc

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def get_contact(
        self,
        *,
        user_id: int,
        contact_id: int,
    ) -> Contact:
        """
        Récupère un contact appartenant à l'utilisateur.
        """

        query = """
            SELECT *
            FROM contacts
            WHERE id = ?
              AND user_id = ?
            LIMIT 1
        """

        try:
            row = self.connection.execute(
                query,
                (contact_id, user_id),
            ).fetchone()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de récupérer le contact."
            ) from exc

        if row is None:
            raise ContactNotFoundError(
                f"Le contact {contact_id} est introuvable."
            )

        return Contact.from_row(row)

    def list_contacts(
        self,
        *,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        include_archived: bool = False,
        status: ContactStatus | None = None,
        source: ContactSource | None = None,
        search: str | None = None,
    ) -> tuple[list[Contact], int]:
        """
        Retourne les contacts d'un utilisateur avec pagination
        et filtres.
        """

        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        offset = (page - 1) * page_size

        conditions = ["user_id = ?"]
        parameters: list[Any] = [user_id]

        if not include_archived:
            conditions.append("is_archived = 0")

        if status is not None:
            conditions.append("status = ?")
            parameters.append(status.value)

        if source is not None:
            conditions.append("source = ?")
            parameters.append(source.value)

        if search:
            search_value = f"%{search.strip()}%"

            conditions.append(
                """
                (
                    first_name LIKE ?
                    OR last_name LIKE ?
                    OR company_name LIKE ?
                    OR email LIKE ?
                    OR phone LIKE ?
                )
                """
            )

            parameters.extend(
                [
                    search_value,
                    search_value,
                    search_value,
                    search_value,
                    search_value,
                ]
            )

        where_clause = " AND ".join(conditions)

        count_query = f"""
            SELECT COUNT(*)
            FROM contacts
            WHERE {where_clause}
        """

        data_query = f"""
            SELECT *
            FROM contacts
            WHERE {where_clause}
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """

        try:
            total = int(
                self.connection.execute(
                    count_query,
                    parameters,
                ).fetchone()[0]
            )

            rows = self.connection.execute(
                data_query,
                [*parameters, page_size, offset],
            ).fetchall()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de récupérer les contacts."
            ) from exc

        contacts = [
            Contact.from_row(row)
            for row in rows
        ]

        return contacts, total

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update_contact(
        self,
        *,
        user_id: int,
        contact_id: int,
        data: ContactUpdate,
    ) -> Contact:
        """
        Modifie un contact existant.
        """

        contact = self.get_contact(
            user_id=user_id,
            contact_id=contact_id,
        )

        update_data = data.model_dump(
            exclude_unset=True,
        )

        if not update_data:
            return contact

        email = update_data.get("email")
        phone = update_data.get("phone")

        if email is not None:
            email = str(email)

        if (
            email is not None
            or phone is not None
        ):
            if self._contact_exists(
                user_id=user_id,
                email=email,
                phone=phone,
                exclude_contact_id=contact_id,
            ):
                raise ConflictError(
                    "Un autre contact possède déjà cet email "
                    "ou ce numéro."
                )

        contact.update(
            first_name=update_data.get("first_name"),
            last_name=update_data.get("last_name"),
            company_name=update_data.get("company_name"),
            email=email,
            phone=phone,
            position=update_data.get("position"),
            status=update_data.get("status"),
            source=update_data.get("source"),
            notes=update_data.get("notes"),
        )

        query = """
            UPDATE contacts
            SET
                first_name = ?,
                last_name = ?,
                company_name = ?,
                email = ?,
                phone = ?,
                position = ?,
                status = ?,
                source = ?,
                notes = ?,
                is_archived = ?,
                updated_at = ?,
                last_contacted_at = ?
            WHERE id = ?
              AND user_id = ?
        """

        values = (
            contact.first_name,
            contact.last_name,
            contact.company_name,
            contact.email,
            contact.phone,
            contact.position,
            contact.status.value,
            contact.source.value,
            contact.notes,
            int(contact.is_archived),
            contact.updated_at.isoformat(),
            (
                contact.last_contacted_at.isoformat()
                if contact.last_contacted_at
                else None
            ),
            contact.id,
            user_id,
        )

        try:
            self.connection.execute(query, values)
            self.connection.commit()

        except sqlite3.Error as exc:
            self.connection.rollback()
            raise DatabaseError(
                "Impossible de modifier le contact."
            ) from exc

        return contact

    # ------------------------------------------------------------------
    # STATUS / ARCHIVE
    # ------------------------------------------------------------------

    def set_status(
        self,
        *,
        user_id: int,
        contact_id: int,
        status: ContactStatus,
    ) -> Contact:
        """
        Modifie uniquement le statut d'un contact.
        """

        contact = self.get_contact(
            user_id=user_id,
            contact_id=contact_id,
        )

        contact.set_status(status)

        self._save_contact_status(contact)

        return contact

    def archive_contact(
        self,
        *,
        user_id: int,
        contact_id: int,
    ) -> Contact:
        """
        Archive un contact sans le supprimer de la base.
        """

        contact = self.get_contact(
            user_id=user_id,
            contact_id=contact_id,
        )

        contact.archive()

        self._save_archive_state(contact)

        return contact

    def unarchive_contact(
        self,
        *,
        user_id: int,
        contact_id: int,
    ) -> Contact:
        """
        Désarchive un contact.
        """

        contact = self.get_contact(
            user_id=user_id,
            contact_id=contact_id,
        )

        contact.unarchive()

        self._save_archive_state(contact)

        return contact

    # ------------------------------------------------------------------
    # CONTACT ACTIVITY
    # ------------------------------------------------------------------

    def register_contact_activity(
        self,
        *,
        user_id: int,
        contact_id: int,
    ) -> Contact:
        """
        Enregistre le moment du dernier contact avec une personne.
        """

        contact = self.get_contact(
            user_id=user_id,
            contact_id=contact_id,
        )

        contact.register_contact()

        query = """
            UPDATE contacts
            SET
                last_contacted_at = ?,
                updated_at = ?
            WHERE id = ?
              AND user_id = ?
        """

        try:
            self.connection.execute(
                query,
                (
                    contact.last_contacted_at.isoformat()
                    if contact.last_contacted_at
                    else None,
                    contact.updated_at.isoformat(),
                    contact.id,
                    user_id,
                ),
            )
            self.connection.commit()

        except sqlite3.Error as exc:
            self.connection.rollback()
            raise DatabaseError(
                "Impossible d'enregistrer l'activité du contact."
            ) from exc

        return contact

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete_contact(
        self,
        *,
        user_id: int,
        contact_id: int,
    ) -> None:
        """
        Supprime définitivement un contact.

        Cette opération sera utilisée avec prudence.
        L'archivage reste préférable dans la majorité des cas.
        """

        self.get_contact(
            user_id=user_id,
            contact_id=contact_id,
        )

        query = """
            DELETE FROM contacts
            WHERE id = ?
              AND user_id = ?
        """

        try:
            cursor = self.connection.execute(
                query,
                (contact_id, user_id),
            )
            self.connection.commit()

        except sqlite3.Error as exc:
            self.connection.rollback()
            raise DatabaseError(
                "Impossible de supprimer le contact."
            ) from exc

        if cursor.rowcount == 0:
            raise ContactNotFoundError(
                f"Le contact {contact_id} est introuvable."
            )

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    def _ensure_user_exists(
        self,
        user_id: int,
    ) -> None:
        query = """
            SELECT id
            FROM users
            WHERE id = ?
            LIMIT 1
        """

        try:
            row = self.connection.execute(
                query,
                (user_id,),
            ).fetchone()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de vérifier l'utilisateur."
            ) from exc

        if row is None:
            raise ContactNotFoundError(
                "L'utilisateur associé à ce contact "
                "n'existe pas."
            )

    def _contact_exists(
        self,
        *,
        user_id: int,
        email: str | None = None,
        phone: str | None = None,
        exclude_contact_id: int | None = None,
    ) -> bool:
        conditions = ["user_id = ?"]
        parameters: list[Any] = [user_id]

        identifiers = []

        if email:
            identifiers.append("email = ?")
            parameters.append(email)

        if phone:
            identifiers.append("phone = ?")
            parameters.append(phone)

        if not identifiers:
            return False

        conditions.append(
            "(" + " OR ".join(identifiers) + ")"
        )

        if exclude_contact_id is not None:
            conditions.append("id != ?")
            parameters.append(exclude_contact_id)

        query = f"""
            SELECT 1
            FROM contacts
            WHERE {" AND ".join(conditions)}
            LIMIT 1
        """

        try:
            row = self.connection.execute(
                query,
                parameters,
            ).fetchone()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de vérifier l'existence du contact."
            ) from exc

        return row is not None

    def _save_contact_status(
        self,
        contact: Contact,
    ) -> None:
        query = """
            UPDATE contacts
            SET
                status = ?,
                updated_at = ?
            WHERE id = ?
              AND user_id = ?
        """

        try:
            self.connection.execute(
                query,
                (
                    contact.status.value,
                    contact.updated_at.isoformat(),
                    contact.id,
                    contact.user_id,
                ),
            )
            self.connection.commit()

        except sqlite3.Error as exc:
            self.connection.rollback()
            raise DatabaseError(
                "Impossible de modifier le statut du contact."
            ) from exc

    def _save_archive_state(
        self,
        contact: Contact,
    ) -> None:
        query = """
            UPDATE contacts
            SET
                is_archived = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
              AND user_id = ?
        """

        try:
            self.connection.execute(
                query,
                (
                    int(contact.is_archived),
                    contact.status.value,
                    contact.updated_at.isoformat(),
                    contact.id,
                    contact.user_id,
                ),
            )
            self.connection.commit()

        except sqlite3.Error as exc:
            self.connection.rollback()
            raise DatabaseError(
                "Impossible de modifier l'archivage du contact."
            ) from exc