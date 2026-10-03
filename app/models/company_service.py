from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CompanyService:
    """
    Service / prestation appartenant à une entreprise VYRA.

    V2 :
    - catalogue de services
    - description
    - prix
    - durée
    - disponibilité
    - zones couvertes
    - conditions
    - moyens de paiement
    - réservation

    V3 :
    - détection d'intention
    - signaux d'achat
    - qualification
    - scoring
    - recommandation de service
    - décision commerciale
    """

    id: int | None = None

    # ============================================================
    # RELATION ENTREPRISE
    # ============================================================

    company_id: int | None = None

    # ============================================================
    # IDENTITÉ
    # ============================================================

    name: str = ""

    code: str | None = None

    category: str | None = None

    subcategory: str | None = None

    description: str | None = None

    short_description: str | None = None

    # ============================================================
    # CARACTÉRISTIQUES
    # ============================================================

    features: list[str] = field(
        default_factory=list
    )

    specifications: dict[str, Any] = field(
        default_factory=dict
    )

    requirements: list[str] = field(
        default_factory=list
    )

    included_items: list[str] = field(
        default_factory=list
    )

    excluded_items: list[str] = field(
        default_factory=list
    )

    tags: list[str] = field(
        default_factory=list
    )

    keywords: list[str] = field(
        default_factory=list
    )

    # ============================================================
    # PRIX
    # ============================================================

    price: Decimal | None = None

    currency: str = "XAF"

    price_type: str = "fixed"

    minimum_price: Decimal | None = None

    maximum_price: Decimal | None = None

    negotiable: bool = False

    # ============================================================
    # PROMOTION
    # ============================================================

    promotional_price: Decimal | None = None

    promotion_active: bool = False

    promotion_description: str | None = None

    discount_percentage: Decimal | None = None

    # ============================================================
    # DURÉE
    # ============================================================

    duration_minutes: int | None = None

    duration_description: str | None = None

    # ============================================================
    # DISPONIBILITÉ
    # ============================================================

    active: bool = True

    availability_status: str = "available"

    availability_description: str | None = None

    advance_booking_required: bool = False

    minimum_booking_notice_hours: int = 0

    maximum_booking_days_ahead: int | None = None

    # ============================================================
    # CAPACITÉ
    # ============================================================

    capacity: int | None = None

    concurrent_capacity: int | None = None

    # ============================================================
    # ZONES
    # ============================================================

    service_areas: list[str] = field(
        default_factory=list
    )

    remote_service: bool = True

    onsite_service: bool = False

    # ============================================================
    # RÉSERVATION
    # ============================================================

    booking_enabled: bool = False

    booking_url: str | None = None

    booking_instructions: str | None = None

    cancellation_policy: str | None = None

    rescheduling_policy: str | None = None

    # ============================================================
    # PAIEMENT
    # ============================================================

    payment_methods: list[str] = field(
        default_factory=list
    )

    payment_before_service: bool = False

    installment_available: bool = False

    installment_description: str | None = None

    # ============================================================
    # CONDITIONS COMMERCIALES
    # ============================================================

    sales_conditions: list[str] = field(
        default_factory=list
    )

    discount_conditions: list[str] = field(
        default_factory=list
    )

    refund_policy: str | None = None

    warranty: str | None = None

    # ============================================================
    # CIBLE COMMERCIALE — V3
    # ============================================================

    target_customers: list[str] = field(
        default_factory=list
    )

    target_segments: list[str] = field(
        default_factory=list
    )

    ideal_customer_profile: str | None = None

    # ============================================================
    # INTENTIONS — V3
    # ============================================================

    relevant_intents: list[str] = field(
        default_factory=list
    )

    buying_signals: list[str] = field(
        default_factory=list
    )

    disqualifying_signals: list[str] = field(
        default_factory=list
    )

    # ============================================================
    # QUALIFICATION — V3
    # ============================================================

    qualification_questions: list[str] = field(
        default_factory=list
    )

    required_customer_information: list[str] = field(
        default_factory=list
    )

    qualification_rules: dict[str, Any] = field(
        default_factory=dict
    )

    # ============================================================
    # SCORING — V3
    # ============================================================

    scoring_weight: float = 1.0

    high_value: bool = False

    high_value_threshold: Decimal | None = None

    sales_priority: int = 0

    # ============================================================
    # RECOMMANDATION — V3
    # ============================================================

    recommendation_enabled: bool = True

    recommendation_reasons: list[str] = field(
        default_factory=list
    )

    alternative_service_ids: list[int] = field(
        default_factory=list
    )

    complementary_service_ids: list[int] = field(
        default_factory=list
    )

    # ============================================================
    # IA
    # ============================================================

    ai_description: str | None = None

    ai_instructions: str | None = None

    recommended_response: str | None = None

    forbidden_claims: list[str] = field(
        default_factory=list
    )

    # ============================================================
    # MÉDIAS / LIENS
    # ============================================================

    image_url: str | None = None

    gallery_urls: list[str] = field(
        default_factory=list
    )

    service_url: str | None = None

    # ============================================================
    # DATES
    # ============================================================

    created_at: datetime = field(
        default_factory=_utcnow
    )

    updated_at: datetime = field(
        default_factory=_utcnow
    )

    # ============================================================
    # POSTGRESQL → MODEL
    # ============================================================

    @classmethod
    def from_row(
        cls,
        row: Any,
    ) -> "CompanyService":
        """
        Construit un service depuis une ligne PostgreSQL.
        """

        if row is None:
            raise ValueError(
                "Impossible de créer CompanyService "
                "à partir d'une ligne vide."
            )

        if hasattr(row, "keys"):
            data = dict(row)

        elif hasattr(row, "_asdict"):
            data = row._asdict()

        else:
            raise TypeError(
                "La ligne PostgreSQL doit être un mapping "
                "ou fournir _asdict()."
            )

        valid_fields = {
            field_name
            for field_name in cls.__dataclass_fields__
        }

        cleaned = {
            key: value
            for key, value in data.items()
            if key in valid_fields
        }

        return cls(**cleaned)

    # ============================================================
    # SERIALISATION
    # ============================================================

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    # ============================================================
    # PRIX EFFECTIF
    # ============================================================

    def get_effective_price(self) -> Decimal | None:
        """
        Retourne le prix actuellement applicable.
        """

        if (
            self.promotion_active
            and self.promotional_price is not None
        ):
            return self.promotional_price

        return self.price

    # ============================================================
    # CONTEXTE PRIX
    # ============================================================

    def get_price_context(self) -> dict[str, Any]:
        return {
            "price": self.price,
            "promotional_price": (
                self.promotional_price
                if self.promotion_active
                else None
            ),
            "currency": self.currency,
            "price_type": self.price_type,
            "minimum_price": self.minimum_price,
            "maximum_price": self.maximum_price,
            "negotiable": self.negotiable,
            "promotion_active": self.promotion_active,
            "discount_percentage": (
                self.discount_percentage
            ),
        }

    # ============================================================
    # CONTEXTE IA
    # ============================================================

    def get_ai_context(self) -> dict[str, Any]:
        """
        Retourne les informations utiles au moteur IA.
        """

        return {
            "service": {
                "name": self.name,
                "category": self.category,
                "description": self.description,
                "short_description": (
                    self.short_description
                ),
                "features": self.features,
                "specifications": self.specifications,
                "requirements": self.requirements,
                "included_items": self.included_items,
                "excluded_items": self.excluded_items,
                "tags": self.tags,
                "keywords": self.keywords,
            },
            "commercial": {
                "price": self.get_price_context(),
                "availability": self.availability_status,
                "sales_conditions": self.sales_conditions,
                "discount_conditions": (
                    self.discount_conditions
                ),
                "payment_methods": self.payment_methods,
                "payment_before_service": (
                    self.payment_before_service
                ),
                "refund_policy": self.refund_policy,
                "warranty": self.warranty,
            },
            "duration": {
                "minutes": self.duration_minutes,
                "description": (
                    self.duration_description
                ),
            },
            "service_area": {
                "areas": self.service_areas,
                "remote": self.remote_service,
                "onsite": self.onsite_service,
            },
            "booking": {
                "enabled": self.booking_enabled,
                "advance_required": (
                    self.advance_booking_required
                ),
                "minimum_notice_hours": (
                    self.minimum_booking_notice_hours
                ),
                "maximum_days_ahead": (
                    self.maximum_booking_days_ahead
                ),
            },
            "target": {
                "customers": self.target_customers,
                "segments": self.target_segments,
                "ideal_customer_profile": (
                    self.ideal_customer_profile
                ),
            },
            "v3": {
                "relevant_intents": (
                    self.relevant_intents
                ),
                "buying_signals": (
                    self.buying_signals
                ),
                "disqualifying_signals": (
                    self.disqualifying_signals
                ),
                "qualification_questions": (
                    self.qualification_questions
                ),
                "required_customer_information": (
                    self.required_customer_information
                ),
                "qualification_rules": (
                    self.qualification_rules
                ),
                "scoring_weight": (
                    self.scoring_weight
                ),
                "high_value": self.high_value,
                "sales_priority": self.sales_priority,
            },
            "recommendation": {
                "enabled": self.recommendation_enabled,
                "reasons": self.recommendation_reasons,
                "alternatives": (
                    self.alternative_service_ids
                ),
                "complementary": (
                    self.complementary_service_ids
                ),
            },
            "ai": {
                "description": self.ai_description,
                "instructions": self.ai_instructions,
                "recommended_response": (
                    self.recommended_response
                ),
                "forbidden_claims": (
                    self.forbidden_claims
                ),
            },
        }

    # ============================================================
    # DISPONIBILITÉ
    # ============================================================

    def is_available(self) -> bool:
        if not self.active:
            return False

        return self.availability_status == "available"

    # ============================================================
    # RÉSERVATION
    # ============================================================

    def can_be_booked(self) -> bool:
        return (
            self.active
            and self.is_available()
            and self.booking_enabled
        )

    # ============================================================
    # INTENTION
    # ============================================================

    def matches_intent(
        self,
        intent: str,
    ) -> bool:
        normalized = intent.strip().lower()

        return normalized in {
            item.strip().lower()
            for item in self.relevant_intents
        }

    # ============================================================
    # SIGNAL D'ACHAT
    # ============================================================

    def has_buying_signal(
        self,
        signal: str,
    ) -> bool:
        normalized = signal.strip().lower()

        return normalized in {
            item.strip().lower()
            for item in self.buying_signals
        }

    # ============================================================
    # SIGNAL DISQUALIFIANT
    # ============================================================

    def has_disqualifying_signal(
        self,
        signal: str,
    ) -> bool:
        normalized = signal.strip().lower()

        return normalized in {
            item.strip().lower()
            for item in self.disqualifying_signals
        }

    # ============================================================
    # VALEUR COMMERCIALE
    # ============================================================

    def is_high_value_service(self) -> bool:
        if self.high_value:
            return True

        if (
            self.high_value_threshold is not None
            and self.price is not None
        ):
            return self.price >= self.high_value_threshold

        return False

    # ============================================================
    # PRIORITÉ COMMERCIALE
    # ============================================================

    def get_sales_priority(self) -> int:
        return max(
            0,
            min(100, self.sales_priority),
        )

    # ============================================================
    # RECOMMANDATION
    # ============================================================

    def can_be_recommended(self) -> bool:
        return (
            self.active
            and self.recommendation_enabled
            and self.is_available()
        )

    # ============================================================
    # ACTIVATION
    # ============================================================

    def activate(self) -> None:
        self.active = True
        self.availability_status = "available"
        self.touch()

    def deactivate(self) -> None:
        self.active = False
        self.touch()

    # ============================================================
    # PROMOTION
    # ============================================================

    def activate_promotion(
        self,
        promotional_price: Decimal,
        description: str | None = None,
    ) -> None:
        if promotional_price < 0:
            raise ValueError(
                "Le prix promotionnel ne peut pas être négatif."
            )

        self.promotional_price = promotional_price
        self.promotion_active = True
        self.promotion_description = description
        self.touch()

    def deactivate_promotion(self) -> None:
        self.promotion_active = False
        self.touch()

    # ============================================================
    # DISPONIBILITÉ
    # ============================================================

    def set_availability(
        self,
        status: str,
        description: str | None = None,
    ) -> None:
        allowed_statuses = {
            "available",
            "unavailable",
            "temporarily_unavailable",
            "coming_soon",
            "booking_required",
        }

        normalized_status = status.strip().lower()

        if normalized_status not in allowed_statuses:
            raise ValueError(
                "Statut de disponibilité invalide."
            )

        self.availability_status = normalized_status
        self.availability_description = description
        self.touch()

    # ============================================================
    # DATE DE MODIFICATION
    # ============================================================

    def touch(self) -> None:
        self.updated_at = _utcnow()