from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskPriority, TaskStatus


class TaskBase(BaseModel):
    """
    Données communes d'une tâche VYRA.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    title: str = Field(
        ...,
        min_length=1,
        max_length=300,
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
    )
    priority: TaskPriority = TaskPriority.NORMAL
    contact_id: int | None = Field(
        default=None,
        gt=0,
    )
    conversation_id: int | None = Field(
        default=None,
        gt=0,
    )
    due_at: datetime | None = None
    reminder_enabled: bool = True

    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None


class TaskCreate(TaskBase):
    """
    Données nécessaires pour créer une tâche.
    """

    pass


class TaskUpdate(BaseModel):
    """
    Données modifiables après création d'une tâche.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=300,
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
    )
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    contact_id: int | None = Field(
        default=None,
        gt=0,
    )
    conversation_id: int | None = Field(
        default=None,
        gt=0,
    )
    due_at: datetime | None = None
    reminder_enabled: bool | None = None

    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None


class TaskResponse(BaseModel):
    """
    Représentation publique d'une tâche.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    id: int
    user_id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    contact_id: int | None
    conversation_id: int | None
    due_at: datetime | None
    completed_at: datetime | None
    reminder_enabled: bool
    reminder_sent: bool
    is_pending: bool
    is_in_progress: bool
    is_completed: bool
    is_cancelled: bool
    is_overdue: bool
    has_reminder: bool
    has_contact: bool
    has_conversation: bool
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    """
    Réponse utilisée lorsqu'une liste de tâches est renvoyée.
    """

    items: list[TaskResponse]
    total: int
    page: int = Field(
        default=1,
        ge=1,
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
    )


class TaskStatusUpdate(BaseModel):
    """
    Modification dédiée du statut d'une tâche.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    status: TaskStatus


class TaskPriorityUpdate(BaseModel):
    """
    Modification dédiée de la priorité.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    priority: TaskPriority


class TaskReminderUpdate(BaseModel):
    """
    Activation ou désactivation du rappel.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    reminder_enabled: bool


class TaskDueDateUpdate(BaseModel):
    """
    Modification de la date d'échéance.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    due_at: datetime | None