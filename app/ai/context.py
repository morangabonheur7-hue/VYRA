from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContactContext:
    """
    Informations utiles concernant le contact.
    """

    contact_id: int
    full_name: str
    company_name: str | None = None
    position: str | None = None
    email: str | None = None
    phone: str | None = None
    status: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "contact_id": self.contact_id,
            "full_name": self.full_name,
            "company_name": self.company_name,
            "position": self.position,
            "email": self.email,
            "phone": self.phone,
            "status": self.status,
            "notes": self.notes,
        }


@dataclass
class ConversationContext:
    """
    Informations principales d'une conversation.
    """

    conversation_id: int
    channel: str
    status: str
    subject: str | None = None
    summary: str | None = None
    ai_enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "channel": self.channel,
            "status": self.status,
            "subject": self.subject,
            "summary": self.summary,
            "ai_enabled": self.ai_enabled,
        }


@dataclass
class MessageContext:
    """
    Représentation simplifiée d'un message pour l'IA.
    """

    sender: str
    content: str
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sender": self.sender,
            "content": self.content,
            "created_at": self.created_at,
        }


@dataclass
class MemoryContext:
    """
    Une information mémorisée par VYRA.
    """

    key: str
    value: Any
    memory_type: str
    importance: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "memory_type": self.memory_type,
            "importance": self.importance,
        }


@dataclass
class AIContext:
    """
    Contexte complet destiné au système IA.

    Cette classe constitue une représentation indépendante
    de la base de données.
    """

    contact: ContactContext | None = None
    conversation: ConversationContext | None = None
    messages: list[MessageContext] = field(
        default_factory=list
    )
    memories: list[MemoryContext] = field(
        default_factory=list
    )
    user_profile: dict[str, Any] = field(
        default_factory=dict
    )
    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contact": (
                self.contact.to_dict()
                if self.contact
                else None
            ),
            "conversation": (
                self.conversation.to_dict()
                if self.conversation
                else None
            ),
            "messages": [
                message.to_dict()
                for message in self.messages
            ],
            "memories": [
                memory.to_dict()
                for memory in self.memories
            ],
            "user_profile": self.user_profile,
            "extra": self.extra,
        }


class ContextBuilder:
    """
    Construit un AIContext de manière contrôlée.

    L'objectif est d'éviter d'envoyer aveuglément toute
    la base de données au modèle IA.

    Seules les informations nécessaires sont conservées.
    """

    def __init__(
        self,
        *,
        max_messages: int = 20,
        max_memories: int = 20,
    ) -> None:
        self.max_messages = min(
            max(max_messages, 1),
            100,
        )

        self.max_memories = min(
            max(max_memories, 1),
            100,
        )

    # ------------------------------------------------------------------
    # BUILD
    # ------------------------------------------------------------------

    def build(
        self,
        *,
        contact: dict[str, Any] | None = None,
        conversation: dict[str, Any] | None = None,
        messages: list[dict[str, Any]] | None = None,
        memories: list[dict[str, Any]] | None = None,
        user_profile: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> AIContext:
        """
        Construit un contexte IA à partir des données
        disponibles.
        """

        context = AIContext()

        if contact:
            context.contact = self._build_contact(
                contact
            )

        if conversation:
            context.conversation = self._build_conversation(
                conversation
            )

        if messages:
            context.messages = self._build_messages(
                messages
            )

        if memories:
            context.memories = self._build_memories(
                memories
            )

        if user_profile:
            context.user_profile = self._clean_dictionary(
                user_profile
            )

        if extra:
            context.extra = self._clean_dictionary(
                extra
            )

        return context

    # ------------------------------------------------------------------
    # CONTACT
    # ------------------------------------------------------------------

    @staticmethod
    def _build_contact(
        contact: dict[str, Any],
    ) -> ContactContext:
        return ContactContext(
            contact_id=int(
                contact.get("id")
                or contact.get("contact_id")
                or 0
            ),
            full_name=str(
                contact.get("full_name")
                or ""
            ),
            company_name=contact.get(
                "company_name"
            ),
            position=contact.get(
                "position"
            ),
            email=contact.get(
                "email"
            ),
            phone=contact.get(
                "phone"
            ),
            status=(
                contact.get("status")
                or (
                    contact.get("status", {}).get("value")
                    if isinstance(
                        contact.get("status"),
                        dict,
                    )
                    else None
                )
            ),
            notes=contact.get(
                "notes"
            ),
        )

    # ------------------------------------------------------------------
    # CONVERSATION
    # ------------------------------------------------------------------

    @staticmethod
    def _build_conversation(
        conversation: dict[str, Any],
    ) -> ConversationContext:
        return ConversationContext(
            conversation_id=int(
                conversation.get("id")
                or conversation.get(
                    "conversation_id"
                )
                or 0
            ),
            channel=str(
                conversation.get("channel")
                or ""
            ),
            status=str(
                conversation.get("status")
                or ""
            ),
            subject=conversation.get(
                "subject"
            ),
            summary=conversation.get(
                "summary"
            ),
            ai_enabled=bool(
                conversation.get(
                    "ai_enabled",
                    True,
                )
            ),
        )

    # ------------------------------------------------------------------
    # MESSAGES
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        messages: list[dict[str, Any]],
    ) -> list[MessageContext]:
        """
        Conserve uniquement les messages les plus récents.

        L'ordre final reste chronologique.
        """

        selected = messages[-self.max_messages:]

        result: list[MessageContext] = []

        for message in selected:
            sender = (
                message.get("sender")
                or message.get("role")
                or "user"
            )

            content = message.get(
                "content",
                "",
            )

            if not isinstance(content, str):
                continue

            content = content.strip()

            if not content:
                continue

            result.append(
                MessageContext(
                    sender=str(sender),
                    content=content,
                    created_at=message.get(
                        "created_at"
                    ),
                )
            )

        return result

    # ------------------------------------------------------------------
    # MEMORIES
    # ------------------------------------------------------------------

    def _build_memories(
        self,
        memories: list[dict[str, Any]],
    ) -> list[MemoryContext]:
        """
        Sélectionne les mémoires les plus pertinentes.

        Les mémoires sont triées par importance décroissante.
        """

        sorted_memories = sorted(
            memories,
            key=lambda memory: int(
                memory.get(
                    "importance",
                    1,
                )
            ),
            reverse=True,
        )

        selected = sorted_memories[
            :self.max_memories
        ]

        result: list[MemoryContext] = []

        for memory in selected:
            key = memory.get(
                "key",
                "",
            )

            if not key:
                continue

            result.append(
                MemoryContext(
                    key=str(key),
                    value=memory.get(
                        "value"
                    ),
                    memory_type=str(
                        memory.get(
                            "memory_type",
                            "other",
                        )
                    ),
                    importance=int(
                        memory.get(
                            "importance",
                            1,
                        )
                    ),
                )
            )

        return result

    # ------------------------------------------------------------------
    # TEXT REPRESENTATION
    # ------------------------------------------------------------------

    def to_prompt_text(
        self,
        context: AIContext,
    ) -> str:
        """
        Transforme le contexte structuré en texte lisible
        par un modèle IA.
        """

        sections: list[str] = []

        if context.contact:
            sections.append(
                self._format_contact(
                    context.contact
                )
            )

        if context.conversation:
            sections.append(
                self._format_conversation(
                    context.conversation
                )
            )

        if context.memories:
            sections.append(
                self._format_memories(
                    context.memories
                )
            )

        if context.messages:
            sections.append(
                self._format_messages(
                    context.messages
                )
            )

        if context.user_profile:
            sections.append(
                self._format_dictionary(
                    "PROFIL UTILISATEUR",
                    context.user_profile,
                )
            )

        if context.extra:
            sections.append(
                self._format_dictionary(
                    "INFORMATIONS SUPPLÉMENTAIRES",
                    context.extra,
                )
            )

        return "\n\n".join(
            section
            for section in sections
            if section
        )

    # ------------------------------------------------------------------
    # FORMATTERS
    # ------------------------------------------------------------------

    @staticmethod
    def _format_contact(
        contact: ContactContext,
    ) -> str:
        lines = [
            "CONTACT",
            f"Nom : {contact.full_name}",
        ]

        if contact.company_name:
            lines.append(
                f"Entreprise : {contact.company_name}"
            )

        if contact.position:
            lines.append(
                f"Poste : {contact.position}"
            )

        if contact.email:
            lines.append(
                f"Email : {contact.email}"
            )

        if contact.phone:
            lines.append(
                f"Téléphone : {contact.phone}"
            )

        if contact.status:
            lines.append(
                f"Statut : {contact.status}"
            )

        if contact.notes:
            lines.append(
                f"Notes : {contact.notes}"
            )

        return "\n".join(lines)

    @staticmethod
    def _format_conversation(
        conversation: ConversationContext,
    ) -> str:
        lines = [
            "CONVERSATION",
            f"Canal : {conversation.channel}",
            f"Statut : {conversation.status}",
            f"IA activée : {conversation.ai_enabled}",
        ]

        if conversation.subject:
            lines.append(
                f"Sujet : {conversation.subject}"
            )

        if conversation.summary:
            lines.append(
                f"Résumé : {conversation.summary}"
            )

        return "\n".join(lines)

    @staticmethod
    def _format_memories(
        memories: list[MemoryContext],
    ) -> str:
        lines = ["MÉMOIRE"]

        for memory in memories:
            lines.append(
                "- "
                f"{memory.key} : "
                f"{memory.value} "
                f"(importance {memory.importance}/5)"
            )

        return "\n".join(lines)

    @staticmethod
    def _format_messages(
        messages: list[MessageContext],
    ) -> str:
        lines = [
            "HISTORIQUE DE CONVERSATION"
        ]

        for message in messages:
            lines.append(
                f"{message.sender.upper()} : "
                f"{message.content}"
            )

        return "\n".join(lines)

    @staticmethod
    def _format_dictionary(
        title: str,
        data: dict[str, Any],
    ) -> str:
        lines = [title]

        for key, value in data.items():
            lines.append(
                f"{key} : {value}"
            )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # CLEANING
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_dictionary(
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Nettoie légèrement un dictionnaire avant son utilisation
        dans le contexte IA.
        """

        cleaned: dict[str, Any] = {}

        for key, value in data.items():
            if not isinstance(key, str):
                continue

            normalized_key = key.strip()

            if not normalized_key:
                continue

            cleaned[normalized_key] = value

        return cleaned