from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> datetime:
    """
    Retourne la date et l'heure actuelles en UTC.
    """

    return datetime.now(timezone.utc)


class TaskStatus(str, Enum):
    """
    Statut d'une tâche.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """
    Niveau de priorité d'une tâche.
    """

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Task:
    """
    Modèle représentant une tâche ou un rappel dans VYRA.

    Une tâche appartient à un utilisateur.

    Elle peut éventuellement être liée à :
        - un contact ;
        - une conversation.

    Exemple :
        "Relancer le prospect demain à 10h."
    """

    TABLE_NAME = "tasks"

    def __init__(
        self,
        *,
        task_id: int | None = None,
        user_id: int,
        title: str,
        description: str | None = None,
        status: TaskStatus | str = TaskStatus.PENDING,
        priority: TaskPriority | str = TaskPriority.NORMAL,
        contact_id: int | None = None,
        conversation_id: int | None = None,
        due_at: datetime | None = None,
        completed_at: datetime | None = None,
        reminder_enabled: bool = True,
        reminder_sent: bool = False,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.id = task_id
        self.user_id = user_id

        self.title = self._normalize_title(title)

        self.description = (
            description.strip()
            if description
            else None
        )

        self.status = self._normalize_status(status)
        self.priority = self._normalize_priority(priority)

        self.contact_id = contact_id
        self.conversation_id = conversation_id

        self.due_at = due_at
        self.completed_at = completed_at

        self.reminder_enabled = bool(reminder_enabled)
        self.reminder_sent = bool(reminder_sent)

        self.created_at = created_at or utc_now()
        self.updated_at = updated_at or self.created_at

    # ==========================================================
    # NORMALISATION
    # ==========================================================

    @staticmethod
    def _normalize_title(title: str) -> str:
        """
        Nettoie et valide le titre de la tâche.
        """

        if not isinstance(title, str):
            raise TypeError(
                "Le titre de la tâche doit être une chaîne de caractères."
            )

        normalized = title.strip()

        if not normalized:
            raise ValueError(
                "Le titre de la tâche ne peut pas être vide."
            )

        return normalized

    @staticmethod
    def _normalize_status(
        status: TaskStatus | str,
    ) -> TaskStatus:
        """
        Convertit une valeur en TaskStatus.
        """

        if isinstance(status, TaskStatus):
            return status

        try:
            return TaskStatus(
                status.strip().lower()
            )
        except ValueError as exc:
            raise ValueError(
                f"Statut de tâche invalide : {status!r}"
            ) from exc

    @staticmethod
    def _normalize_priority(
        priority: TaskPriority | str,
    ) -> TaskPriority:
        """
        Convertit une valeur en TaskPriority.
        """

        if isinstance(priority, TaskPriority):
            return priority

        try:
            return TaskPriority(
                priority.strip().lower()
            )
        except ValueError as exc:
            raise ValueError(
                f"Priorité de tâche invalide : {priority!r}"
            ) from exc

    # ==========================================================
    # PROPRIÉTÉS
    # ==========================================================

    @property
    def is_pending(self) -> bool:
        """
        Indique si la tâche est encore en attente.
        """

        return self.status == TaskStatus.PENDING

    @property
    def is_in_progress(self) -> bool:
        """
        Indique si la tâche est actuellement en cours.
        """

        return self.status == TaskStatus.IN_PROGRESS

    @property
    def is_completed(self) -> bool:
        """
        Indique si la tâche est terminée.
        """

        return self.status == TaskStatus.COMPLETED

    @property
    def is_cancelled(self) -> bool:
        """
        Indique si la tâche a été annulée.
        """

        return self.status == TaskStatus.CANCELLED

    @property
    def is_overdue(self) -> bool:
        """
        Indique si la tâche est en retard.

        Une tâche sans date d'échéance ne peut pas être
        considérée comme en retard.
        """

        if self.due_at is None:
            return False

        if self.is_completed or self.is_cancelled:
            return False

        return self.due_at < utc_now()

    @property
    def has_reminder(self) -> bool:
        """
        Indique si un rappel doit être géré pour cette tâche.
        """

        return (
            self.reminder_enabled
            and self.due_at is not None
            and not self.reminder_sent
            and not self.is_completed
            and not self.is_cancelled
        )

    @property
    def has_contact(self) -> bool:
        """
        Indique si la tâche est liée à un contact.
        """

        return self.contact_id is not None

    @property
    def has_conversation(self) -> bool:
        """
        Indique si la tâche est liée à une conversation.
        """

        return self.conversation_id is not None

    # ==========================================================
    # STATUT
    # ==========================================================

    def start(self) -> None:
        """
        Commence l'exécution de la tâche.
        """

        if self.is_completed:
            raise ValueError(
                "Une tâche terminée ne peut pas être relancée."
            )

        if self.is_cancelled:
            raise ValueError(
                "Une tâche annulée doit être réactivée "
                "avant de pouvoir commencer."
            )

        self.status = TaskStatus.IN_PROGRESS
        self.touch()

    def complete(self) -> None:
        """
        Marque la tâche comme terminée.
        """

        if self.is_cancelled:
            raise ValueError(
                "Une tâche annulée ne peut pas être terminée."
            )

        self.status = TaskStatus.COMPLETED
        self.completed_at = utc_now()
        self.touch()

    def cancel(self) -> None:
        """
        Annule la tâche.
        """

        if self.is_completed:
            raise ValueError(
                "Une tâche terminée ne peut pas être annulée."
            )

        self.status = TaskStatus.CANCELLED
        self.touch()

    def reopen(self) -> None:
        """
        Réouvre une tâche terminée ou annulée.
        """

        self.status = TaskStatus.PENDING
        self.completed_at = None
        self.reminder_sent = False
        self.touch()

    # ==========================================================
    # PRIORITÉ
    # ==========================================================

    def set_priority(
        self,
        priority: TaskPriority | str,
    ) -> None:
        """
        Modifie la priorité de la tâche.
        """

        self.priority = self._normalize_priority(priority)
        self.touch()

    # ==========================================================
    # RAPPELS
    # ==========================================================

    def enable_reminder(self) -> None:
        """
        Active le rappel.
        """

        self.reminder_enabled = True
        self.reminder_sent = False
        self.touch()

    def disable_reminder(self) -> None:
        """
        Désactive le rappel.
        """

        self.reminder_enabled = False
        self.touch()

    def mark_reminder_sent(self) -> None:
        """
        Indique que le rappel a été envoyé.
        """

        if not self.reminder_enabled:
            raise ValueError(
                "Le rappel est désactivé pour cette tâche."
            )

        self.reminder_sent = True
        self.touch()

    # ==========================================================
    # ÉCHÉANCE
    # ==========================================================

    def set_due_at(
        self,
        due_at: datetime | None,
    ) -> None:
        """
        Définit ou modifie la date d'échéance.
        """

        self.due_at = due_at
        self.reminder_sent = False
        self.touch()

    def clear_due_date(self) -> None:
        """
        Supprime la date d'échéance.
        """

        self.due_at = None
        self.reminder_sent = False
        self.touch()
# ==========================================================
    # MISE À JOUR
    # ==========================================================

    def update(
        self,
        *,
        title: str | None = None,
        description: str | None = None,
        status: TaskStatus | str | None = None,
        priority: TaskPriority | str | None = None,
        contact_id: int | None = None,
        conversation_id: int | None = None,
        due_at: datetime | None = None,
        reminder_enabled: bool | None = None,
    ) -> None:
        """
        Met à jour les informations modifiables de la tâche.

        Seuls les champs explicitement fournis sont modifiés.
        """

        if title is not None:
            self.title = self._normalize_title(title)

        if description is not None:
            self.description = (
                description.strip()
                or None
            )

        if status is not None:
            self.status = self._normalize_status(status)

            if self.status == TaskStatus.COMPLETED:
                self.completed_at = utc_now()

        if priority is not None:
            self.priority = self._normalize_priority(priority)

        if contact_id is not None:
            self.contact_id = contact_id

        if conversation_id is not None:
            self.conversation_id = conversation_id

        if due_at is not None:
            self.due_at = due_at
            self.reminder_sent = False

        if reminder_enabled is not None:
            self.reminder_enabled = bool(
                reminder_enabled
            )

        self.touch()

    def touch(self) -> None:
        """
        Met à jour la date de modification.
        """

        self.updated_at = utc_now()

    # ==========================================================
    # VALIDATION MÉTIER
    # ==========================================================

    def belongs_to_user(
        self,
        user_id: int,
    ) -> bool:
        """
        Vérifie que la tâche appartient à l'utilisateur indiqué.
        """

        return self.user_id == user_id

    def should_send_reminder(self) -> bool:
        """
        Détermine si un rappel doit actuellement être envoyé.
        """

        if not self.has_reminder:
            return False

        if self.due_at is None:
            return False

        return self.due_at <= utc_now()

    # ==========================================================
    # CONVERSION
    # ==========================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convertit la tâche en dictionnaire.
        """

        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "contact_id": self.contact_id,
            "conversation_id": self.conversation_id,
            "due_at": (
                self.due_at.isoformat()
                if self.due_at
                else None
            ),
            "completed_at": (
                self.completed_at.isoformat()
                if self.completed_at
                else None
            ),
            "reminder_enabled": self.reminder_enabled,
            "reminder_sent": self.reminder_sent,
            "is_pending": self.is_pending,
            "is_in_progress": self.is_in_progress,
            "is_completed": self.is_completed,
            "is_cancelled": self.is_cancelled,
            "is_overdue": self.is_overdue,
            "has_reminder": self.has_reminder,
            "has_contact": self.has_contact,
            "has_conversation": self.has_conversation,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_database_dict(self) -> dict[str, Any]:
        """
        Prépare les données pour SQLite.
        """

        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "contact_id": self.contact_id,
            "conversation_id": self.conversation_id,
            "due_at": (
                self.due_at.isoformat()
                if self.due_at
                else None
            ),
            "completed_at": (
                self.completed_at.isoformat()
                if self.completed_at
                else None
            ),
            "reminder_enabled": int(
                self.reminder_enabled
            ),
            "reminder_sent": int(
                self.reminder_sent
            ),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    # ==========================================================
    # DATABASE
    # ==========================================================

    @classmethod
    def from_row(cls, row: Any) -> "Task":
        """
        Construit une Task à partir d'une ligne SQLite.
        """

        def parse_datetime(
            value: Any,
        ) -> datetime | None:
            if value is None:
                return None

            if isinstance(value, datetime):
                return value

            return datetime.fromisoformat(str(value))

        return cls(
            task_id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            description=row["description"],
            status=row["status"],
            priority=row["priority"],
            contact_id=row["contact_id"],
            conversation_id=row["conversation_id"],
            due_at=parse_datetime(row["due_at"]),
            completed_at=parse_datetime(
                row["completed_at"]
            ),
            reminder_enabled=bool(
                row["reminder_enabled"]
            ),
            reminder_sent=bool(
                row["reminder_sent"]
            ),
            created_at=parse_datetime(
                row["created_at"]
            ),
            updated_at=parse_datetime(
                row["updated_at"]
            ),
        )

    # ==========================================================
    # REPRÉSENTATION
    # ==========================================================

    def __repr__(self) -> str:
        """
        Représentation utile pendant le développement.
        """

        return (
            f"Task("
            f"id={self.id!r}, "
            f"user_id={self.user_id!r}, "
            f"title={self.title!r}, "
            f"status={self.status.value!r}, "
            f"priority={self.priority.value!r}, "
            f"due_at={self.due_at!r}"
            f")"
        )