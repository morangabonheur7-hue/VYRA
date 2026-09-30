from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> datetime:
    """
    Retourne la date et l'heure actuelles en UTC.
    """

    return datetime.now(timezone.utc)


class ContactStatus(str, Enum):
    """
    Statut commercial d'un contact.
    """

    NEW = "new"
    PROSPECT = "prospect"
    CLIENT = "client"
    PARTNER = "partner"
    SUPPLIER = "supplier"
    INACTIVE = "inactive"


class ContactSource(str, Enum):
    """
    Origine du contact.
    """

    MANUAL = "manual"
    REFERRAL = "referral"
    WEBSITE = "website"
    SOCIAL_MEDIA = "social_media"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    PHONE = "phone"
    OTHER = "other"


class Contact:
    """
    Modèle représentant un contact dans VYRA.

    Un contact appartient à un utilisateur VYRA.
    Il peut représenter une personne ou une entreprise.

    Cette classe ne gère pas directement la base de données.
    Elle représente les données et les règles métier du contact.
    """

    TABLE_NAME = "contacts"

    def __init__(
        self,
        *,
        contact_id: int | None = None,
        user_id: int,
        first_name: str,
        last_name: str = "",
        company_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        position: str | None = None,
        status: ContactStatus | str = ContactStatus.NEW,
        source: ContactSource | str = ContactSource.MANUAL,
        notes: str | None = None,
        is_archived: bool = False,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        last_contacted_at: datetime | None = None,
    ) -> None:
        self.id = contact_id
        self.user_id = user_id

        self.first_name = first_name.strip()
        self.last_name = last_name.strip()

        self.company_name = (
            company_name.strip()
            if company_name
            else None
        )

        self.email = (
            email.strip().lower()
            if email
            else None
        )

        self.phone = (
            phone.strip()
            if phone
            else None
        )

        self.position = (
            position.strip()
            if position
            else None
        )

        self.status = self._normalize_status(status)
        self.source = self._normalize_source(source)

        self.notes = (
            notes.strip()
            if notes
            else None
        )

        self.is_archived = bool(is_archived)

        self.created_at = created_at or utc_now()
        self.updated_at = updated_at or self.created_at
        self.last_contacted_at = last_contacted_at

    # ==========================================================
    # NORMALISATION
    # ==========================================================

    @staticmethod
    def _normalize_status(
        status: ContactStatus | str,
    ) -> ContactStatus:
        """
        Convertit une valeur en ContactStatus.
        """

        if isinstance(status, ContactStatus):
            return status

        try:
            return ContactStatus(status.strip().lower())
        except ValueError as exc:
            raise ValueError(
                f"Statut de contact invalide : {status!r}"
            ) from exc

    @staticmethod
    def _normalize_source(
        source: ContactSource | str,
    ) -> ContactSource:
        """
        Convertit une valeur en ContactSource.
        """

        if isinstance(source, ContactSource):
            return source

        try:
            return ContactSource(source.strip().lower())
        except ValueError as exc:
            raise ValueError(
                f"Source de contact invalide : {source!r}"
            ) from exc

    # ==========================================================
    # PROPRIÉTÉS
    # ==========================================================

    @property
    def full_name(self) -> str:
        """
        Retourne le nom complet du contact.
        """

        return " ".join(
            part
            for part in (
                self.first_name,
                self.last_name,
            )
            if part
        )

    @property
    def display_name(self) -> str:
        """
        Retourne le nom à afficher dans l'interface.

        Si une entreprise existe, elle est ajoutée au nom.
        """

        if self.company_name:
            return f"{self.full_name} — {self.company_name}"

        return self.full_name

    @property
    def has_email(self) -> bool:
        """
        Indique si le contact possède une adresse email.
        """

        return bool(self.email)

    @property
    def has_phone(self) -> bool:
        """
        Indique si le contact possède un numéro de téléphone.
        """

        return bool(self.phone)

    @property
    def is_business_contact(self) -> bool:
        """
        Indique si le contact possède des informations
        professionnelles.
        """

        return bool(
            self.company_name
            or self.position
        )

    # ==========================================================
    # STATUT
    # ==========================================================

    def set_status(
        self,
        status: ContactStatus | str,
    ) -> None:
        """
        Modifie le statut du contact.
        """

        self.status = self._normalize_status(status)
        self.touch()

    def mark_as_client(self) -> None:
        """
        Transforme le contact en client.
        """

        self.status = ContactStatus.CLIENT
        self.touch()

    def mark_as_prospect(self) -> None:
        """
        Transforme le contact en prospect.
        """

        self.status = ContactStatus.PROSPECT
        self.touch()

    def mark_as_partner(self) -> None:
        """
        Transforme le contact en partenaire.
        """

        self.status = ContactStatus.PARTNER
        self.touch()

    def mark_as_inactive(self) -> None:
        """
        Marque le contact comme inactif.
        """

        self.status = ContactStatus.INACTIVE
        self.touch()

    # ==========================================================
    # ARCHIVAGE
    # ==========================================================

    def archive(self) -> None:
        """
        Archive le contact sans le supprimer.
        """

        self.is_archived = True
        self.touch()

    def unarchive(self) -> None:
        """
        Désarchive le contact.
        """

        self.is_archived = False
        self.touch()

    # ==========================================================
    # CONTACT
    # ==========================================================

    def register_contact(self) -> None:
        """
        Enregistre la date du dernier contact avec cette personne.
        """

        self.last_contacted_at = utc_now()
        self.touch()

    # ==========================================================
    # MISE À JOUR
    # ==========================================================

    def update(
        self,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        company_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        position: str | None = None,
        status: ContactStatus | str | None = None,
        source: ContactSource | str | None = None,
        notes: str | None = None,
    ) -> None:
        """
        Met à jour les informations du contact.

        Seuls les champs fournis sont modifiés.
        """

        if first_name is not None:
            self.first_name = first_name.strip()

        if last_name is not None:
            self.last_name = last_name.strip()

        if company_name is not None:
            self.company_name = (
                company_name.strip()
                or None
            )

        if email is not None:
            self.email = (
                email.strip().lower()
                or None
            )

        if phone is not None:
            self.phone = (
                phone.strip()
                or None
            )

        if position is not None:
            self.position = (
                position.strip()
                or None
            )

        if status is not None:
            self.status = self._normalize_status(status)

        if source is not None:
            self.source = self._normalize_source(source)

        if notes is not None:
            self.notes = notes.strip() or None

        self.touch()

    def touch(self) -> None:
        """
        Met à jour la date de modification.
        """

        self.updated_at = utc_now()

    # ==========================================================
    # VALIDATION MÉTIER
    # ==========================================================

    def can_be_contacted(self) -> bool:
        """
        Indique si le contact peut actuellement être utilisé
        pour une communication.

        Un contact archivé ou inactif n'est pas considéré
        comme actif.
        """

        return (
            not self.is_archived
            and self.status != ContactStatus.INACTIVE
        )

    def has_contact_information(self) -> bool:
        """
        Indique si VYRA dispose d'au moins un moyen
        de contact direct.
        """

        return bool(
            self.email
            or self.phone
        )

    # ==========================================================
    # CONVERSION
    # ==========================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convertit le contact en dictionnaire destiné
        notamment aux réponses API.
        """

        return {
            "id": self.id,
            "user_id": self.user_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "display_name": self.display_name,
            "company_name": self.company_name,
            "email": self.email,
            "phone": self.phone,
            "position": self.position,
            "status": self.status.value,
            "source": self.source.value,
            "notes": self.notes,
            "is_archived": self.is_archived,
            "has_email": self.has_email,
            "has_phone": self.has_phone,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_contacted_at": (
                self.last_contacted_at.isoformat()
                if self.last_contacted_at
                else None
            ),
        }

    def to_database_dict(self) -> dict[str, Any]:
        """
        Prépare les données pour un enregistrement SQLite.
        """

        return {
            "id": self.id,
            "user_id": self.user_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "company_name": self.company_name,
            "email": self.email,
            "phone": self.phone,
            "position": self.position,
            "status": self.status.value,
            "source": self.source.value,
            "notes": self.notes,
            "is_archived": int(self.is_archived),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_contacted_at": (
                self.last_contacted_at.isoformat()
                if self.last_contacted_at
                else None
            ),
        }

    # ==========================================================
    # DATABASE
    # ==========================================================

    @classmethod
    def from_row(cls, row: Any) -> "Contact":
        """
        Construit un Contact à partir d'une ligne SQLite.
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
            contact_id=row["id"],
            user_id=row["user_id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            company_name=row["company_name"],
            email=row["email"],
            phone=row["phone"],
            position=row["position"],
            status=row["status"],
            source=row["source"],
            notes=row["notes"],
            is_archived=bool(row["is_archived"]),
            created_at=parse_datetime(row["created_at"]),
            updated_at=parse_datetime(row["updated_at"]),
            last_contacted_at=parse_datetime(
                row["last_contacted_at"]
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
            f"Contact("
            f"id={self.id!r}, "
            f"user_id={self.user_id!r}, "
            f"name={self.full_name!r}, "
            f"company={self.company_name!r}, "
            f"status={self.status.value!r}, "
            f"is_archived={self.is_archived!r}"
            f")"
        )