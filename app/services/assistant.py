import sqlite3
from typing import Any, Protocol

from app.core.errors import (
    AIProviderError,
    ConversationNotFoundError,
    DatabaseError,
)
from app.models.message import Message
from app.services.memory import MemoryService


class AIGatewayProtocol(Protocol):
    """
    Contrat minimal attendu par AssistantService.

    Le véritable AI Gateway sera construit plus tard
    dans app/ai/gateway.py.

    Grâce à ce contrat, AssistantService n'a pas besoin
    de connaître Gemini, OpenAI, OpenRouter, etc.
    """

    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        ...


class AssistantService:
    """
    Orchestre le fonctionnement intelligent de VYRA.

    Responsabilités principales :

    1. récupérer le contexte d'une conversation ;
    2. récupérer les mémoires pertinentes ;
    3. préparer les informations pour l'IA ;
    4. appeler l'AI Gateway ;
    5. transformer la réponse IA en proposition ;
    6. conserver le contrôle humain.

    VYRA V1 ne permet PAS à ce service d'envoyer
    automatiquement une réponse au contact.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
        ai_gateway: AIGatewayProtocol,
    ) -> None:
        self.connection = connection
        self.ai_gateway = ai_gateway
        self.memory_service = MemoryService(connection)

    # ------------------------------------------------------------------
    # SUGGESTION DE RÉPONSE
    # ------------------------------------------------------------------

    def suggest_reply(
        self,
        *,
        user_id: int,
        conversation_id: int,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Message:
        """
        Génère une proposition de réponse IA.

        La réponse est enregistrée comme brouillon nécessitant
        une validation humaine.

        IMPORTANT :
        cette méthode ne contacte jamais directement WhatsApp
        ou un autre canal externe.
        """

        conversation = self._get_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if not conversation.can_use_ai:
            raise AIProviderError(
                "L'assistant IA est désactivé "
                "pour cette conversation."
            )

        context = self.build_conversation_context(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        ai_messages = self._build_ai_messages(
            context=context,
        )

        try:
            result = self.ai_gateway.generate(
                messages=ai_messages,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            raise AIProviderError(
                "Impossible de générer une réponse avec "
                "le fournisseur IA."
            ) from exc

        generated_text = self._extract_generated_text(result)

        if not generated_text:
            raise AIProviderError(
                "Le fournisseur IA a retourné une réponse vide."
            )

        message = Message.ai_draft(
            conversation_id=conversation_id,
            content=generated_text,
            metadata={
                "assistant_action": "suggest_reply",
                "requires_human_validation": True,
            },
        )

        return self._save_message(
            message=message,
        )

    # ------------------------------------------------------------------
    # ANALYSE D'UNE CONVERSATION
    # ------------------------------------------------------------------

    def analyze_conversation(
        self,
        *,
        user_id: int,
        conversation_id: int,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        """
        Demande à l'IA d'analyser une conversation.

        Cette fonction ne crée pas de message à envoyer.

        Elle pourra servir notamment à identifier :

        - intention du contact ;
        - besoin ;
        - niveau d'intérêt ;
        - objections ;
        - informations manquantes ;
        - prochaine action recommandée.
        """

        conversation = self._get_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        context = self.build_conversation_context(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        ai_messages = self._build_ai_messages(
            context=context,
            analysis_mode=True,
        )

        try:
            return self.ai_gateway.generate(
                messages=ai_messages,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            raise AIProviderError(
                "Impossible d'analyser la conversation."
            ) from exc

    # ------------------------------------------------------------------
    # CONTEXTE
    # ------------------------------------------------------------------

    def build_conversation_context(
        self,
        *,
        user_id: int,
        conversation_id: int,
        max_messages: int = 20,
        max_memories: int = 20,
    ) -> dict[str, Any]:
        """
        Construit le contexte complet nécessaire à l'IA.

        Le contexte contient :

        - informations de conversation ;
        - contact ;
        - messages récents ;
        - mémoires pertinentes.
        """

        conversation = self._get_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        contact = self._get_contact(
            user_id=user_id,
            contact_id=conversation.contact_id,
        )

        messages = self._get_recent_messages(
            conversation_id=conversation_id,
            limit=max_messages,
        )

        memories = self.memory_service.build_context(
            user_id=user_id,
            contact_id=conversation.contact_id,
            conversation_id=conversation_id,
            limit=max_memories,
        )

        return {
            "conversation": conversation.to_dict(),
            "contact": self._row_to_dict(contact),
            "messages": [
                message.to_dict()
                for message in messages
            ],
            "memories": memories,
        }

    # ------------------------------------------------------------------
    # PRÉPARATION DU CONTEXTE POUR L'IA
    # ------------------------------------------------------------------

    def _build_ai_messages(
        self,
        *,
        context: dict[str, Any],
        analysis_mode: bool = False,
    ) -> list[dict[str, str]]:
        """
        Transforme le contexte interne de VYRA en messages
        compréhensibles par l'AI Gateway.
        """

        messages: list[dict[str, str]] = []

        if analysis_mode:
            instruction = (
                "Analyse cette conversation commerciale. "
                "Identifie l'intention du contact, son besoin, "
                "les informations importantes, les objections "
                "éventuelles, les informations manquantes et "
                "la prochaine action recommandée. "
                "Ne prétends pas avoir effectué une action "
                "qui n'a pas été réalisée."
            )
        else:
            instruction = (
                "Génère une réponse commerciale naturelle, "
                "claire et utile à partir du contexte fourni. "
                "Ne prétends pas avoir effectué une action "
                "qui n'a pas été réalisée. "
                "La réponse doit rester une proposition "
                "soumise à validation humaine."
            )

        messages.append(
            {
                "role": "system",
                "content": instruction,
            }
        )

        contact = context.get("contact", {})

        contact_information = (
            f"Nom : {contact.get('full_name', '')}\n"
            f"Entreprise : {contact.get('company_name', '')}\n"
            f"Poste : {contact.get('position', '')}"
        )

        messages.append(
            {
                "role": "system",
                "content": (
                    "Informations sur le contact :\n"
                    f"{contact_information}"
                ),
            }
        )

        memories = context.get("memories", [])

        if memories:
            memory_lines = []

            for memory in memories:
                memory_lines.append(
                    "- "
                    f"{memory.get('key')}: "
                    f"{memory.get('value')}"
                )

            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Mémoire pertinente :\n"
                        + "\n".join(memory_lines)
                    ),
                }
            )

        conversation_messages = context.get(
            "messages",
            [],
        )

        for message in conversation_messages:
            role = self._map_message_role(
                message.get("sender"),
            )

            messages.append(
                {
                    "role": role,
                    "content": message.get(
                        "content",
                        "",
                    ),
                }
            )

        return messages

    # ------------------------------------------------------------------
    # DATABASE : CONVERSATION
    # ------------------------------------------------------------------

    def _get_conversation(
        self,
        *,
        user_id: int,
        conversation_id: int,
    ):
        query = """
            SELECT *
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
                "Impossible de récupérer la conversation."
            ) from exc

        if row is None:
            raise ConversationNotFoundError(
                f"La conversation {conversation_id} "
                "est introuvable."
            )

        from app.models.conversation import Conversation

        return Conversation.from_row(row)

    # ------------------------------------------------------------------
    # DATABASE : CONTACT
    # ------------------------------------------------------------------

    def _get_contact(
        self,
        *,
        user_id: int,
        contact_id: int,
    ) -> sqlite3.Row:
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
                (
                    contact_id,
                    user_id,
                ),
            ).fetchone()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de récupérer le contact."
            ) from exc

        if row is None:
            raise DatabaseError(
                "Le contact associé à la conversation "
                "est introuvable."
            )

        return row

    # ------------------------------------------------------------------
    # DATABASE : MESSAGES
    # ------------------------------------------------------------------

    def _get_recent_messages(
        self,
        *,
        conversation_id: int,
        limit: int,
    ) -> list[Message]:
        limit = min(max(limit, 1), 100)

        query = """
            SELECT *
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """

        try:
            rows = self.connection.execute(
                query,
                (
                    conversation_id,
                    limit,
                ),
            ).fetchall()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de récupérer les messages."
            ) from exc

        messages = [
            Message.from_row(row)
            for row in rows
        ]

        # La requête récupère les plus récents en premier.
        # Pour l'IA, nous voulons conserver l'ordre chronologique.
        messages.reverse()

        return messages

    # ------------------------------------------------------------------
    # DATABASE : SAVE MESSAGE
    # ------------------------------------------------------------------

    def _save_message(
        self,
        *,
        message: Message,
    ) -> Message:
        """
        Enregistre une proposition IA.

        La metadata est convertie en JSON car SQLite
        ne sait pas stocker directement un dictionnaire Python.
        """

        query = """
            INSERT INTO messages (
                conversation_id,
                sender,
                role,
                content,
                status,
                is_ai_generated,
                requires_approval,
                approved_by_user,
                external_message_id,
                metadata,
                created_at,
                updated_at,
                sent_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        import json

        values = (
            message.conversation_id,
            message.sender.value,
            message.role.value,
            message.content,
            message.status.value,
            int(message.is_ai_generated),
            int(message.requires_approval),
            int(message.approved_by_user),
            message.external_message_id,
            json.dumps(
                message.metadata,
                ensure_ascii=False,
            ),
            message.created_at.isoformat(),
            message.updated_at.isoformat(),
            message.sent_at.isoformat()
            if message.sent_at
            else None,
        )

        try:
            cursor = self.connection.execute(
                query,
                values,
            )

            self.connection.commit()

            message.id = cursor.lastrowid

            return message

        except sqlite3.IntegrityError as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Impossible d'enregistrer la proposition IA.",
                details={"database_error": str(exc)},
            ) from exc

        except sqlite3.Error as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Une erreur est survenue lors de "
                "l'enregistrement de la proposition IA."
            ) from exc

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_generated_text(
        result: Any,
    ) -> str:
        """
        Extrait le texte produit par différents formats
        possibles de l'AI Gateway.

        Le Gateway définitra ensuite un format standard,
        mais cette méthode garde le service robuste.
        """

        if isinstance(result, str):
            return result.strip()

        if isinstance(result, dict):
            for key in (
                "text",
                "content",
                "response",
                "output",
            ):
                value = result.get(key)

                if isinstance(value, str):
                    return value.strip()

        text_attribute = getattr(
            result,
            "text",
            None,
        )

        if isinstance(text_attribute, str):
            return text_attribute.strip()

        return ""

    @staticmethod
    def _map_message_role(
        sender: str | None,
    ) -> str:
        """
        Convertit les rôles internes de VYRA vers les rôles
        standards utilisés par les fournisseurs IA.
        """

        if sender == "contact":
            return "user"

        if sender in {
            "assistant",
            "user",
        }:
            return sender

        return "user"

    @staticmethod
    def _row_to_dict(
        row: sqlite3.Row,
    ) -> dict[str, Any]:
        return {
            key: row[key]
            for key in row.keys()
        }