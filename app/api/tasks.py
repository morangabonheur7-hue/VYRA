from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.auth import get_current_user
from app.core.database import get_db
from app.core.errors import (
    DatabaseError,
    TaskNotFoundError,
)
from app.models.task import TaskPriority, TaskStatus
from app.models.user import User
from app.schemas.task import (
    TaskCreate,
    TaskDueDateUpdate,
    TaskListResponse,
    TaskPriorityUpdate,
    TaskReminderUpdate,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services.tasks import TaskService


router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
)


# ======================================================================
# CREATE
# ======================================================================


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> TaskResponse:
    """
    Crée une nouvelle tâche pour l'utilisateur connecté.
    """

    service = TaskService(connection)

    try:
        task = service.create_task(
            user_id=current_user.id,
            data=data,
        )

    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return TaskResponse(
        **task.to_dict()
    )


# ======================================================================
# LIST
# ======================================================================


@router.get(
    "",
    response_model=TaskListResponse,
)
def list_tasks(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    task_status: TaskStatus | None = Query(
        default=None,
        alias="status",
    ),
    priority: TaskPriority | None = Query(
        default=None,
    ),
    contact_id: int | None = Query(
        default=None,
        gt=0,
    ),
    conversation_id: int | None = Query(
        default=None,
        gt=0,
    ),
    overdue_only: bool = Query(
        default=False,
    ),
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> TaskListResponse:
    """
    Retourne les tâches de l'utilisateur connecté.
    """

    service = TaskService(connection)

    try:
        tasks, total = service.list_tasks(
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            status=task_status,
            priority=priority,
            contact_id=contact_id,
            conversation_id=conversation_id,
            overdue_only=overdue_only,
        )

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return TaskListResponse(
        items=[
            TaskResponse(
                **task.to_dict()
            )
            for task in tasks
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ======================================================================
# DUE TASKS
# ======================================================================


@router.get(
    "/due",
    response_model=list[TaskResponse],
)
def list_due_tasks(
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> list[TaskResponse]:
    """
    Retourne les tâches dont le rappel doit être traité.
    """

    service = TaskService(connection)

    try:
        tasks = service.list_due_tasks(
            user_id=current_user.id,
            limit=limit,
        )

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return [
        TaskResponse(
            **task.to_dict()
        )
        for task in tasks
    ]


# ======================================================================
# GET ONE
# ======================================================================


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> TaskResponse:
    """
    Retourne une tâche appartenant à l'utilisateur connecté.
    """

    service = TaskService(connection)

    try:
        task = service.get_task(
            user_id=current_user.id,
            task_id=task_id,
        )

    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return TaskResponse(
        **task.to_dict()
    )


# ======================================================================
# UPDATE
# ======================================================================


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
)
def update_task(
    task_id: int,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> TaskResponse:
    """
    Modifie une tâche.
    """

    service = TaskService(connection)

    try:
        task = service.update_task(
            user_id=current_user.id,
            task_id=task_id,
            data=data,
        )

    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return TaskResponse(
        **task.to_dict()
    )


# ======================================================================
# START
# ======================================================================


@router.post(
    "/{task_id}/start",
    response_model=TaskResponse,
)
def start_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> TaskResponse:
    """
    Passe une tâche à l'état 'in_progress'.
    """

    service = TaskService(connection)

    try:
        task = service.start_task(
            user_id=current_user.id,
            task_id=task_id,
        )

    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return TaskResponse(
        **task.to_dict()
    )


# ======================================================================
# COMPLETE
# ======================================================================


@router.post(
    "/{task_id}/complete",
    response_model=TaskResponse,
)
def complete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> TaskResponse:
    """
    Termine une tâche.
    """

    service = TaskService(connection)

    try:
        task = service.complete_task(
            user_id=current_user.id,
            task_id=task_id,
        )

    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return TaskResponse(
        **task.to_dict()
    )


# ======================================================================
# CANCEL
# ======================================================================


@router.post(
    "/{task_id}/cancel",
    response_model=TaskResponse,
)
def cancel_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> TaskResponse:
    """
    Annule une tâche.
    """

    service = TaskService(connection)

    try:
        task = service.cancel_task(
            user_id=current_user.id,
            task_id=task_id,
        )

    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return TaskResponse(
        **task.to_dict()
    )


# ======================================================================
# REOPEN
# ======================================================================


@router.post(
    "/{task_id}/reopen",
    response_model=TaskResponse,
)
def reopen_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> TaskResponse:
    """
    Réouvre une tâche terminée ou annulée.
    """

    service = TaskService(connection)

    try:
        task = service.reopen_task(
            user_id=current_user.id,
            task_id=task_id,
        )

    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return TaskResponse(
        **task.to_dict()
    )


# ======================================================================
# PRIORITY
# ======================================================================


@router.patch(
    "/{task_id}/priority",
    response_model=TaskResponse,
)
def update_task_priority(
    task_id: int,
    data: TaskPriorityUpdate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> TaskResponse:
    """
    Modifie la priorité d'une tâche.
    """

    service = TaskService(connection)

    try:
        task = service.update_task(
            user_id=current_user.id,
            task_id=task_id,
            data=TaskUpdate(
                priority=data.priority
            ),
        )

    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return TaskResponse(
        **task.to_dict()
    )


# ======================================================================
# STATUS
# ======================================================================


@router.patch(
    "/{task_id}/status",
    response_model=TaskResponse,
)
def update_task_status(
    task_id: int,
    data: TaskStatusUpdate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> TaskResponse:
    """
    Modifie directement le statut d'une tâche.
    """

    service = TaskService(connection)

    try:
        task = service.update_task(
            user_id=current_user.id,
            task_id=task_id,
            data=TaskUpdate(
                status=data.status
            ),
        )

    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return TaskResponse(
        **task.to_dict()
    )


# ======================================================================
# REMINDER ENABLE / DISABLE
# ======================================================================


@router.patch(
    "/{task_id}/reminder",
    response_model=TaskResponse,
)
def update_task_reminder(
    task_id: int,
    data: TaskReminderUpdate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> TaskResponse:
    """
    Active ou désactive le rappel d'une tâche.
    """

    service = TaskService(connection)

    try:
        if data.reminder_enabled:
            task = service.enable_reminder(
                user_id=current_user.id,
                task_id=task_id,
            )
        else:
            task = service.disable_reminder(
                user_id=current_user.id,
                task_id=task_id,
            )

    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return TaskResponse(
        **task.to_dict()
    )


# ======================================================================
# REMINDER SENT
# ======================================================================


@router.post(
    "/{task_id}/reminder/sent",
    response_model=TaskResponse,
)
def mark_reminder_sent(
    task_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> TaskResponse:
    """
    Marque le rappel comme envoyé.
    """

    service = TaskService(connection)

    try:
        task = service.mark_reminder_sent(
            user_id=current_user.id,
            task_id=task_id,
        )

    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return TaskResponse(
        **task.to_dict()
    )


# ======================================================================
# DUE DATE
# ======================================================================


@router.patch(
    "/{task_id}/due-date",
    response_model=TaskResponse,
)
def update_task_due_date(
    task_id: int,
    data: TaskDueDateUpdate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> TaskResponse:
    """
    Définit ou modifie la date d'échéance.
    """

    service = TaskService(connection)

    try:
        task = service.set_due_date(
            user_id=current_user.id,
            task_id=task_id,
            due_at=data.due_at,
        )

    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return TaskResponse(
        **task.to_dict()
    )


# ======================================================================
# CLEAR DUE DATE
# ======================================================================


@router.delete(
    "/{task_id}/due-date",
    response_model=TaskResponse,
)
def clear_task_due_date(
    task_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> TaskResponse:
    """
    Supprime la date d'échéance d'une tâche.
    """

    service = TaskService(connection)

    try:
        task = service.clear_due_date(
            user_id=current_user.id,
            task_id=task_id,
        )

    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return TaskResponse(
        **task.to_dict()
    )


# ======================================================================
# DELETE
# ======================================================================


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> None:
    """
    Supprime définitivement une tâche.
    """

    service = TaskService(connection)

    try:
        service.delete_task(
            user_id=current_user.id,
            task_id=task_id,
        )

    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc