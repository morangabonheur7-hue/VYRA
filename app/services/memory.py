import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.core.errors import DatabaseError, MemoryNotFoundError


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryService:
    """
    Service de mémoire contextuelle de VYRA.

    La mémoire permet de conserver des informations utiles
    concernant un contact ou une conversation afin que
    l'assistant puisse utiliser le contexte lors de futures
    interactions.

    Exemples :
    - préférence du client ;
    - budget annoncé ;
    - produit recherché ;
    - information personnelle utile ;
    - résumé d'une conversation ;
    - besoin identifié.
    """

    TABLE_NAME = "memories"

    def __init__(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        self.connection = connection

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create_memory(
        self,
        *,
        user_id: int,
        contact_id: int | None,
        conversation_id: int | None,
        key: str,
        value: Any,
        memory_type: str = "fact",
        importance: int = 3,
    ) -> dict[str, Any]:
        """
        Crée une nouvelle mémoire.
        """

        key = self._normalize_key(key)
        memory_type = self._normalize_memory_type(memory_type)
        importance = self._normalize_importance(importance)

        self._validate_related_entities(
            user_id=user_id,
            contact_id=contact_id,
            conversation_id=conversation_id,
        )

        now = utc_now().isoformat()

        query = """
            INSERT INTO memories (
                user_id,
                contact_id,
                conversation_id,
                memory_key,
                memory_value,
                memory_type,
                importance,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        try:
            cursor = self.connection.execute(
                query,
                (
                    user_id,
                    contact_id,
                    conversation_id,
                    key,
                    json.dumps(
                        value,
                        ensure_ascii=False,
                    ),
                    memory_type,
                    importance,
                    now,
                    now,
                ),
            )

            self.connection.commit()

            return self.get_memory(
                user_id=user_id,
                memory_id=cursor.lastrowid,
            )

        except sqlite3.IntegrityError as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Impossible de créer la mémoire.",
                details={"database_error": str(exc)},
            ) from exc

        except sqlite3.Error as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Une erreur est survenue lors de la création "
                "de la mémoire."
            ) from exc

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def get_memory(
        self,
        *,
        user_id: int,
        memory_id: int,
    ) -> dict[str, Any]:
        """
        Récupère une mémoire.
        """

        query = """
            SELECT *
            FROM memories
            WHERE id = ?
              AND user_id = ?
            LIMIT 1
        """

        try:
            row = self.connection.execute(
                query,
                (
                    memory_id,
                    user_id,
                ),
            ).fetchone()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de récupérer la mémoire."
            ) from exc

        if row is None:
            raise MemoryNotFoundError(
                f"La mémoire {memory_id} est introuvable."
            )

        return self._row_to_dict(row)

    def list_memories(
        self,
        *,
        user_id: int,
        contact_id: int | None = None,
        conversation_id: int | None = None,
        memory_type: str | None = None,
        minimum_importance: int = 1,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Récupère les mémoires pertinentes pour un utilisateur,
        contact ou conversation.
        """

        limit = min(max(limit, 1), 500)
        minimum_importance = self._normalize_importance(
            minimum_importance
        )

        conditions = ["user_id = ?"]
        parameters: list[Any] = [user_id]

        if contact_id is not None:
            conditions.append("contact_id = ?")
            parameters.append(contact_id)

        if conversation_id is not None:
            conditions.append("conversation_id = ?")
            parameters.append(conversation_id)

        if memory_type is not None:
            conditions.append("memory_type = ?")
            parameters.append(
                self._normalize_memory_type(memory_type)
            )

        conditions.append("importance >= ?")
        parameters.append(minimum_importance)

        query = f"""
            SELECT *
            FROM memories
            WHERE {" AND ".join(conditions)}
            ORDER BY importance DESC, updated_at DESC
            LIMIT ?
        """

        parameters.append(limit)

        try:
            rows = self.connection.execute(
                query,
                parameters,
            ).fetchall()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de récupérer les mémoires."
            ) from exc

        return [
            self._row_to_dict(row)
            for row in rows
        ]

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update_memory(
        self,
        *,
        user_id: int,
        memory_id: int,
        value: Any | None = None,
        memory_type: str | None = None,
        importance: int | None = None,
    ) -> dict[str, Any]:
        """
        Met à jour une mémoire existante.
        """

        memory = self.get_memory(
            user_id=user_id,
            memory_id=memory_id,
        )

        new_value = (
            value
            if value is not None
            else memory["value"]
        )

        new_type = (
            self._normalize_memory_type(memory_type)
            if memory_type is not None
            else memory["memory_type"]
        )

        new_importance = (
            self._normalize_importance(importance)
            if importance is not None
            else memory["importance"]
        )

        updated_at = utc_now().isoformat()

        query = """
            UPDATE memories
            SET
                memory_value = ?,
                memory_type = ?,
                importance = ?,
                updated_at = ?
            WHERE id = ?
              AND user_id = ?
        """

        try:
            self.connection.execute(
                query,
                (
                    json.dumps(
                        new_value,
                        ensure_ascii=False,
                    ),
                    new_type,
                    new_importance,
                    updated_at,
                    memory_id,
                    user_id,
                ),
            )

            self.connection.commit()

        except sqlite3.Error as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Impossible de modifier la mémoire."
            ) from exc

        return self.get_memory(
            user_id=user_id,
            memory_id=memory_id,
        )

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete_memory(
        self,
        *,
        user_id: int,
        memory_id: int,
    ) -> None:
        """
        Supprime une mémoire.
        """

        self.get_memory(
            user_id=user_id,
            memory_id=memory_id,
        )

        query = """
            DELETE FROM memories
            WHERE id = ?
              AND user_id = ?
        """

        try:
            cursor = self.connection.execute(
                query,
                (
                    memory_id,
                    user_id,
                ),
            )

            self.connection.commit()

        except sqlite3.Error as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Impossible de supprimer la mémoire."
            ) from exc

        if cursor.rowcount == 0:
            raise MemoryNotFoundError(
                f"La mémoire {memory_id} est introuvable."
            )

    # ------------------------------------------------------------------
    # CONTEXT
    # ------------------------------------------------------------------

    def build_context(
        self,
        *,
        user_id: int,
        contact_id: int | None = None,
        conversation_id: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Construit un contexte propre à transmettre plus tard
        au système IA.
        """

        memories = self.list_memories(
            user_id=user_id,
            contact_id=contact_id,
            conversation_id=conversation_id,
            minimum_importance=1,
            limit=limit,
        )

        return [
            {
                "key": memory["key"],
                "value": memory["value"],
                "type": memory["memory_type"],
                "importance": memory["importance"],
            }
            for memory in memories
        ]

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_key(key: str) -> str:
        if not isinstance(key, str):
            raise TypeError(
                "La clé de mémoire doit être une chaîne."
            )

        key = key.strip()

        if not key:
            raise ValueError(
                "La clé de mémoire ne peut pas être vide."
            )

        return key[:200]

    @staticmethod
    def _normalize_memory_type(
        memory_type: str,
    ) -> str:
        if not isinstance(memory_type, str):
            raise TypeError(
                "Le type de mémoire doit être une chaîne."
            )

        memory_type = memory_type.strip().lower()

        allowed_types = {
            "fact",
            "preference",
            "need",
            "budget",
            "product",
            "context",
            "summary",
            "other",
        }

        if memory_type not in allowed_types:
            raise ValueError(
                f"Type de mémoire invalide : {memory_type!r}"
            )

        return memory_type

    @staticmethod
    def _normalize_importance(
        importance: int,
    ) -> int:
        try:
            importance = int(importance)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "L'importance doit être un nombre entier."
            ) from exc

        return min(max(importance, 1), 5)

    def _validate_related_entities(
        self,
        *,
        user_id: int,
        contact_id: int | None,
        conversation_id: int | None,
    ) -> None:
        if contact_id is not None:
            query = """
                SELECT id
                FROM contacts
                WHERE id = ?
                  AND user_id = ?
                LIMIT 1
            """

            try:
                row = self.connection.execute(
                    query,
                    (
                        contact_id,
                        user_id,
                    ),
                ).fetchone()

            except sqlite3.Error as exc:
                raise DatabaseError(
                    "Impossible de vérifier le contact."
                ) from exc

            if row is None:
                raise MemoryNotFoundError(
                    "Le contact associé à la mémoire "
                    "n'existe pas."
                )

        if conversation_id is not None:
            query = """
                SELECT id
                FROM conversations
                WHERE id = ?
                  AND user_id = ?
                LIMIT 1
            """

            try:
                row = self.connection.execute(
                    query,
                    (
                        conversation_id,
                        user_id,
                    ),
                ).fetchone()

            except sqlite3.Error as exc:
                raise DatabaseError(
                    "Impossible de vérifier la conversation."
                ) from exc

            if row is None:
                raise MemoryNotFoundError(
                    "La conversation associée à la mémoire "
                    "n'existe pas."
                )

    @staticmethod
    def _row_to_dict(
        row: sqlite3.Row,
    ) -> dict[str, Any]:
        raw_value = row["memory_value"]

        try:
            value = json.loads(raw_value)
        except (TypeError, json.JSONDecodeError):
            value = raw_value

        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "contact_id": row["contact_id"],
            "conversation_id": row["conversation_id"],
            "key": row["memory_key"],
            "value": value,
            "memory_type": row["memory_type"],
            "importance": row["importance"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }