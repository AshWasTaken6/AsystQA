"""
Reporter Agent - Advanced Analytics and Report Generation

Enhanced reporting agent that aggregates findings, calculates scores,
generates insights, and produces comprehensive reports.

Features:
- Multi-dimensional scoring algorithms
- Risk assessment modeling
- Trend analysis over time
- Pattern recognition
- Actionable recommendation engine
- Report customization and formatting
- Historical comparison
- Benchmarking
"""

import asyncio
import logging
import time
import uuid
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict
from core.agent_base import BaseAgent, Priority, register_agent
from core.memory import (
    WorkingMemory,
    EpisodicMemory,
    ProceduralMemory,
    TaskPattern,
)
from core.telemetry import get_telemetry_manager
from core.events import EventType, emit_event
from core.tools import SimpleTool, ToolContext, ToolResult, ToolPermission
from core.strategies import ScoringStrategy, Criterion
from schemas.response import Report as ReportSchema

logger = logging.getLogger(__name__)


# severity_weights = {
#     "CRITICAL": 30,
#     "HIGH": 20,
#     "MEDIUM": 10,
#     "LOW": 5,
#     "INFO": 1,
# }

class ScoreAlgorithm(Enum):
    """Scoring algorithms"""
    LINEAR = "linear"              # Simple weighted sum
    EXPONENTIAL = "exponential"    # Critical issues have outsized impact
    CATEGORY_BALANCED = "balanced" # Balanced across categories
    CUMULATIVE = "cumulative"      # Accumulated impact


@dataclass
class ScoreWeights:
    """Weight configuration for scoring"""
    critical: float = 30.0
    high: float = 20.0
    medium: float = 10.0
    low: float = 5.0
    info: float = 1.0
    algorithm: ScoreAlgorithm = ScoreAlgorithm.LINEAR

    def calculate(self, findings: List[Dict[str, Any]]) -> int:
        """Calculate overall score from findings"""
        if not findings:
            return 95

        # Base deduction per severity
        severity_counts = defaultdict(int)
        for f in findings:
            sev = f.get("severity", "LOW").upper()
            severity_counts[sev] += 1

        # Weighted deduction
        if self.algorithm == ScoreAlgorithm.EXPONENTIAL:
            # Exponential decay on critical issues
            score = 100.0
            for sev, count in severity_counts.items():
                weight = getattr(self, sev.lower(), 5)
                deduction = weight * (1.5 ** count - 1) / 1.5
                score -= deduction
        elif self.algorithm == ScoreAlgorithm.CUMULATIVE:
            # Each issue reduces score more as count increases
            total_issues = len(findings)
            score = max(0, 100 - (total_issues * 8))
            # Apply severity caps
            cap = min([f.get("scoreCap", 100) for f in findings], default=100)
            score = min(score, cap)
        else:  # LINEAR
            total_deduction = sum(
                severity_counts.get(sev, 0) * getattr(self, sev.lower(), 5)
                for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
            )
            score = max(0, 100 - total_deduction)

        # Apply min caps from findings
        caps = [f.get("scoreCap") for f in findings if isinstance(f.get("scoreCap"), int)]
        if caps:
            score = min(score, min(caps))

        return int(round(score))

    def category_weights(self) -> Dict[str, float]:
        """Weight per finding category"""
        return {
            "Security": self.critical * 1.2,
            "Variable & Scope Trace": self.high,
            "Data Type & Arithmetic Validation": self.high,
            "Logic & Boundary Integrity": self.medium,
            "SOLID & Clean Code": self.medium,
            "Robustness & Error Handling": self.high,
            "Formal Review": self.medium,
            "Cryptographic & Secret Management": self.critical,
        }


@dataclass
class Insight:
    """Insight generated from analysis"""
    type: str
    description: str
    confidence: float
    related_findings: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "description": self.description,
            "confidence": self.confidence,
            "related": self.related_findings,
            "recommendations": self.recommendations,
            **self.metadata,
        }


@dataclass
class Benchmark:
    """Benchmark comparison"""
    name: str
    baseline_score: int
    current_score: int
    threshold: int
    trend: str  # improving, declining, stable


@register_agent
class ReporterAgent(BaseAgent):
    """
    Enhanced Reporter agent for comprehensive analytics.

    Beyond simple aggregation:
    - Multi-algorithm scoring
    - Risk prediction
    - Trend analysis
    - Pattern recognition
    - Priority recommendation
    - Report customization
    """

    AGENT_NAME = "reporter"
    AGENT_VERSION = "3.0.0"
    AGENT_CATEGORY = "reporting"
    AGENT_DESCRIPTION = "Advanced analytics, risk assessment, and report generation"

    def __init__(
        self,
        weights: Optional[ScoreWeights] = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.memory = WorkingMemory(
            primary_capacity=200,
            observations_capacity=150,
            long_term_capacity=500,
        )

        self.weights = weights or ScoreWeights()
        self._insights_cache: Dict[str, Insight] = {}
        self._benchmarks: Dict[str, Benchmark] = {}
        self._historical_scores: List[Tuple[float, int]] = []  # (timestamp, score)

        # Load patterns
        self._load_reporting_patterns()

    def _load_reporting_patterns(self) -> None:
        """Load analytical patterns"""
        patterns = [
            TaskPattern(
                id="report-trend-improving",
                name="Improving Trend Detection",
                pattern_type=PatternType.ISSUE_DETECTION,
                description="Detect when code quality is improving over time",
                trigger_conditions={"analysis": "trend"},
                action_template=[
                    {"compare": "current_scores", "with": "historical"},
                    {"direction": "improving"},
                ],
                expected_outcome="Track quality improvement",
                applicable_domains={"analytics", "trends"},
            ),
        ]
        for p in patterns:
            self.procedural.store_pattern(p)

    # ============== Core Execution ==============

    async def execute(
        self,
        aggregated: Dict[str, List[Any]],
        code: Optional[str] = None,
        language: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate comprehensive report.

        Args:
            aggregated: Dict with 'reviewer', 'security', 'planner', 'tester' lists
            code: Original code (for analysis)
            language: Programming language
            metadata: Additional metadata

        Returns:
            Full Report schema with enriched data
        """
        self.state = "RUNNING"
        start_time = time.time()

        session_id = metadata.get("session_id") if metadata else None
        self.start_session(session_id or str(uuid.uuid4()))

        emit_event(
            EventType.AGENT_START,
            source=self.agent_id,
            data={"sources": list(aggregated.keys())},
        )

        try:
            with get_telemetry_manager().trace_span(
                self.agent_id, "report_generation"
            ) as span:
                # Extract findings
                reviewer = aggregated.get("reviewer", [])
                security = aggregated.get("security", [])
                planner = aggregated.get("planner", [])
                tester = aggregated.get("tester", [])

                # Compute score
                score = self.weights.calculate(reviewer + security)

                # Classification
                classification = self._classify_score(score)

                # Risk assessment
                risk = self._assess_risk(reviewer, security, score)

                # Build summary
                summary = self._build_summary(
                    classification,
                    len(planner),
                    len(reviewer),
                    len(security),
                    len(tester),
                )

                # Build enriched issues with full metadata
                issues = self._enrich_issues(reviewer, security, aggregated)

                # Generate tests suggestions
                tests = self._format_tests(tester)

                # Generate insights
                insights = self._generate_insights(
                    code, language, reviewer, security, score
                )

                # Trend analysis
                trend_data = self._analyze_trend(score)

                # Recommendations
                recommendations = self._generate_recommendations(
                    issues, code, language, score
                )

                # Build report
                report = ReportSchema(
                    score=score,
                    summary=summary,
                    risk=risk,
                    issueCount=len(issues),
                    issues=issues,
                    tests=tests,
                )

                duration = time.time() - start_time
                self._record_success(duration)

                # Store in episodic memory
                self.remember_episode(
                    content=f"Report: score={score}, risk={risk}, issues={len(issues)}",
                    metadata={
                        "agent": self.agent_id,
                        "score": score,
                        "risk": risk,
                        "issues": len(issues),
                        "language": language,
                        "duration": duration,
                    },
                    importance=0.8,
                )

                emit_event(
                    EventType.AGENT_COMPLETE,
                    source=self.agent_id,
                    data={"score": score, "issues": len(issues), "risk": risk},
                )

                # Return full report + extras
                report_dict = report.model_dump()
                report_dict.update({
                    "insights": insights,
                    "recommendations": recommendations,
                    "trend": trend_data,
                    "processing_time": duration,
                    "score_breakdown": self._score_breakdown(reviewer, security),
                })

                return report_dict

        except Exception as e:
            duration = time.time() - start_time
            self._record_failure(e, duration)
            emit_event(EventType.AGENT_ERROR, source=self.agent_id, data={"error": str(e)})
            raise

    # ============== Analytics Methods ==============

    def _classify_score(self, score: int) -> str:
        """Classify code quality based on score"""
        if score <= 30:
            return "Non-Functional"
        if score <= 60:
            return "Flawed"
        if score <= 85:
            return "Functional"
        return "Production Ready"

    def _assess_risk(self, reviewer: List, security: List, score: int) -> str:
        """Assess overall risk level"""
        severities = {f.get("severity", "").lower() for f in reviewer + security}

        if "critical" in severities or "high" in severities:
            if any("security" in f.get("category", "").lower() for f in security):
                return "Critical - Security vulnerabilities present"
            return "High - Critical issues found"
        if "warning" in severities or "medium" in severities:
            return "Medium - Non-critical issues present"
        if score >= 80:
            return "Low - Code appears production-ready"
        return "Medium-Low - Minor improvements needed"

    def _build_summary(
        self,
        classification: str,
        planner_count: int,
        reviewer_count: int,
        security_count: int,
        tester_count: int,
    ) -> str:
        """Build human-readable summary"""
        parts = [
            f"Classification: {classification}.",
            f"Architect generated {planner_count} planning step(s).",
            f"Sentinel/Critic found {reviewer_count} execution and formal-review issue(s).",
            f"Auditor found {security_count} security issue(s).",
            f"Chaos Engineer suggested {tester_count} adversarial test(s).",
        ]
        return " ".join(parts)

    def _enrich_issues(
        self,
        reviewer: List[Dict],
        security: List[Dict],
        all_aggregated: Dict[str, List],
    ) -> List[Dict]:
        """Enrich issues with additional metadata"""
        enriched = []

        for item in reviewer + security:
            # Ensure standard fields
            issue = {
                "severity": item.get("severity", "LOW"),
                "category": item.get("category", "General"),
                "title": item.get("issue", "Issue detected"),
                "text": item.get("fix", item.get("impact", "Review required")),
                "source": item.get("agent", "unknown"),
            }

            # Optional fields
            for field in ["lineNumber", "predictedException", "rootCause", "owasp", "recovery"]:
                if field in item:
                    issue[field] = item[field]

            # Add risk score
            severity_weights = {"CRITICAL": 10, "HIGH": 7, "MEDIUM": 4, "LOW": 2, "INFO": 1}
            issue["risk_score"] = severity_weights.get(issue["severity"].upper(), 2)

            enriched.append(issue)

        # Sort by severity descending, then by risk score
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        enriched.sort(
            key=lambda x: (severity_order.get(x["severity"].upper(), 4), -x.get("risk_score", 0))
        )
        return enriched

    def _format_tests(self, tester: List[str]) -> List[Dict[str, str]]:
        """Format test suggestions"""
        return [
            {"title": suggestion, "type": "Suggestion"}
            for suggestion in tester
        ]

    def _generate_insights(
        self,
        code: Optional[str],
        language: Optional[str],
        reviewer: List,
        security: List,
        score: int,
    ) -> Dict[str, Any]:
        """Generate deeper insights"""
        insights = {
            "summary": self._insight_summary(reviewer, security, score),
            "hotspots": self._identify_hotspots(reviewer),
            "security_profile": self._security_profile(security),
            "quality_trend": self._quality_trend(),
            "top_risk_factors": self._top_risk_factors(reviewer + security),
        }

        # Add language-specific guesses
        if language:
            insights["language"] = language
            insights["language_patterns"] = self._language_patterns(language, reviewer)

        return insights

    def _insight_summary(self, reviewer: List, security: List, score: int) -> str:
        total_issues = len(reviewer) + len(security)

        if total_issues == 0:
            return "No issues detected - code appears robust."
        elif total_issues <= 3:
            return f"Few issues ({total_issues}) - generally good quality."
        elif total_issues <= 8:
            return f"Moderate issues ({total_issues}) - improvements recommended."
        else:
            return f"Many issues ({total_issues}) - significant refactoring needed."

    def _identify_hotspots(self, reviewer: List) -> List[Dict[str, Any]]:
        """Identify code areas needing attention"""
        line_counts = defaultdict(int)
        for f in reviewer:
            line = f.get("lineNumber")
            if line:
                # Bucket by region
                region = (line // 100) * 100
                line_counts[region] += 1

        hotspots = []
        for region, count in sorted(line_counts.items(), key=lambda x: -x[1])[:3]:
            hotspots.append({
                "line_region": f"{region}-{region+99}",
                "issue_count": count,
                "suggestion": "Consider refactoring this region"
            })
        return hotspots

    def _security_profile(self, security: List) -> Dict[str, Any]:
        """Generate security risk profile"""
        owasp_counts = defaultdict(int)
        severity_counts = defaultdict(int)

        for f in security:
            owasp = f.get("owasp", "Other")
            owasp_counts[owasp] += 1
            severity_counts[f.get("severity", "LOW")] += 1

        return {
            "by_owasp": dict(owasp_counts),
            "by_severity": dict(severity_counts),
            "critical_count": severity_counts.get("CRITICAL", 0),
            "overall_risk": "HIGH" if severity_counts.get("CRITICAL", 0) > 0 else "MEDIUM",
        }

    def _quality_trend(self) -> Dict[str, Any]:
        """Analyze quality trend over recent scans"""
        if len(self._historical_scores) < 2:
            return {"trend": "insufficient_data", "direction": "unknown"}

        # Compare recent average to older average
        recent = self._historical_scores[-5:] if len(self._historical_scores) >= 5 else self._historical_scores[-2:]
        older = self._historical_scores[-10:-5] if len(self._historical_scores) >= 10 else self._historical_scores[:-5]

        if not older:
            return {"trend": "insufficient_data", "direction": "unknown"}

        recent_avg = sum(s for s, _ in recent) / len(recent)
        older_avg = sum(s for s, _ in older) / len(older)

        if recent_avg > older_avg + 5:
            direction = "improving"
        elif recent_avg < older_avg - 5:
            direction = "declining"
        else:
            direction = "stable"

        return {
            "trend": "calculated",
            "direction": direction,
            "recent_avg": round(recent_avg, 1),
            "previous_avg": round(older_avg, 1),
            "change": round(recent_avg - older_avg, 1),
        }

    def _top_risk_factors(self, findings: List[Dict]) -> List[str]:
        """Identify top risk factors requiring immediate attention"""
        risks = []
        critical_security = [
            f for f in findings
            if f.get("severity") == "CRITICAL" and "security" in f.get("category", "").lower()
        ]
        if critical_security:
            risks.append("Critical security vulnerabilities require immediate attention")

        runtime_defects = [
            f for f in findings
            if f.get("predictedException") in {"NameError", "UnboundLocalError", "ZeroDivisionError"}
        ]
        if runtime_defects:
            risks.append("Runtime defects risk production failures")

        return risks

    def _language_patterns(self, language: str, reviewer: List) -> List[str]:
        """Identify language anti-patterns"""
        patterns = []
        lang_lower = language.lower()

        if lang_lower in {"python", "py"}:
            evals = [f for f in reviewer if "eval" in f.get("issue", "").lower()]
            if evals:
                patterns.append("Python: avoid eval() - use ast.literal_eval or parser")
            # More Python patterns

        elif lang_lower in {"javascript", "js"}:
            globals = [f for f in reviewer if "global" in f.get("issue", "").lower()]
            if globals:
                patterns.append("JS: avoid polluting global namespace")

        return patterns

    def _score_breakdown(self, reviewer: List, security: List) -> Dict[str, Any]:
        """Break down score by category"""
        breakdown = {}

        # Count by severity
        for field in ["reviewer", "security"]:
            items = reviewer if field == "reviewer" else security
            for f in items:
                sev = f.get("severity", "LOW").upper()
                breakdown[field + "_" + sev.lower()] = breakdown.get(field + "_" + sev.lower(), 0) + 1

        return breakdown

    def _generate_recommendations(
        self,
        issues: List[Dict],
        code: Optional[str],
        language: Optional[str],
        score: int,
    ) -> List[str]:
        """Generate prioritized recommendations"""
        recommendations = []

        # Direct from security
        security_issues = [i for i in issues if "Security" in i.get("category", "")]
        if security_issues:
            recommendations.append("URGENT: Address security vulnerabilities before deployment")

        # Based on common issues
        category_counts = defaultdict(int)
        for issue in issues:
            category_counts[issue.get("category", "")] += 1

        for category, count in sorted(category_counts.items(), key=lambda x: -x[1])[:3]:
            if count >= 3:
                recommendations.append(
                    f"Consider systematic refactoring of {category} ({count} issues found)"
                )

        if score < 60:
            recommendations.append("Consider additional QA cycle before release")

        return recommendations[:5]

    # ============== Tools ==============

    def get_tools(self) -> List[SimpleTool]:
        return [
            SimpleTool(
                name="extract_metrics",
                func=self._tool_extract_metrics,
                description="Extract quality metrics from report",
                permission=ToolPermission.PUBLIC,
            ),
            SimpleTool(
                name="compare_versions",
                func=self._tool_compare_versions,
                description="Compare report with baseline",
                permission=ToolPermission.INTERNAL,
            ),
        ]

    def _tool_extract_metrics(self, context: ToolContext, report: Dict) -> ToolResult:
        metrics = {
            "score": report.get("score"),
            "risk": report.get("risk"),
            "issue_count": report.get("issueCount"),
        }
        return ToolResult.ok(data={"metrics": metrics})

    def _tool_compare_versions(self, context: ToolContext, baseline: Dict, current: Dict) -> ToolResult:
        delta = current.get("score", 0) - baseline.get("score", 0)
        return ToolResult.ok(data={
            "score_delta": delta,
            "improved": delta > 0,
        })

    def get_capabilities(self):
        from core.agent_base import AgentCapabilities
        return AgentCapabilities(
            languages=["any"],
            categories=["reporting", "analytics", "metrics"],
            tools=[t.name for t in self.get_tools()],
            requires_context=False,
            produces_insights=True,
        )

    # ============== Historical Tracking ==============

    def record_score(self, score: int) -> None:
        """Record score for trend analysis"""
        self._historical_scores.append((time.time(), score))
        # Keep last 100
        if len(self._historical_scores) > 100:
            self._historical_scores = self._historical_scores[-100:]


# ============== Compatibility ==============

def run_reporter(aggregated: Dict[str, List[Any]]) -> Dict[str, Any]:
    """Compatibility wrapper"""
    from core.agent_factory import create_agent
    agent = create_agent("reporter")
    # Run synchronously via asyncio
    return asyncio.run(agent.execute(aggregated))
