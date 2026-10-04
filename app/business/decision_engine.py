from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.business.rules import (
    BusinessRule,
    BusinessRuleEngine,
    RuleResult,
)
from app.business.scoring import ScoringResult


@dataclass
class DecisionResult:
    action: str = "wait"

    confidence: float = 0.0
    priority: str = "normal"

    reason: str = ""

    response_required: bool = False
    response_text: str | None = None

    require_human: bool = False
    follow_up: bool = False

    stop: bool = False

    matched_rules: list[str] = field(default_factory=list)
    blocked_actions: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    detected_intent: str | None = None
    qualification_status: str | None = None

    score: float = 0.0
    temperature: str = "faible"

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "confidence": self.confidence,
            "priority": self.priority,
            "reason": self.reason,
            "response_required": self.response_required,
            "response_text": self.response_text,
            "require_human": self.require_human,
            "follow_up": self.follow_up,
            "stop": self.stop,
            "matched_rules": self.matched_rules,
            "blocked_actions": self.blocked_actions,
            "conflicts": self.conflicts,
            "detected_intent": self.detected_intent,
            "qualification_status": self.qualification_status,
            "score": self.score,
            "temperature": self.temperature,
            "metadata": self.metadata,
        }


class DecisionEngine:
    """
    Cerveau de décision commercial de VYRA.

    Il combine :
    - score du prospect
    - température
    - intention
    - qualification
    - règles commerciales
    - contraintes humaines
    """

    VALID_ACTIONS = {
        "respond",
        "ask",
        "follow_up",
        "wait",
        "human",
        "stop",
        "nurture",
        "convert",
    }

    ACTION_PRIORITY = {
        "stop": 100,
        "human": 90,
        "convert": 80,
        "respond": 70,
        "ask": 60,
        "follow_up": 50,
        "nurture": 30,
        "wait": 10,
    }

    def __init__(
        self,
        rules: list[BusinessRule] | None = None,
    ) -> None:
        self.rule_engine = BusinessRuleEngine(
            rules
        )

    def decide(
        self,
        *,
        scoring: ScoringResult,
        intent: str | None = None,
        qualification_status: str | None = None,
        sales_stage: str | None = None,
        signals: list[str] | None = None,
        response_available: bool = True,
        human_requested: bool = False,
    ) -> DecisionResult:

        result = DecisionResult(
            score=scoring.score,
            temperature=scoring.temperature,
            priority=scoring.priority,
            detected_intent=intent,
            qualification_status=qualification_status,
        )

        if human_requested:
            return self._human_decision(
                result,
                "Le client demande une intervention humaine.",
            )

        if scoring.negative_signal >= 80:
            return self._stop_decision(
                result,
                "Signaux négatifs ou disqualifiants importants.",
            )

        rule_results = self.rule_engine.evaluate(
            score=scoring.score,
            temperature=scoring.temperature,
            intent=intent,
            signals=signals,
            qualification_status=qualification_status,
            sales_stage=sales_stage,
        )

        result.matched_rules = [
            item.rule_id
            for item in rule_results
        ]

        if rule_results:
            selected = self._select_rule(
                rule_results
            )

            result.action = (
                selected.action
                or scoring.recommended_action
            )

            result.reason = (
                selected.reason
                or "Règle commerciale appliquée."
            )

            result.metadata[
                "rules"
            ] = self.rule_engine.context(
                rule_results
            )

            if self.rule_engine.has_stop_rule(
                rule_results
            ):
                result.stop = True
                result.action = "stop"

            if any(
                self._rule_requires_human(
                    rule_id
                )
                for rule_id in result.matched_rules
            ):
                result.require_human = True
                result.action = "human"

        else:
            result.action = (
                scoring.recommended_action
            )

            result.reason = (
                "Décision basée sur le score "
                "commercial."
            )

        result.action = self._sanitize_action(
            result.action
        )

        result.follow_up = (
            result.action == "follow_up"
        )

        result.response_required = (
            result.action
            in {"respond", "ask", "convert"}
        )

        if not response_available:
            result.response_required = False

            if result.action in {
                "respond",
                "ask",
                "convert",
            }:
                result.action = "wait"

        result.confidence = self._calculate_confidence(
            scoring,
            result,
        )

        return result

    def _select_rule(
        self,
        results: list[RuleResult],
    ) -> RuleResult:

        return max(
            results,
            key=lambda item: (
                item.priority,
                self.ACTION_PRIORITY.get(
                    item.action or "wait",
                    0,
                ),
            ),
        )

    def _rule_requires_human(
        self,
        rule_id: str,
    ) -> bool:

        for rule in self.rule_engine.rules:
            if rule.rule_id == rule_id:
                return rule.require_human

        return False

    def _sanitize_action(
        self,
        action: str | None,
    ) -> str:

        if action in self.VALID_ACTIONS:
            return action

        return "wait"

    def _calculate_confidence(
        self,
        scoring: ScoringResult,
        decision: DecisionResult,
    ) -> float:

        confidence = scoring.confidence

        if decision.matched_rules:
            confidence += 0.10

        if decision.require_human:
            confidence = min(
                confidence,
                0.95,
            )

        return round(
            min(1.0, max(0.0, confidence)),
            3,
        )

    def _human_decision(
        self,
        result: DecisionResult,
        reason: str,
    ) -> DecisionResult:

        result.action = "human"
        result.require_human = True
        result.response_required = False
        result.reason = reason
        result.confidence = 1.0

        return result

    def _stop_decision(
        self,
        result: DecisionResult,
        reason: str,
    ) -> DecisionResult:

        result.action = "stop"
        result.stop = True
        result.response_required = False
        result.reason = reason
        result.confidence = 1.0

        return result

    def add_rule(
        self,
        rule: BusinessRule,
    ) -> "DecisionEngine":

        self.rule_engine.add_rule(rule)
        return self

    def evaluate_rules(
        self,
        **kwargs: Any,
    ) -> list[RuleResult]:

        return self.rule_engine.evaluate(
            **kwargs
        )

    def ai_context(
        self,
        result: DecisionResult,
    ) -> dict[str, Any]:

        return {
            "action": result.action,
            "confidence": result.confidence,
            "priority": result.priority,
            "reason": result.reason,
            "response_required": result.response_required,
            "require_human": result.require_human,
            "follow_up": result.follow_up,
            "stop": result.stop,
            "detected_intent": result.detected_intent,
            "qualification_status": result.qualification_status,
            "score": result.score,
            "temperature": result.temperature,
            "matched_rules": result.matched_rules,
            "blocked_actions": result.blocked_actions,
            "conflicts": result.conflicts,
        }