from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuleResult:
    rule_id: str
    matched: bool = False
    action: str | None = None
    reason: str | None = None
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BusinessRule:
    rule_id: str
    name: str
    description: str = ""

    active: bool = True
    priority: int = 0

    action: str = "respond"

    min_score: float | None = None
    max_score: float | None = None

    temperatures: list[str] = field(default_factory=list)
    intents: list[str] = field(default_factory=list)
    required_signals: list[str] = field(default_factory=list)
    excluded_signals: list[str] = field(default_factory=list)

    qualification_statuses: list[str] = field(default_factory=list)
    sales_stages: list[str] = field(default_factory=list)

    require_human: bool = False
    stop: bool = False

    conditions: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def matches(
        self,
        *,
        score: float = 0.0,
        temperature: str | None = None,
        intent: str | None = None,
        signals: list[str] | None = None,
        qualification_status: str | None = None,
        sales_stage: str | None = None,
    ) -> bool:

        if not self.active:
            return False

        if self.min_score is not None and score < self.min_score:
            return False

        if self.max_score is not None and score > self.max_score:
            return False

        if self.temperatures:
            if temperature not in self.temperatures:
                return False

        if self.intents:
            if intent not in self.intents:
                return False

        if self.qualification_statuses:
            if qualification_status not in self.qualification_statuses:
                return False

        if self.sales_stages:
            if sales_stage not in self.sales_stages:
                return False

        current_signals = set(signals or [])

        if self.required_signals:
            if not set(self.required_signals).issubset(
                current_signals
            ):
                return False

        if self.excluded_signals:
            if current_signals.intersection(
                self.excluded_signals
            ):
                return False

        return True

    def evaluate(
        self,
        **kwargs: Any,
    ) -> RuleResult:

        matched = self.matches(**kwargs)

        return RuleResult(
            rule_id=self.rule_id,
            matched=matched,
            action=self.action if matched else None,
            reason=(
                self.description
                if matched
                else None
            ),
            priority=self.priority,
            metadata=dict(self.metadata),
        )


class BusinessRuleEngine:
    """
    Évalue les règles commerciales dans un ordre déterministe.

    Les règles ne dépendent pas directement du fournisseur IA.
    """

    def __init__(
        self,
        rules: list[BusinessRule] | None = None,
    ) -> None:
        self.rules = rules or []

    def add_rule(
        self,
        rule: BusinessRule,
    ) -> "BusinessRuleEngine":
        self.rules.append(rule)
        return self

    def remove_rule(
        self,
        rule_id: str,
    ) -> bool:
        original = len(self.rules)

        self.rules = [
            rule
            for rule in self.rules
            if rule.rule_id != rule_id
        ]

        return len(self.rules) != original

    def evaluate(
        self,
        *,
        score: float = 0.0,
        temperature: str | None = None,
        intent: str | None = None,
        signals: list[str] | None = None,
        qualification_status: str | None = None,
        sales_stage: str | None = None,
    ) -> list[RuleResult]:

        ordered_rules = sorted(
            self.rules,
            key=lambda rule: rule.priority,
            reverse=True,
        )

        results: list[RuleResult] = []

        for rule in ordered_rules:
            result = rule.evaluate(
                score=score,
                temperature=temperature,
                intent=intent,
                signals=signals,
                qualification_status=qualification_status,
                sales_stage=sales_stage,
            )

            if result.matched:
                results.append(result)

        return results

    def first_match(
        self,
        **kwargs: Any,
    ) -> RuleResult | None:

        results = self.evaluate(**kwargs)

        return results[0] if results else None

    def has_stop_rule(
        self,
        results: list[RuleResult],
    ) -> bool:

        matched_ids = {
            result.rule_id
            for result in results
            if result.matched
        }

        return any(
            rule.stop
            and rule.rule_id in matched_ids
            for rule in self.rules
        )

    def context(
        self,
        results: list[RuleResult],
    ) -> dict[str, Any]:

        return {
            "matched_rules": [
                result.rule_id
                for result in results
            ],
            "actions": [
                result.action
                for result in results
                if result.action
            ],
            "reasons": [
                result.reason
                for result in results
                if result.reason
            ],
        }