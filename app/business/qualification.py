from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QualificationResult:
    status: str = "unknown"
    confidence: float = 0.0

    needs_identified: bool = False
    budget_identified: bool = False
    timeline_identified: bool = False
    decision_maker_identified: bool = False
    product_fit_identified: bool = False

    needs: list[str] = field(default_factory=list)
    objections: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    positive_signals: list[str] = field(default_factory=list)
    negative_signals: list[str] = field(default_factory=list)

    budget: float | None = None
    currency: str | None = None

    timeline: str | None = None
    decision_maker: str | None = None

    recommended_next_step: str | None = None

    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "confidence": self.confidence,
            "needs_identified": self.needs_identified,
            "budget_identified": self.budget_identified,
            "timeline_identified": self.timeline_identified,
            "decision_maker_identified": self.decision_maker_identified,
            "product_fit_identified": self.product_fit_identified,
            "needs": self.needs,
            "objections": self.objections,
            "missing_information": self.missing_information,
            "positive_signals": self.positive_signals,
            "negative_signals": self.negative_signals,
            "budget": self.budget,
            "currency": self.currency,
            "timeline": self.timeline,
            "decision_maker": self.decision_maker,
            "recommended_next_step": self.recommended_next_step,
            "evidence": self.evidence,
        }


class QualificationEngine:
    """
    Analyse un prospect à partir des données disponibles.

    Le moteur reste volontairement indépendant de l'IA.
    L'IA peut fournir des signaux, mais cette classe transforme
    ces signaux en état commercial exploitable.
    """

    STATUS_ORDER = {
        "unknown": 0,
        "unqualified": 1,
        "identified": 2,
        "qualified": 3,
        "highly_qualified": 4,
        "customer": 5,
        "disqualified": -1,
    }

    def qualify(
        self,
        *,
        needs: list[str] | None = None,
        budget: float | None = None,
        currency: str | None = None,
        timeline: str | None = None,
        decision_maker: str | None = None,
        product_fit: bool | None = None,
        positive_signals: list[str] | None = None,
        negative_signals: list[str] | None = None,
        objections: list[str] | None = None,
        evidence: list[str] | None = None,
    ) -> QualificationResult:

        result = QualificationResult(
            needs=needs or [],
            budget=budget,
            currency=currency,
            timeline=timeline,
            decision_maker=decision_maker,
            positive_signals=positive_signals or [],
            negative_signals=negative_signals or [],
            objections=objections or [],
            evidence=evidence or [],
        )

        result.needs_identified = bool(result.needs)
        result.budget_identified = budget is not None
        result.timeline_identified = bool(timeline)
        result.decision_maker_identified = bool(decision_maker)
        result.product_fit_identified = product_fit is True

        if result.negative_signals and not result.positive_signals:
            result.status = "disqualified"
            result.confidence = 0.9
            result.recommended_next_step = "stop"
            return result

        points = 0

        if result.needs_identified:
            points += 2

        if result.budget_identified:
            points += 2

        if result.timeline_identified:
            points += 2

        if result.decision_maker_identified:
            points += 1

        if result.product_fit_identified:
            points += 2

        if result.positive_signals:
            points += min(len(result.positive_signals), 3)

        if result.objections:
            points -= min(len(result.objections), 2)

        if points <= 0:
            result.status = "unqualified"
            result.recommended_next_step = "ask"
        elif points <= 3:
            result.status = "identified"
            result.recommended_next_step = "qualify"
        elif points <= 6:
            result.status = "qualified"
            result.recommended_next_step = "advance"
        else:
            result.status = "highly_qualified"
            result.recommended_next_step = "convert"

        result.confidence = min(
            1.0,
            0.45 + (abs(points) * 0.07),
        )

        return result

    def merge(
        self,
        current: QualificationResult,
        new: QualificationResult,
    ) -> QualificationResult:
        return self.qualify(
            needs=list(
                dict.fromkeys(
                    current.needs + new.needs
                )
            ),
            budget=new.budget if new.budget is not None else current.budget,
            currency=new.currency or current.currency,
            timeline=new.timeline or current.timeline,
            decision_maker=(
                new.decision_maker
                or current.decision_maker
            ),
            product_fit=(
                new.product_fit_identified
                or current.product_fit_identified
            ),
            positive_signals=list(
                dict.fromkeys(
                    current.positive_signals
                    + new.positive_signals
                )
            ),
            negative_signals=list(
                dict.fromkeys(
                    current.negative_signals
                    + new.negative_signals
                )
            ),
            objections=list(
                dict.fromkeys(
                    current.objections
                    + new.objections
                )
            ),
            evidence=list(
                dict.fromkeys(
                    current.evidence
                    + new.evidence
                )
            ),
        )

    def compare_status(
        self,
        first: str,
        second: str,
    ) -> int:
        return (
            self.STATUS_ORDER.get(first, 0)
            - self.STATUS_ORDER.get(second, 0)
        )

    def is_more_qualified(
        self,
        first: QualificationResult,
        second: QualificationResult,
    ) -> bool:
        return (
            self.STATUS_ORDER.get(first.status, 0)
            >
            self.STATUS_ORDER.get(second.status, 0)
        )

    def next_question(
        self,
        result: QualificationResult,
    ) -> str | None:

        if not result.needs_identified:
            return "Quel est exactement votre besoin ?"

        if not result.product_fit_identified:
            return "Quel produit ou service recherchez-vous exactement ?"

        if not result.budget_identified:
            return "Avez-vous déjà prévu un budget pour ce projet ?"

        if not result.timeline_identified:
            return "Pour quand souhaitez-vous mettre cela en place ?"

        if not result.decision_maker_identified:
            return "Est-ce vous qui prenez la décision finale ?"

        return None

    def ai_context(
        self,
        result: QualificationResult,
    ) -> dict[str, Any]:
        return {
            "qualification_status": result.status,
            "confidence": result.confidence,
            "needs": result.needs,
            "budget": result.budget,
            "currency": result.currency,
            "timeline": result.timeline,
            "decision_maker": result.decision_maker,
            "product_fit": result.product_fit_identified,
            "positive_signals": result.positive_signals,
            "negative_signals": result.negative_signals,
            "objections": result.objections,
            "missing_information": result.missing_information,
            "recommended_next_step": result.recommended_next_step,
        }