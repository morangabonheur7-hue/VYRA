from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    """
    Retourne la date et l'heure actuelles en UTC.

    Utiliser UTC permet d'avoir une référence temporelle
    cohérente même si les utilisateurs de VYRA sont dans
    plusieurs pays.
    """

    return datetime.now(timezone.utc)


class User:
    """
    Modèle représentant un utilisateur de VYRA.

    Cette classe représente les informations principales
    d'un compte utilisateur.

    Le mot de passe n'est jamais stocké en clair.
    Seul son hash doit être placé dans password_hash.
    """

    TABLE_NAME = "users"

    def __init__(
        self,
        *,
        user_id: int | None = None,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str = "",
        phone: str | None = None,
        business_name: str | None = None,
        business_description: str | None = None,
        is_active: bool = True,
        is_verified: bool = False,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        last_login_at: datetime | None = None,
    ) -> None:
        self.id = user_id
        self.email = email.strip().lower()
        self.password_hash = password_hash

        self.first_name = first_name.strip()
        self.last_name = last_name.strip()

        self.phone = phone.strip() if phone else None

        self.business_name = (
            business_name.strip()
            if business_name
            else None
        )

        self.business_description = (
            business_description.strip()
            if business_description
            else None
        )

        self.is_active = bool(is_active)
        self.is_verified = bool(is_verified)

        self.created_at = created_at or utc_now()
        self.updated_at = updated_at or self.created_at
        self.last_login_at = last_login_at

    # ==========================================================
    # PROPRIÉTÉS
    # ==========================================================

    @property
    def full_name(self) -> str:
        """
        Retourne le nom complet de l'utilisateur.
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
    def has_business_profile(self) -> bool:
        """
        Indique si l'utilisateur possède des informations
        professionnelles.
        """

        return bool(
            self.business_name
            or self.business_description
        )

    # ==========================================================
    # COMPTE
    # ==========================================================

    def activate(self) -> None:
        """
        Active le compte utilisateur.
        """

        self.is_active = True
        self.touch()

    def deactivate(self) -> None:
        """
        Désactive le compte utilisateur.
        """

        self.is_active = False
        self.touch()

    def verify(self) -> None:
        """
        Marque le compte comme vérifié.
        """

        self.is_verified = True
        self.touch()

    # ==========================================================
    # CONNEXION
    # ==========================================================

    def register_login(self) -> None:
        """
        Enregistre la dernière connexion de l'utilisateur.
        """

        self.last_login_at = utc_now()
        self.touch()

    # ==========================================================
    # MISE À JOUR
    # ==========================================================

    def touch(self) -> None:
        """
        Met à jour la date de modification du compte.
        """

        self.updated_at = utc_now()

    def update_profile(
        self,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        phone: str | None = None,
        business_name: str | None = None,
        business_description: str | None = None,
    ) -> None:
        """
        Met à jour les informations modifiables du profil.

        Seuls les champs fournis sont modifiés.
        """

        if first_name is not None:
            self.first_name = first_name.strip()

        if last_name is not None:
            self.last_name = last_name.strip()

        if phone is not None:
            self.phone = phone.strip() or None

        if business_name is not None:
            self.business_name = (
                business_name.strip() or None
            )

        if business_description is not None:
            self.business_description = (
                business_description.strip() or None
            )

        self.touch()

    # ==========================================================
    # VALIDATION MÉTIER
    # ==========================================================

    def can_login(self) -> bool:
        """
        Indique si l'utilisateur peut actuellement
        se connecter à VYRA.
        """

        return self.is_active

    # ==========================================================
    # CONVERSION
    # ==========================================================

    def to_dict(
        self,
        *,
        include_sensitive: bool = False,
    ) -> dict[str, Any]:
        """
        Convertit l'utilisateur en dictionnaire.

        Par défaut, password_hash n'est PAS exposé.

        include_sensitive=True est réservé aux opérations
        internes qui ont réellement besoin des données sensibles.
        """

        data: dict[str, Any] = {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "phone": self.phone,
            "business_name": self.business_name,
            "business_description": self.business_description,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login_at": (
                self.last_login_at.isoformat()
                if self.last_login_at
                else None
            ),
        }

        if include_sensitive:
            data["password_hash"] = self.password_hash

        return data

    # ==========================================================
    # DATABASE
    # ==========================================================

    @classmethod
    def from_row(cls, row: Any) -> "User":
        """
        Construit un User à partir d'une ligne provenant
        de SQLite.

        Cette méthode sera utilisée lorsque la couche database
        récupérera un utilisateur.
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
            user_id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            phone=row["phone"],
            business_name=row["business_name"],
            business_description=row["business_description"],
            is_active=bool(row["is_active"]),
            is_verified=bool(row["is_verified"]),
            created_at=parse_datetime(row["created_at"]),
            updated_at=parse_datetime(row["updated_at"]),
            last_login_at=parse_datetime(row["last_login_at"]),
        )

    def to_database_dict(self) -> dict[str, Any]:
        """
        Retourne uniquement les données nécessaires
        à l'enregistrement en base de données.

        Les dates sont converties en ISO 8601 afin d'être
        facilement stockées dans SQLite.
        """

        return {
            "id": self.id,
            "email": self.email,
            "password_hash": self.password_hash,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "business_name": self.business_name,
            "business_description": self.business_description,
            "is_active": int(self.is_active),
            "is_verified": int(self.is_verified),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login_at": (
                self.last_login_at.isoformat()
                if self.last_login_at
                else None
            ),
        }

    # ==========================================================
    # REPRÉSENTATION
    # ==========================================================

    def __repr__(self) -> str:
        """
        Représentation utile pour le développement.

        Le password_hash n'est volontairement jamais affiché.
        """

        return (
            f"User("
            f"id={self.id!r}, "
            f"email={self.email!r}, "
            f"full_name={self.full_name!r}, "
            f"is_active={self.is_active!r}, "
            f"is_verified={self.is_verified!r}"
            f")"
        )