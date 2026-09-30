import hashlib
import hmac
import os
import sqlite3
from typing import Any

from app.core.errors import (
    ConflictError,
    DatabaseError,
    UserNotFoundError,
)
from app.models.user import User
from app.schemas.user import (
    PasswordChange,
    UserCreate,
    UserUpdate,
)


class UserService:
    """
    Service de gestion des utilisateurs VYRA.

    Responsabilités :

    - créer un utilisateur ;
    - rechercher un utilisateur ;
    - modifier son profil ;
    - gérer son statut ;
    - vérifier un mot de passe ;
    - modifier un mot de passe.

    Le service ne gère pas directement les tokens JWT.
    Cette responsabilité appartiendra à api/auth.py.
    """

    PASSWORD_ALGORITHM = "scrypt"

    def __init__(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        self.connection = connection

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create_user(
        self,
        data: UserCreate,
    ) -> User:
        """
        Crée un nouvel utilisateur.
        """

        email = str(data.email).strip().lower()

        if self.email_exists(email):
            raise ConflictError(
                "Un compte existe déjà avec cette adresse email."
            )

        password_hash = self.hash_password(
            data.password
        )

        user = User(
            email=email,
            password_hash=password_hash,
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            business_name=data.business_name,
            business_description=data.business_description,
        )

        query = """
            INSERT INTO users (
                email,
                password_hash,
                first_name,
                last_name,
                phone,
                business_name,
                business_description,
                is_active,
                is_verified,
                created_at,
                updated_at,
                last_login_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        values = (
            user.email,
            user.password_hash,
            user.first_name,
            user.last_name,
            user.phone,
            user.business_name,
            user.business_description,
            int(user.is_active),
            int(user.is_verified),
            user.created_at.isoformat(),
            user.updated_at.isoformat(),
            None,
        )

        try:
            cursor = self.connection.execute(
                query,
                values,
            )

            self.connection.commit()

            user.id = cursor.lastrowid

            return user

        except sqlite3.IntegrityError as exc:
            self.connection.rollback()

            raise ConflictError(
                "Impossible de créer cet utilisateur.",
                details={
                    "database_error": str(exc),
                },
            ) from exc

        except sqlite3.Error as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Une erreur est survenue lors de "
                "la création du compte."
            ) from exc

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def get_user(
        self,
        user_id: int,
    ) -> User:
        """
        Récupère un utilisateur par son identifiant.
        """

        query = """
            SELECT *
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
                "Impossible de récupérer l'utilisateur."
            ) from exc

        if row is None:
            raise UserNotFoundError(
                f"L'utilisateur {user_id} est introuvable."
            )

        return User.from_row(row)

    def get_user_by_email(
        self,
        email: str,
    ) -> User:
        """
        Récupère un utilisateur à partir de son email.
        """

        normalized_email = (
            email.strip().lower()
        )

        query = """
            SELECT *
            FROM users
            WHERE email = ?
            LIMIT 1
        """

        try:
            row = self.connection.execute(
                query,
                (normalized_email,),
            ).fetchone()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de rechercher l'utilisateur."
            ) from exc

        if row is None:
            raise UserNotFoundError(
                "Aucun utilisateur ne correspond "
                "à cette adresse email."
            )

        return User.from_row(row)

    def email_exists(
        self,
        email: str,
    ) -> bool:
        """
        Vérifie si une adresse email est déjà utilisée.
        """

        normalized_email = (
            email.strip().lower()
        )

        query = """
            SELECT 1
            FROM users
            WHERE email = ?
            LIMIT 1
        """

        try:
            row = self.connection.execute(
                query,
                (normalized_email,),
            ).fetchone()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de vérifier l'adresse email."
            ) from exc

        return row is not None

    # ------------------------------------------------------------------
    # AUTHENTICATION
    # ------------------------------------------------------------------

    def authenticate(
        self,
        *,
        email: str,
        password: str,
    ) -> User:
        """
        Vérifie les identifiants d'un utilisateur.

        Retourne l'utilisateur si les identifiants sont corrects.
        """

        try:
            user = self.get_user_by_email(email)

        except UserNotFoundError:
            raise

        if not self.verify_password(
            password,
            user.password_hash,
        ):
            raise UserNotFoundError(
                "Email ou mot de passe incorrect."
            )

        if not user.can_login():
            raise ConflictError(
                "Ce compte est actuellement désactivé."
            )

        user.register_login()

        self._save_login_time(user)

        return user

    # ------------------------------------------------------------------
    # PROFILE
    # ------------------------------------------------------------------

    def update_user(
        self,
        *,
        user_id: int,
        data: UserUpdate,
    ) -> User:
        """
        Modifie les informations du profil.
        """

        user = self.get_user(user_id)

        update_data = data.model_dump(
            exclude_unset=True
        )

        if not update_data:
            return user

        user.update_profile(
            first_name=update_data.get(
                "first_name"
            ),
            last_name=update_data.get(
                "last_name"
            ),
            phone=update_data.get(
                "phone"
            ),
            business_name=update_data.get(
                "business_name"
            ),
            business_description=update_data.get(
                "business_description"
            ),
        )

        query = """
            UPDATE users
            SET
                first_name = ?,
                last_name = ?,
                phone = ?,
                business_name = ?,
                business_description = ?,
                updated_at = ?
            WHERE id = ?
        """

        try:
            self.connection.execute(
                query,
                (
                    user.first_name,
                    user.last_name,
                    user.phone,
                    user.business_name,
                    user.business_description,
                    user.updated_at.isoformat(),
                    user.id,
                ),
            )

            self.connection.commit()

        except sqlite3.Error as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Impossible de modifier le profil."
            ) from exc

        return user

    # ------------------------------------------------------------------
    # STATUS
    # ------------------------------------------------------------------

    def activate_user(
        self,
        user_id: int,
    ) -> User:
        """
        Active un compte.
        """

        user = self.get_user(user_id)

        user.activate()

        self._save_status(user)

        return user

    def deactivate_user(
        self,
        user_id: int,
    ) -> User:
        """
        Désactive un compte.
        """

        user = self.get_user(user_id)

        user.deactivate()

        self._save_status(user)

        return user

    def verify_user(
        self,
        user_id: int,
    ) -> User:
        """
        Marque un utilisateur comme vérifié.
        """

        user = self.get_user(user_id)

        user.verify()

        query = """
            UPDATE users
            SET
                is_verified = ?,
                updated_at = ?
            WHERE id = ?
        """

        try:
            self.connection.execute(
                query,
                (
                    int(user.is_verified),
                    user.updated_at.isoformat(),
                    user.id,
                ),
            )

            self.connection.commit()

        except sqlite3.Error as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Impossible de vérifier l'utilisateur."
            ) from exc

        return user

    # ------------------------------------------------------------------
    # PASSWORD
    # ------------------------------------------------------------------

    def change_password(
        self,
        *,
        user_id: int,
        data: PasswordChange,
    ) -> User:
        """
        Modifie le mot de passe après vérification
        de l'ancien mot de passe.
        """

        user = self.get_user(user_id)

        if not self.verify_password(
            data.current_password,
            user.password_hash,
        ):
            raise ConflictError(
                "Le mot de passe actuel est incorrect."
            )

        new_hash = self.hash_password(
            data.new_password
        )

        user.password_hash = new_hash
        user.touch()

        query = """
            UPDATE users
            SET
                password_hash = ?,
                updated_at = ?
            WHERE id = ?
        """

        try:
            self.connection.execute(
                query,
                (
                    user.password_hash,
                    user.updated_at.isoformat(),
                    user.id,
                ),
            )

            self.connection.commit()

        except sqlite3.Error as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Impossible de modifier le mot de passe."
            ) from exc

        return user

    # ------------------------------------------------------------------
    # PASSWORD HASHING
    # ------------------------------------------------------------------

    @classmethod
    def hash_password(
        cls,
        password: str,
    ) -> str:
        """
        Hash sécurisé du mot de passe avec scrypt.

        Le format stocké est :

        scrypt$N$r$p$salt$hash
        """

        if not isinstance(password, str):
            raise TypeError(
                "Le mot de passe doit être une chaîne."
            )

        if len(password) < 8:
            raise ValueError(
                "Le mot de passe doit contenir "
                "au moins 8 caractères."
            )

        salt = os.urandom(16)

        n = 16384
        r = 8
        p = 1

        derived_key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=64,
        )

        return (
            f"{cls.PASSWORD_ALGORITHM}$"
            f"{n}$"
            f"{r}$"
            f"{p}$"
            f"{salt.hex()}$"
            f"{derived_key.hex()}"
        )

    @classmethod
    def verify_password(
        cls,
        password: str,
        stored_hash: str,
    ) -> bool:
        """
        Vérifie un mot de passe contre son hash.
        """

        try:
            (
                algorithm,
                n,
                r,
                p,
                salt_hex,
                hash_hex,
            ) = stored_hash.split("$")

            if algorithm != cls.PASSWORD_ALGORITHM:
                return False

            salt = bytes.fromhex(
                salt_hex
            )

            expected_hash = bytes.fromhex(
                hash_hex
            )

            derived_key = hashlib.scrypt(
                password.encode("utf-8"),
                salt=salt,
                n=int(n),
                r=int(r),
                p=int(p),
                dklen=len(expected_hash),
            )

            return hmac.compare_digest(
                derived_key,
                expected_hash,
            )

        except (
            ValueError,
            TypeError,
            AttributeError,
        ):
            return False

    # ------------------------------------------------------------------
    # DATABASE HELPERS
    # ------------------------------------------------------------------

    def _save_login_time(
        self,
        user: User,
    ) -> None:
        query = """
            UPDATE users
            SET
                last_login_at = ?,
                updated_at = ?
            WHERE id = ?
        """

        try:
            self.connection.execute(
                query,
                (
                    user.last_login_at.isoformat()
                    if user.last_login_at
                    else None,
                    user.updated_at.isoformat(),
                    user.id,
                ),
            )

            self.connection.commit()

        except sqlite3.Error as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Impossible d'enregistrer la connexion."
            ) from exc

    def _save_status(
        self,
        user: User,
    ) -> None:
        query = """
            UPDATE users
            SET
                is_active = ?,
                updated_at = ?
            WHERE id = ?
        """

        try:
            self.connection.execute(
                query,
                (
                    int(user.is_active),
                    user.updated_at.isoformat(),
                    user.id,
                ),
            )

            self.connection.commit()

        except sqlite3.Error as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Impossible de modifier le statut "
                "de l'utilisateur."
            ) from exc