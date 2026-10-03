from datetime import datetime
from typing import Any

import psycopg

from app.core.errors import (
    DatabaseError,
    TaskNotFoundError,
)
from app.models.task import Task, TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    """
    Service métier responsable des tâches VYRA.

    Il gère :
    - création ;
    - récupération ;
    - recherche ;
    - modification ;
    - statuts ;
    - échéances ;
    - rappels ;
    - suppression.
    """

    def __init__(
        self,
        connection: Any,
    ) -> None:
        self.connection = connection

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create_task(
        self,
        *,
        user_id: int,
        data: TaskCreate,
    ) -> Task:

        self._validate_related_entities(
            user_id=user_id,
            contact_id=data.contact_id,
            conversation_id=data.conversation_id,
        )

        task = Task(
            user_id=user_id,
            title=data.title,
            description=data.description,
            priority=data.priority,
            contact_id=data.contact_id,
            conversation_id=data.conversation_id,
            due_at=data.due_at,
            reminder_enabled=data.reminder_enabled,
        )

        query = """
            INSERT INTO tasks (
                user_id,
                title,
                description,
                status,
                priority,
                contact_id,
                conversation_id,
                due_at,
                completed_at,
                reminder_enabled,
                reminder_sent,
                created_at,
                updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            RETURNING id
        """

        values = (
            task.user_id,
            task.title,
            task.description,
            task.status.value,
            task.priority.value,
            task.contact_id,
            task.conversation_id,
            task.due_at.isoformat()
            if task.due_at
            else None,
            None,
            task.reminder_enabled,
            task.reminder_sent,
            task.created_at.isoformat(),
            task.updated_at.isoformat(),
        )

        try:
            row = self.connection.execute(
                query,
                values,
            ).fetchone()

            self.connection.commit()

            task.id = row["id"]

            return task

        except psycopg.IntegrityError as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Impossible de créer la tâche.",
                details={
                    "database_error": str(exc),
                },
            ) from exc

        except psycopg.Error as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Une erreur est survenue lors de la création "
                "de la tâche."
            ) from exc

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def get_task(
        self,
        *,
        user_id: int,
        task_id: int,
    ) -> Task:

        query = """
            SELECT *
            FROM tasks
            WHERE id = %s
              AND user_id = %s
            LIMIT 1
        """

        try:
            row = self.connection.execute(
                query,
                (
                    task_id,
                    user_id,
                ),
            ).fetchone()

        except psycopg.Error as exc:
            raise DatabaseError(
                "Impossible de récupérer la tâche."
            ) from exc

        if row is None:
            raise TaskNotFoundError(
                f"La tâche {task_id} est introuvable."
            )

        return Task.from_row(row)

    def list_tasks(
        self,
        *,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        contact_id: int | None = None,
        conversation_id: int | None = None,
        overdue_only: bool = False,
    ) -> tuple[list[Task], int]:

        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        offset = (page - 1) * page_size

        conditions = ["user_id = %s"]
        parameters: list[Any] = [user_id]

        if status is not None:
            conditions.append("status = %s")
            parameters.append(status.value)

        if priority is not None:
            conditions.append("priority = %s")
            parameters.append(priority.value)

        if contact_id is not None:
            conditions.append("contact_id = %s")
            parameters.append(contact_id)

        if conversation_id is not None:
            conditions.append("conversation_id = %s")
            parameters.append(conversation_id)

        if overdue_only:
            conditions.append(
                """
                due_at IS NOT NULL
                AND due_at < %s
                AND status NOT IN (%s, %s)
                """
            )

            parameters.extend(
                [
                    datetime.now().isoformat(),
                    TaskStatus.COMPLETED.value,
                    TaskStatus.CANCELLED.value,
                ]
            )

        where_clause = " AND ".join(conditions)

        count_query = f"""
            SELECT COUNT(*) AS total
            FROM tasks
            WHERE {where_clause}
        """

        data_query = f"""
            SELECT *
            FROM tasks
            WHERE {where_clause}
            ORDER BY
                CASE priority
                    WHEN 'urgent' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'normal' THEN 3
                    WHEN 'low' THEN 4
                    ELSE 5
                END,
                CASE
                    WHEN due_at IS NULL THEN 1
                    ELSE 0
                END,
                due_at ASC,
                created_at DESC
            LIMIT %s OFFSET %s
        """

        try:
            count_row = self.connection.execute(
                count_query,
                parameters,
            ).fetchone()

            total = int(count_row["total"])

            rows = self.connection.execute(
                data_query,
                [
                    *parameters,
                    page_size,
                    offset,
                ],
            ).fetchall()

        except psycopg.Error as exc:
            raise DatabaseError(
                "Impossible de récupérer les tâches."
            ) from exc

        tasks = [
            Task.from_row(row)
            for row in rows
        ]

        return tasks, total

    def list_due_tasks(
        self,
        *,
        user_id: int,
        limit: int = 100,
    ) -> list[Task]:

        limit = min(max(limit, 1), 500)

        query = """
            SELECT *
            FROM tasks
            WHERE user_id = %s
              AND due_at IS NOT NULL
              AND due_at <= %s
              AND reminder_enabled = TRUE
              AND reminder_sent = FALSE
              AND status NOT IN (%s, %s)
            ORDER BY due_at ASC
            LIMIT %s
        """

        try:
            rows = self.connection.execute(
                query,
                (
                    user_id,
                    datetime.now().isoformat(),
                    TaskStatus.COMPLETED.value,
                    TaskStatus.CANCELLED.value,
                    limit,
                ),
            ).fetchall()

        except psycopg.Error as exc:
            raise DatabaseError(
                "Impossible de récupérer les rappels à envoyer."
            ) from exc

        return [
            Task.from_row(row)
            for row in rows
        ]

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update_task(
        self,
        *,
        user_id: int,
        task_id: int,
        data: TaskUpdate,
    ) -> Task:

        task = self.get_task(
            user_id=user_id,
            task_id=task_id,
        )

        update_data = data.model_dump(
            exclude_unset=True,
        )

        if not update_data:
            return task

        self._validate_related_entities(
            user_id=user_id,
            contact_id=update_data.get("contact_id"),
            conversation_id=update_data.get("conversation_id"),
        )

        task.update(
            title=update_data.get("title"),
            description=update_data.get("description"),
            status=update_data.get("status"),
            priority=update_data.get("priority"),
            contact_id=update_data.get("contact_id"),
            conversation_id=update_data.get("conversation_id"),
            due_at=update_data.get("due_at"),
            reminder_enabled=update_data.get(
                "reminder_enabled"
            ),
        )

        self._save_task(task)

        return task

    # ------------------------------------------------------------------
    # STATUS
    # ------------------------------------------------------------------

    def start_task(
        self,
        *,
        user_id: int,
        task_id: int,
    ) -> Task:

        task = self.get_task(
            user_id=user_id,
            task_id=task_id,
        )

        task.start()

        self._save_task(task)

        return task

    def complete_task(
        self,
        *,
        user_id: int,
        task_id: int,
    ) -> Task:

        task = self.get_task(
            user_id=user_id,
            task_id=task_id,
        )

        task.complete()

        self._save_task(task)

        return task

    def cancel_task(
        self,
        *,
        user_id: int,
        task_id: int,
    ) -> Task:

        task = self.get_task(
            user_id=user_id,
            task_id=task_id,
        )

        task.cancel()

        self._save_task(task)

        return task

    def reopen_task(
        self,
        *,
        user_id: int,
        task_id: int,
    ) -> Task:

        task = self.get_task(
            user_id=user_id,
            task_id=task_id,
        )

        task.reopen()

        self._save_task(task)

        return task

    # ------------------------------------------------------------------
    # REMINDERS
    # ------------------------------------------------------------------

    def enable_reminder(
        self,
        *,
        user_id: int,
        task_id: int,
    ) -> Task:

        task = self.get_task(
            user_id=user_id,
            task_id=task_id,
        )

        task.enable_reminder()

        self._save_task(task)

        return task

    def disable_reminder(
        self,
        *,
        user_id: int,
        task_id: int,
    ) -> Task:

        task = self.get_task(
            user_id=user_id,
            task_id=task_id,
        )

        task.disable_reminder()

        self._save_task(task)

        return task

    def mark_reminder_sent(
        self,
        *,
        user_id: int,
        task_id: int,
    ) -> Task:

        task = self.get_task(
            user_id=user_id,
            task_id=task_id,
        )

        task.mark_reminder_sent()

        self._save_task(task)

        return task

    # ------------------------------------------------------------------
    # DATES
    # ------------------------------------------------------------------

    def set_due_date(
        self,
        *,
        user_id: int,
        task_id: int,
        due_at: datetime | None,
    ) -> Task:

        task = self.get_task(
            user_id=user_id,
            task_id=task_id,
        )

        task.set_due_at(due_at)

        self._save_task(task)

        return task

    def clear_due_date(
        self,
        *,
        user_id: int,
        task_id: int,
    ) -> Task:

        task = self.get_task(
            user_id=user_id,
            task_id=task_id,
        )

        task.clear_due_date()

        self._save_task(task)

        return task

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete_task(
        self,
        *,
        user_id: int,
        task_id: int,
    ) -> None:

        self.get_task(
            user_id=user_id,
            task_id=task_id,
        )

        query = """
            DELETE FROM tasks
            WHERE id = %s
              AND user_id = %s
        """

        try:
            cursor = self.connection.execute(
                query,
                (
                    task_id,
                    user_id,
                ),
            )

            self.connection.commit()

        except psycopg.Error as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Impossible de supprimer la tâche."
            ) from exc

        if cursor.rowcount == 0:
            raise TaskNotFoundError(
                f"La tâche {task_id} est introuvable."
            )

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

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
                WHERE id = %s
                  AND user_id = %s
                LIMIT 1
            """

            try:
                contact = self.connection.execute(
                    query,
                    (
                        contact_id,
                        user_id,
                    ),
                ).fetchone()

            except psycopg.Error as exc:
                raise DatabaseError(
                    "Impossible de vérifier le contact."
                ) from exc

            if contact is None:
                raise TaskNotFoundError(
                    "Le contact associé à la tâche "
                    "n'existe pas."
                )

        if conversation_id is not None:
            query = """
                SELECT id
                FROM conversations
                WHERE id = %s
                  AND user_id = %s
                LIMIT 1
            """

            try:
                conversation = self.connection.execute(
                    query,
                    (
                        conversation_id,
                        user_id,
                    ),
                ).fetchone()

            except psycopg.Error as exc:
                raise DatabaseError(
                    "Impossible de vérifier la conversation."
                ) from exc

            if conversation is None:
                raise TaskNotFoundError(
                    "La conversation associée à la tâche "
                    "n'existe pas."
                )

    def _save_task(
        self,
        task: Task,
    ) -> None:

        query = """
            UPDATE tasks
            SET
                title = %s,
                description = %s,
                status = %s,
                priority = %s,
                contact_id = %s,
                conversation_id = %s,
                due_at = %s,
                completed_at = %s,
                reminder_enabled = %s,
                reminder_sent = %s,
                updated_at = %s
            WHERE id = %s
              AND user_id = %s
        """

        try:
            self.connection.execute(
                query,
                (
                    task.title,
                    task.description,
                    task.status.value,
                    task.priority.value,
                    task.contact_id,
                    task.conversation_id,
                    task.due_at.isoformat()
                    if task.due_at
                    else None,
                    task.completed_at.isoformat()
                    if task.completed_at
                    else None,
                    task.reminder_enabled,
                    task.reminder_sent,
                    task.updated_at.isoformat(),
                    task.id,
                    task.user_id,
                ),
            )

            self.connection.commit()

        except psycopg.Error as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Impossible de sauvegarder la tâche."
            ) from exc
