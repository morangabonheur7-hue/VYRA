from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CompanyProduct:
    """
    Produit appartenant à une entreprise VYRA.

    V2 :
    - catalogue produit
    - prix
    - disponibilité
    - description
    - caractéristiques
    - variantes
    - zones de vente
    - règles commerciales

    V3 :
    - produit recommandé selon l'intention du prospect
    - qualification commerciale
    - scoring
    - détection d'intérêt
    - aide à la décision
    """

    id: int | None = None

    # ============================================================
    # RELATION ENTREPRISE
    # ============================================================

    company_id: int | None = None

    # ============================================================
    # IDENTITÉ DU PRODUIT
    # ============================================================

    name: str = ""

    sku: str | None = None

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

    variants: list[dict[str, Any]] = field(
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
    # PROMOTIONS
    # ============================================================

    promotional_price: Decimal | None = None

    promotion_active: bool = False

    promotion_description: str | None = None

    discount_percentage: Decimal | None = None

    # ============================================================
    # STOCK / DISPONIBILITÉ
    # ============================================================

    stock_quantity: int | None = None

    stock_tracking_enabled: bool = False

    in_stock: bool = True

    availability_status: str = "available"

    availability_description: str | None = None

    # ============================================================
    # VENTE
    # ============================================================

    active: bool = True

    featured: bool = False

    sales_priority: int = 0

    minimum_order_quantity: int = 1

    maximum_order_quantity: int | None = None

    # ============================================================
    # LIVRAISON
    # ============================================================

    delivery_available: bool = True

    delivery_areas: list[str] = field(
        default_factory=list
    )

    delivery_time: str | None = None

    delivery_fee: Decimal | None = None

    # ============================================================
    # PAIEMENT
    # ============================================================

    payment_methods: list[str] = field(
        default_factory=list
    )

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

    return_policy: str | None = None

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
    # INTENTIONS ASSOCIÉES — V3
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
    # MÉDIAS / RÉFÉRENCES
    # ============================================================

    image_url: str | None = None

    gallery_urls: list[str] = field(
        default_factory=list
    )

    product_url: str | None = None

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
    # CONVERSION DEPUIS POSTGRESQL
    # ============================================================

    @classmethod
    def from_row(
        cls,
        row: Any,
    ) -> "CompanyProduct":
        """
        Construit un produit depuis une ligne PostgreSQL.

        Compatible avec les mappings retournés
        par les curseurs PostgreSQL.
        """

        if row is None:
            raise ValueError(
                "Impossible de créer CompanyProduct "
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
    # PRIX POUR L'IA
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
        Retourne les informations utiles au moteur IA
        sans exposer inutilement toute la structure interne.
        """

        return {
            "product": {
                "name": self.name,
                "category": self.category,
                "description": self.description,
                "short_description": (
                    self.short_description
                ),
                "features": self.features,
                "specifications": self.specifications,
                "variants": self.variants,
                "tags": self.tags,
                "keywords": self.keywords,
            },
            "commercial": {
                "price": self.get_price_context(),
                "availability": self.availability_status,
                "in_stock": self.in_stock,
                "negotiable": self.negotiable,
                "sales_conditions": self.sales_conditions,
                "discount_conditions": (
                    self.discount_conditions
                ),
                "payment_methods": self.payment_methods,
                "delivery_available": (
                    self.delivery_available
                ),
                "delivery_areas": self.delivery_areas,
                "delivery_time": self.delivery_time,
                "delivery_fee": self.delivery_fee,
                "warranty": self.warranty,
                "return_policy": self.return_policy,
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

        if not self.in_stock:
            return False

        if (
            self.stock_tracking_enabled
            and self.stock_quantity is not None
            and self.stock_quantity <= 0
        ):
            return False

        return self.availability_status == "available"

    # ============================================================
    # STOCK
    # ============================================================

    def has_stock(self, quantity: int = 1) -> bool:
        if quantity <= 0:
            return False

        if not self.stock_tracking_enabled:
            return self.in_stock

        if self.stock_quantity is None:
            return self.in_stock

        return self.stock_quantity >= quantity

    # ============================================================
    # QUANTITÉ
    # ============================================================

    def can_sell_quantity(
        self,
        quantity: int,
    ) -> bool:
        if quantity < self.minimum_order_quantity:
            return False

        if (
            self.maximum_order_quantity is not None
            and quantity > self.maximum_order_quantity
        ):
            return False

        return self.has_stock(quantity)

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
    # VALEUR DU PRODUIT
    # ============================================================

    def is_high_value_product(self) -> bool:
        if self.high_value:
            return True

        if (
            self.high_value_threshold is not None
            and self.price is not None
        ):
            return self.price >= self.high_value_threshold

        return False

    # ============================================================
    # PRIORITÉ
    # ============================================================

    def get_sales_priority(self) -> int:
        """
        Retourne une priorité commerciale comprise
        entre 0 et 100.
        """

        return max(
            0,
            min(100, self.sales_priority),
        )

    # ============================================================
    # ACTIVATION
    # ============================================================

    def activate(self) -> None:
        self.active = True
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
        self.promotional_price = promotional_price
        self.promotion_active = True
        self.promotion_description = description
        self.touch()

    def deactivate_promotion(self) -> None:
        self.promotion_active = False
        self.touch()

    # ============================================================
    # STOCK
    # ============================================================

    def update_stock(
        self,
        quantity: int,
    ) -> None:
        if quantity < 0:
            raise ValueError(
                "La quantité en stock ne peut pas être négative."
            )

        self.stock_quantity = quantity
        self.stock_tracking_enabled = True
        self.in_stock = quantity > 0

        if quantity <= 0:
            self.availability_status = "out_of_stock"
        else:
            self.availability_status = "available"

        self.touch()

    # ============================================================
    # DATE DE MODIFICATION
    # ============================================================

    def touch(self) -> None:
        self.updated_at = _utcnow()