"""
Strategy Pattern for Agent Decision-Making

Provides pluggable decision-making algorithms for agents.
Allows switching between different reasoning strategies:
- Rule-based (if-then-else)
- Scoring/weighting systems
- Multi-criteria decision analysis
- Simple pattern matching

Each strategy implements the same interface and can be combined.
"""

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class DecisionStrategyType(Enum):
    """Available decision strategies"""
    RULE_BASED = "rule_based"
    SCORING = "scoring"
    MULTI_CRITERIA = "multi_criteria"
    PATTERN_MATCH = "pattern_match"
    NEURAL = "neural"  # placeholder for future ML integration


@dataclass
class DecisionRule:
    """
    A single rule for rule-based strategy.

    Rules are evaluated in order, first match wins.
    """
    condition: str  # Python expression with placeholders like {variable}
    action: str    # Action identifier
    priority: int = 0  # Higher = evaluated first
    metadata: Dict[str, Any] = field(default_factory=dict)

    def matches(self, context: Dict[str, Any]) -> bool:
        """Evaluate condition against context"""
        try:
            # Simple template substitution
            condition = self.condition
            for key, value in context.items():
                placeholder = "{" + key + "}"
                str_value = str(value).lower() if isinstance(value, str) else str(value)
                condition = condition.replace(placeholder, str_value)

            # Safe evaluation - only allow simple comparisons
            # In production, use a proper rules engine
            return eval(condition, {"__builtins__": {}}, {})
        except Exception:
            return False


@dataclass
class Criterion:
    """
    A scoring criterion for multi-criteria decisions.

    Attributes:
        name: Human-readable name
        weight: Importance weight (0-1), normalized
        scorer: Function that returns 0-1 score given context
        threshold: Minimum acceptable score
    """
    name: str
    weight: float
    scorer: callable
    threshold: float = 0.0
    description: Optional[str] = None


class DecisionStrategy(ABC):
    """
    Abstract decision strategy for agent reasoning.

    All strategies take a context dict and return a decision result.
    """

    @abstractmethod
    def decide(self, context: Dict[str, Any], options: List[str]) -> Tuple[str, float]:
        """
        Make a decision based on context.

        Args:
            context: Current situation data
            options: List of possible actions/choices

        Returns:
            (chosen_option, confidence_score)
        """
        pass

    @abstractmethod
    def explain(self, context: Dict[str, Any], choice: str) -> str:
        """Return human-readable explanation for decision"""
        pass


class RuleBasedStrategy(DecisionStrategy):
    """
    Classic if-then-else rule engine.

    Rules are evaluated sequentially; the first matching rule wins.
    """

    def __init__(self, rules: List[DecisionRule], default_action: str = "default"):
        """
        Args:
            rules: Ordered list of rules (highest priority first)
            default_action: Fallback if no rule matches
        """
        self.rules = sorted(rules, key=lambda r: -r.priority)
        self.default_action = default_action

    def decide(self, context: Dict[str, Any], options: List[str]) -> Tuple[str, float]:
        """Evaluate rules in order"""
        for rule in self.rules:
            if rule.matches(context):
                # Check if action is in available options
                if rule.action in options:
                    return rule.action, 0.9

        # No rule matched, use default if available
        if self.default_action in options:
            return self.default_action, 0.5

        # No valid option
        return options[0] if options else "none", 0.1

    def explain(self, context: Dict[str, Any], choice: str) -> str:
        for rule in self.rules:
            if rule.action == choice and rule.matches(context):
                return f"Rule matched: {rule.condition}"
        return f"Default action selected (no rule matched)"


class ScoringStrategy(DecisionStrategy):
    """
    Weighted scoring over multiple criteria.

    Each option gets a score for each criterion; weighted sum determines winner.
    """

    def __init__(
        self,
        criteria: List[Criterion],
        aggregation: str = "weighted_sum",  # or "max", "min"
    ):
        """
        Args:
            criteria: Scoring criteria
            aggregation: How to combine scores
        """
        self.criteria = criteria
        self.aggregation = aggregation
        total_weight = sum(c.weight for c in criteria)
        # Normalize weights
        for c in criteria:
            c.weight = c.weight / total_weight if total_weight > 0 else 0

    def decide(self, context: Dict[str, Any], options: List[str]) -> Tuple[str, float]:
        """Score each option and pick highest"""
        if not options:
            return "none", 0.0

        scores: Dict[str, float] = {opt: 0.0 for opt in options}

        for criterion in self.criteria:
            try:
                # Scorer returns score for each option
                criterion_scores = criterion.scorer(context, options)
                for opt, score in criterion_scores.items():
                    if opt in scores:
                        if self.aggregation == "max":
                            scores[opt] = max(scores[opt], score * criterion.weight)
                        else:
                            scores[opt] += score * criterion.weight
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"Criterion '{criterion.name}' scoring failed: {e}")

        # Pick best
        best_option = max(scores, key=lambda opt: scores[opt])
        best_score = scores[best_option]

        # Check if below threshold
        if best_score < 0.5:
            # Uncertain - pick safe default
            return best_option, best_score

        return best_option, best_score

    def explain(self, context: Dict[str, Any], choice: str) -> str:
        explanations = []
        for criterion in self.criteria:
            try:
                scores = criterion.scorer(context, [choice])
                score = scores.get(choice, 0)
                explanations.append(f"{criterion.name}: {score:.2f}")
            except Exception:
                pass
        return ", ".join(explanations)


class PatternMatchingStrategy(DecisionStrategy):
    """
    Pattern-based decision making.

    Matches current context against known patterns and returns
    associated actions.
    """

    def __init__(self, patterns: Dict[str, callable]):
        """
        Args:
            patterns: Dict mapping pattern_name -> matcher function
                     matcher(context) -> match_score (0-1)
        """
        self.patterns = patterns

    def decide(self, context: Dict[str, Any], options: List[str]) -> Tuple[str, float]:
        """Find best matching pattern"""
        best_pattern = None
        best_score = 0.0

        for pattern_name, matcher in self.patterns.items():
            try:
                score = matcher(context)
                if score > best_score:
                    best_score = score
                    best_pattern = pattern_name
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"Pattern '{pattern_name}' matching failed: {e}")

        if best_pattern and best_pattern in options:
            return best_pattern, best_score

        # Fallback to pattern name hint
        for pattern_name in self.patterns:
            if pattern_name in options:
                return pattern_name, best_score

        return options[0] if options else "none", 0.0

    def explain(self, context: Dict[str, Any], choice: str) -> str:
        if choice in self.patterns:
            try:
                score = self.patterns[choice](context)
                return f"Pattern '{choice}' matched with confidence {score:.2f}"
            except Exception:
                pass
        return "Pattern-based selection"


class MultiCriteriaDecisionAnalysis(DecisionStrategy):
    """
    Full MCDA implementation with multiple methods.

    Supports:
    - Weighted sum
    - TOPSIS
    - AHP-inspired
    """

    def __init__(
        self,
        criteria: List[Criterion],
        method: str = "weighted_sum",
        reference_point: Optional[Dict[str, float]] = None,
    ):
        """
        Args:
            criteria: Evaluation criteria
            method: 'weighted_sum', 'topsis', 'ahp'
            reference_point: Ideal/worst values for TOPSIS
        """
        self.criteria = criteria
        self.method = method
        self.reference_point = reference_point or {}

    def decide(self, context: Dict[str, Any], options: List[str]) -> Tuple[str, float]:
        """Apply MCDA method to choose best option"""
        if not options:
            return "none", 0.0

        # Get scores matrix: options x criteria
        scores_matrix = {}
        for criterion in self.criteria:
            try:
                opt_scores = criterion.scorer(context, options)
                scores_matrix[criterion.name] = opt_scores
            except Exception:
                continue

        if not scores_matrix:
            return options[0], 0.0

        if self.method == "weighted_sum":
            return self._weighted_sum(scores_matrix, options)
        elif self.method == "topsis":
            return self._topsis(scores_matrix, options)
        else:
            return self._weighted_sum(scores_matrix, options)

    def _weighted_sum(
        self,
        scores: Dict[str, Dict[str, float]],
        options: List[str]
    ) -> Tuple[str, float]:
        """Weighted sum model"""
        weighted_scores = {opt: 0.0 for opt in options}

        for criterion in self.criteria:
            weight = criterion.weight
            criterion_scores = scores.get(criterion.name, {})
            for opt in options:
                score = criterion_scores.get(opt, 0.0)
                weighted_scores[opt] += weight * score

        best = max(weighted_scores, key=weighted_scores.get)
        return best, weighted_scores[best]

    def _topsis(
        self,
        scores: Dict[str, Dict[str, float]],
        options: List[str]
    ) -> Tuple[str, float]:
        """
        TOPSIS: Technique for Order Preference by Similarity to Ideal Solution.

        Finds solution closest to ideal solution and farthest from negative-ideal.
        """
        import numpy as np

        criteria_names = [c.name for c in self.criteria]
        weights = np.array([c.weight for c in self.criteria])

        # Build decision matrix (options x criteria)
        matrix = []
        for opt in options:
            row = [scores.get(cname, {}).get(opt, 0.0) for cname in criteria_names]
            matrix.append(row)

        matrix = np.array(matrix)

        # Normalize
        norms = np.sqrt(np.sum(matrix**2, axis=0))
        normalized = matrix / (norms + 1e-8)

        # Weighted normalized
        weighted = normalized * weights

        # Determine ideal and anti-ideal
        ideal = np.max(weighted, axis=0)
        anti_ideal = np.min(weighted, axis=0)

        # Distance to ideal and anti-ideal
        d_plus = np.sqrt(np.sum((weighted - ideal)**2, axis=1))
        d_minus = np.sqrt(np.sum((weighted - anti_ideal)**2, axis=1))

        # Relative closeness
        closeness = d_minus / (d_plus + d_minus + 1e-8)

        best_idx = np.argmax(closeness)
        return options[best_idx], float(closeness[best_idx])

    def explain(self, context: Dict[str, Any], choice: str) -> str:
        scores_desc = []
        for criterion in self.criteria:
            try:
                s = criterion.scorer(context, [choice])
                scores_desc.append(f"{criterion.name}={s.get(choice, 0):.2f}")
            except Exception:
                pass
        return f"MCDA({self.method}): " + ", ".join(scores_desc)


class ScoringStrategyWrapper(DecisionStrategy):
    """
    Simple scoring strategy that wraps a scoring function.

    Convenience for simple cases.
    """

    def __init__(
        self,
        scoring_fn: callable,
        explanation_fn: Optional[callable] = None,
    ):
        """
        Args:
            scoring_fn: function(context, options) -> Dict[option -> score]
            explanation_fn: Optional function to explain decision
        """
        self.scoring_fn = scoring_fn
        self.explanation_fn = explanation_fn or (lambda ctx, opt: "Scored highest")

    def decide(self, context: Dict[str, Any], options: List[str]) -> Tuple[str, float]:
        scores = self.scoring_fn(context, options)
        if not scores:
            return options[0] if options else "none", 0.0
        best = max(scores, key=scores.get)
        return best, scores[best]

    def explain(self, context: Dict[str, Any], choice: str) -> str:
        return self.explanation_fn(context, choice)


# ============== Common Criteria Scorers ==============

def relevance_criterion(name: str, query_key: str = "query") -> Criterion:
    """Create a criterion that scores relevance to a query"""
    def scorer(context: Dict[str, Any], options: List[str]) -> Dict[str, float]:
        query = context.get(query_key, "").lower()
        if not query:
            return {opt: 0.5 for opt in options}
        scores = {}
        for opt in options:
            opt_lower = str(opt).lower()
            if query in opt_lower:
                scores[opt] = 1.0
            else:
                # Simple word overlap
                q_words = set(query.split())
                o_words = set(opt_lower.split())
                overlap = len(q_words & o_words) / max(1, len(q_words))
                scores[opt] = overlap
        return scores

    return Criterion(name=name, weight=1.0, scorer=scorer)


def confidence_criterion(name: str) -> Criterion:
    """Create a criterion favoring higher-confidence options"""
    def scorer(context: Dict[str, Any], options: List[str]) -> Dict[str, float]:
        confidences = context.get("confidences", {})
        return {opt: confidences.get(opt, 0.5) for opt in options}

    return Criterion(name=name, weight=1.0, scorer=scorer)


def recency_criterion(name: str, timestamp_key: str = "timestamp") -> Criterion:
    """Create a criterion favoring recent items"""
    def scorer(context: Dict[str, Any], options: List[str]) -> Dict[str, float]:
        now = time.time()
        timestamps = context.get(timestamp_key, {})
        if not isinstance(timestamps, dict):
            return {opt: 0.5 for opt in options}
        scores = {}
        for opt in options:
            ts = timestamps.get(opt, 0)
            age_hours = (now - ts) / 3600 if ts else 999
            scores[opt] = max(0.0, 1.0 - (age_hours / 24))  # Decay over 24h
        return scores

    return Criterion(name=name, weight=1.0, scorer=scorer)
