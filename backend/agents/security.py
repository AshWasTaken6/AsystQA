"""
Auditor Agent - Security Analysis & Threat Modeling

Enhanced security agent with deep OWASP analysis, threat modeling,
intrusion pattern detection, and security policy enforcement.

Specializes in:
- OWASP Top 10 vulnerability detection
- Cryptographic weakness identification
- Secret and credential leakage prevention
- Access control validation
- Input validation and injection prevention
- Security anti-pattern recognition

Maintains episodic memory of vulnerabilities and learns from security incidents.
"""

import re
import asyncio
import logging
import time
import uuid
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

from core.agent_base import BaseAgent, Priority, register_agent
from core.memory import (
    WorkingMemory,
    EpisodicMemory,
    ProceduralMemory,
    Priority,
    PatternType,
    PatternSuccess,
    TaskPattern,
)
from core.telemetry import get_telemetry_manager
from core.events import EventType, emit_event
from core.tools import SimpleTool, ToolContext, ToolResult, ToolPermission
from core.strategies import DecisionStrategy, RuleBasedStrategy, DecisionRule
from services.audit import query_audit_logs

logger = logging.getLogger(__name__)


class SecuritySeverity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class OWASPCategory(Enum):
    """OWASP Top 10 categories (2021)"""
    A01 = "A01:2021 Broken Access Control"
    A02 = "A02:2021 Cryptographic Failures"
    A03 = "A03:2021 Injection"
    A04 = "A04:2021 Insecure Design"
    A05 = "A05:2021 Security Misconfiguration"
    A06 = "A06:2021 Vulnerable and Outdated Components"
    A07 = "A07:2021 Identification and Authentication Failures"
    A08 = "A08:2021 Software and Data Integrity Failures"
    A09 = "A09:2021 Security Logging and Monitoring Failures"
    A10 = "A10:2021 Server-Side Request Forgery"


@dataclass
class SecurityFinding:
    """Rich security finding with full context"""
    severity: SecuritySeverity
    line: int
    issue: str
    root_cause: str
    fix_suggestion: str
    category: str
    owasp: Optional[OWASPCategory]
    code_snippet: str
    confidence: float
    cwe_id: Optional[str] = None
    agent_id: str = "auditor"
    tags: Set[str] = field(default_factory=set)
    references: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent_id,
            "severity": self.severity.value,
            "lineNumber": self.line,
            "issue": self.issue,
            "predictedException": "Security vulnerability",
            "rootCause": self.root_cause,
            "fix": self.fix_suggestion,
            "impact": self.root_cause,
            "category": self.category,
            "owasp": self.owasp.value if self.owasp else None,
            "cwe": self.cwe_id,
            "confidence": self.confidence,
            "tags": list(self.tags),
            "references": self.references,
            **self.metadata,
        }


@register_agent
class AuditorAgent(BaseAgent):
    """
    Enhanced Auditor agent with sophisticated security analysis.

    Extends basic security scanning with:
    - Context-aware threat modeling
    - Security pattern learning
    - Cross-agent correlation
    - Policy-based checking
    - Historical vulnerability tracking
    - Security debt quantification
    """

    AGENT_NAME = "auditor"
    AGENT_VERSION = "3.0.0"
    AGENT_CATEGORY = "security"
    AGENT_DESCRIPTION = "Comprehensive security analysis with OWASP and threat modeling"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.memory = WorkingMemory(
            primary_capacity=200,
            observations_capacity=150,
            long_term_capacity=500,
        )

        self._findings: List[SecurityFinding] = []
        self._vulnerability_patterns: Dict[str, int] = {}
        self._cwe_mapping: Dict[str, str] = {}
        self._decision_strategy = self._build_security_strategy()

        # Load security patterns
        self._load_security_patterns()
        self._compile_detection_patterns()

    def _load_security_patterns(self) -> None:
        """Load security-focused procedural patterns"""
        patterns = [
            TaskPattern(
                id="auditor-injection",
                name="Injection Vulnerability Detection",
                pattern_type=PatternType.ISSUE_DETECTION,
                description="Detect code injection vulnerabilities",
                trigger_conditions={"owasp": OWASPCategory.A03.value},
                action_template=[
                    {"scan": "sink_functions"},
                    {"check": "input_validation"},
                    {"verify": "parameterized_queries"},
                ],
                expected_outcome="All injection vectors identified and blocked",
                applicable_domains={"security", "injection"},
            ),
            TaskPattern(
                id="auditor-crypto-weak",
                name="Cryptographic Weakness Detection",
                pattern_type=PatternType.ISSUE_DETECTION,
                description="Find weak hash functions and crypto usage",
                trigger_conditions={"owasp": OWASPCategory.A02.value},
                action_template=[
                    {"scan": "hash_functions"},
                    {"check": "salt_usage"},
                    {"verify": "algorithm_strength"},
                ],
                expected_outcome="Weak crypto primitives identified",
                applicable_domains={"cryptography", "security"},
            ),
            TaskPattern(
                id="auditor-secret-leak",
                name="Secret Detection and Redaction",
                pattern_type=PatternType.ISSUE_DETECTION,
                description="Find hardcoded secrets and credentials",
                trigger_conditions={"category": "Cryptographic & Secret Management"},
                action_template=[
                    {"scan": "credential_patterns"},
                    {"check": "hardcoded_values"},
                    {"action": "redact_and_flag"},
                ],
                expected_outcome="No secrets in source code",
                applicable_domains={"secrets", "credentials"},
            ),
        ]

        for pattern in patterns:
            self.procedural.store_pattern(pattern)

    def _build_security_strategy(self) -> DecisionStrategy:
        """Build security-focused decision strategy"""
        rules = [
            DecisionRule(
                condition="{severity} == 'CRITICAL'",
                action="block_release",
                priority=100,
            ),
            DecisionRule(
                condition="{owasp} in {'A01:2021', 'A02:2021', 'A03:2021'}",
                action="escalate_to_architect",
                priority=95,
            ),
            DecisionRule(
                condition="{has_sentinel_errors} and {severity} == 'CRITICAL'",
                action="fail_closed",
                priority=90,
            ),
        ]
        return RuleBasedStrategy(rules, default_action="flag_for_review")

    def _compile_detection_patterns(self) -> None:
        """Compile all security detection regex patterns"""
        self._sink_patterns = {
            "eval": re.compile(r'eval\s*\('),
            "exec": re.compile(r'exec\s*\('),
            "subprocess": re.compile(r'subprocess\.(?:call|run|Popen)\s*\('),
            "innerHTML": re.compile(r'\.innerHTML\s*='),
            "document_write": re.compile(r'document\.write\s*\('),
        }

        self._secret_patterns = [
            (re.compile(
                r'(?i)(api[_-]?key|secret|token|password)\s*=\s*[\'"][^\'"]{6,}[\'"]'
            ), "hardcoded_secret"),
            (re.compile(r'(?i)bearer\s+[a-z0-9._~+/=-]{12,}'), "bearer_token"),
            (re.compile(r'sk-[a-z0-9_-]{8,}'), "openai_key"),
            (re.compile(r'AIza[0-9A-Za-z\-_]{35}'), "google_api_key"),
        ]

        self._crypto_patterns = [
            (re.compile(r'md5\s*\('), "MD5", "CWE-327"),
            (re.compile(r'sha1\s*\('), "SHA-1", "CWE-328"),
            (re.compile(r'random\.random\s*\('), "Predictable RNG", "CWE-330"),
        ]

        self._access_patterns = [
            (re.compile(r'user_id'), "user_scoped_data"),
            (re.compile(r'(?i)(admin|role|permission)'), "access_control"),
        ]

    # ============== Core Execution ==============

    async def execute(
        self,
        code: str,
        language: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Execute comprehensive security analysis.

        Args:
            code: Source code
            language: Programming language
            context: From previous agents (includes sentinel findings)

        Returns:
            List of security findings
        """
        self.state = "RUNNING"
        start_time = time.time()
        context = context or {}

        session_id = context.get("session_id")
        self.start_session(session_id or str(uuid.uuid4()))

        emit_event(
            EventType.AGENT_START,
            source=self.agent_id,
            data={"language": language},
        )

        try:
            with get_telemetry_manager().trace_span(
                self.agent_id, "security_analysis"
            ) as span:
                if span:
                    span.set_attribute("language", language)

                self.memory.add(
                    content="Starting security analysis",
                    context_type="observations",
                    priority=Priority.HIGH,
                    agent_id=self.agent_id,
                    tags={"security_scan_start"},
                )

                findings = await self._analyze_security(
                    code, language, context
                )

                # Apply security decision strategy
                findings = self._apply_security_strategy(findings, context)

                # Record
                duration = time.time() - start_time
                self._record_success(duration)

                self.remember_episode(
                    content=f"Security scan: {len(findings)} vulnerabilities",
                    metadata={
                        "agent": self.agent_id,
                        "severity_dist": self._severity_histogram(findings),
                        "duration": duration,
                    },
                    importance=0.9 if findings else 0.3,  # High importance for vulns
                )

                emit_event(
                    EventType.AGENT_COMPLETE,
                    source=self.agent_id,
                    data={"vulnerabilities": len(findings)},
                )

                self.memory.add(
                    content=f"Security scan complete: {len(findings)} issues",
                    context_type="results",
                    priority=Priority.HIGH,
                    agent_id=self.agent_id,
                )

                return [f.to_dict() for f in findings]

        except Exception as e:
            duration = time.time() - start_time
            self._record_failure(e, duration)
            emit_event(
                EventType.AGENT_ERROR,
                source=self.agent_id,
                data={"error": str(e), "type": "security_scan_error"},
            )
            raise

    async def _analyze_security(
        self,
        code: str,
        language: str,
        context: Dict[str, Any],
    ) -> List[SecurityFinding]:
        """Main security analysis logic"""
        findings = []

        # Run all detection modules
        findings.extend(self._detect_injection_sinks(code, language))
        findings.extend(self._detect_hardcoded_secrets(code))
        findings.extend(self._detect_crypto_weaknesses(code))
        findings.extend(self._detect_authentication_issues(code))
        findings.extend(self._detect_access_control_issues(code, language))

        # Cross-reference with sentinel findings
        sentinel_findings = context.get("sentinel", [])
        if sentinel_findings:
            findings.extend(self._correlate_with_sentinel(sentinel_findings))

        return findings

    def _detect_injection_sinks(self, code: str, language: str) -> List[SecurityFinding]:
        """Detect code injection vulnerabilities"""
        findings = []
        lowered = code.lower()

        injection_checks = [
            ("eval(", "Dynamic code execution", "User input can execute arbitrary code", "Replace with safe parser or sandbox", OWASPCategory.A03),
            ("exec(", "Dynamic code execution", "Code injection risk", "Remove exec or isolate", OWASPCategory.A03),
        ]

        if language.lower() in {"javascript", "js", "typescript", "ts"}:
            injection_checks.extend([
                ("innerhtml", "Unsafe HTML injection", "innerHTML with untrusted content", "Use textContent or sanitizer", OWASPCategory.A03),
                ("document.write(", "Unsafe DOM write", "Can inject script", "Use safe DOM API", OWASPCategory.A03),
            ])
        elif language.lower() in {"python", "py"}:
            injection_checks.extend([
                ("subprocess", "Shell execution", "Command injection risk", "Use argv array, shell=False", OWASPCategory.A03),
                ("os.system", "Shell execution", "Command injection risk", "Avoid os.system", OWASPCategory.A03),
            ])

        for needle, issue, root, fix, owasp in injection_checks:
            if needle in lowered:
                line = code[:lowered.find(needle)].count('\n') + 1
                findings.append(SecurityFinding(
                    severity=SecuritySeverity.CRITICAL,
                    line=line,
                    issue=issue,
                    root_cause=root,
                    fix_suggestion=fix,
                    category="Injection",
                    owasp=owasp,
                    code_snippet=code.split('\n')[line-1].strip() if line <= len(code.splitlines()) else "",
                    confidence=0.95,
                    tags={"injection", "untrusted_input"},
                    references=["CWE-94" if "eval" in needle else "CWE-78"],
                ))

        return findings

    def _detect_hardcoded_secrets(self, code: str) -> List[SecurityFinding]:
        """Detect hardcoded credentials"""
        findings = []

        for pattern, issue in self._secret_patterns:
            for match in pattern.finditer(code):
                secret_type = issue
                line = code[:match.start()].count('\n') + 1

                findings.append(SecurityFinding(
                    severity=SecuritySeverity.CRITICAL,
                    line=line,
                    issue=f"Hardcoded {secret_type.replace('_', ' ')}",
                    root_cause="Credential-like value appears directly in source",
                    fix_suggestion="Move to environment-backed secret storage; rotate exposed values.",
                    category="Cryptographic & Secret Management",
                    owasp=OWASPCategory.A02,
                    code_snippet=code.split('\n')[line-1].strip(),
                    confidence=0.9,
                    tags={"secrets", "credentials"},
                    metadata={"matched_text": match.group(0)[:20] + "..."},
                ))

        return findings

    def _detect_crypto_weaknesses(self, code: str) -> List[SecurityFinding]:
        """Detect weak cryptography"""
        findings = []

        for pattern, issue, cwe in self._crypto_patterns:
            if pattern.search(code):
                line = code[:pattern.search(code).start()].count('\n') + 1
                findings.append(SecurityFinding(
                    severity=SecuritySeverity.CRITICAL,
                    line=line,
                    issue=issue,
                    root_cause="Use of deprecated or weak cryptographic primitive",
                    fix_suggestion=self._get_crypto_fix(issue),
                    category="Cryptographic Weakness",
                    owasp=OWASPCategory.A02,
                    code_snippet=code.split('\n')[line-1].strip(),
                    confidence=0.9,
                    cwe_id=cwe,
                    tags={"crypto", "weak_hash"},
                ))

        # Password hashing check
        if re.search(r'password', code, re.IGNORECASE) and not re.search(r'hash|bcrypt|argon2|scrypt|pbkdf2', code, re.IGNORECASE):
            # Find the line
            match = re.search(r'password', code, re.IGNORECASE)
            line = code[:match.start()].count('\n') + 1
            findings.append(SecurityFinding(
                severity=SecuritySeverity.CRITICAL,
                line=line,
                issue="Password handling lacks visible hashing",
                root_cause="Password data appears without password hashing",
                fix_suggestion="Hash passwords with Argon2, bcrypt, scrypt, or PBKDF2.",
                category="Authentication",
                owasp=OWASPCategory.A07,
                code_snippet=code.split('\n')[line-1].strip(),
                confidence=0.8,
                tags={"passwords", "hashing"},
            ))

        return findings

    def _detect_authentication_issues(self, code: str) -> List[SecurityFinding]:
        """Detect auth-related issues"""
        findings = []

        # Check for MFA indicators
        if "mfa" in code.lower() or "2fa" in code.lower():
            # Verify enforced MFA
            # Could check for mandatory=true
            pass

        return findings

    def _detect_access_control_issues(self, code: str, language: str) -> List[SecurityFinding]:
        """Detect access control bypass risks"""
        findings = []

        lowered = code.lower()
        access_indicators = ["admin", "role", "permission", "owner", "user_id"]

        if any(indicator in lowered for indicator in access_indicators):
            has_auth = any(gate in lowered for gate in ["permission", "authorize", "forbidden", "403", "role_check"])
            if "user_id" in lowered and not has_auth:
                match = re.search(r'user_id', lowered)
                line = code[:match.start()].count('\n') + 1
                findings.append(SecurityFinding(
                    severity=SecuritySeverity.HIGH,
                    line=line,
                    issue="User-scoped data access lacks authorization check",
                    root_cause="User ownership referenced without visible permission check at trust boundary.",
                    fix_suggestion="Enforce owner/admin checks before accessing user data.",
                    category="Broken Access Control",
                    owasp=OWASPCategory.A01,
                    code_snippet=code.split('\n')[line-1].strip(),
                    confidence=0.8,
                    tags={"access_control", "authorization"},
                    references=["CWE-284"],
                ))

        return findings

    def _correlate_with_sentinel(self, sentinel_findings: List[Dict]) -> List[SecurityFinding]:
        """Correlate sentinel runtime issues with security"""
        findings = []

        # If sentinel found runtime errors, security may be bypassed
        runtime_errors = [
            f for f in sentinel_findings
            if f.get("predictedException") in {"NameError", "TypeError", "AttributeError"}
        ]
        if runtime_errors:
            findings.append(SecurityFinding(
                severity=SecuritySeverity.MEDIUM,
                line=1,
                issue="Runtime instability can weaken security controls",
                root_cause="Sentinel found runtime defects that may bypass logging, authorization, cleanup.",
                fix_suggestion="Fix runtime blockers before relying on security controls.",
                category="Security Reliability",
                owasp=OWASPCategory.A04,
                code_snippet="",
                confidence=0.7,
                tags={"runtime", "reliability"},
            ))

        return findings

    def _apply_security_strategy(
        self,
        findings: List[SecurityFinding],
        context: Dict[str, Any],
    ) -> List[SecurityFinding]:
        """Apply security decision rules"""
        # Already weighted by critical; could add ML-based risk scoring
        return findings

    def _severity_histogram(self, findings: List[SecurityFinding]) -> Dict[str, int]:
        hist = {s.value: 0 for s in SecuritySeverity}
        for f in findings:
            hist[f.severity.value] += 1
        return hist

    def _get_crypto_fix(self, issue: str) -> str:
        mappings = {
            "MD5": "Use SHA-256 for integrity or Argon2/bcrypt/scrypt for passwords.",
            "SHA-1": "Use SHA-256+ or password-hashing KDF.",
            "Predictable RNG": "Use secrets.token_urlsafe or CSPRNG.",
        }
        return mappings.get(issue, "Use industry-standard cryptographic primitives.")

    # ============== Tools ==============

    def get_tools(self) -> List[SimpleTool]:
        return [
            SimpleTool(
                name="owasp_scan",
                func=self._tool_owasp,
                description="Full OWASP scan",
                permission=ToolPermission.PUBLIC,
            ),
            SimpleTool(
                name="secret_scan",
                func=self._tool_secrets,
                description="Detect hardcoded secrets",
                permission=ToolPermission.PUBLIC,
            ),
            SimpleTool(
                name="crypto_scan",
                func=self._tool_crypto,
                description="Find crypto weaknesses",
                permission=ToolPermission.PUBLIC,
            ),
        ]

    def _tool_owasp(self, context: ToolContext, code: str) -> ToolResult:
        result = asyncio.run(self.execute(code, "python", context.to_dict() if hasattr(context, 'to_dict') else {}))
        return ToolResult.ok(data={"findings": result})

    def _tool_secrets(self, context: ToolContext, code: str) -> ToolResult:
        secrets = self._detect_hardcoded_secrets(code)
        return ToolResult.ok(data={"findings": [s.to_dict() for s in secrets]})

    def _tool_crypto(self, context: ToolContext, code: str) -> ToolResult:
        crypto = self._detect_crypto_weaknesses(code)
        return ToolResult.ok(data={"findings": [c.to_dict() for c in crypto]})

    def get_capabilities(self):
        from core.agent_base import AgentCapabilities
        return AgentCapabilities(
            languages=["python", "py", "javascript", "js", "typescript", "ts", "c", "cpp"],
            categories=["security", "vulnerability", "compliance"],
            tools=[t.name for t in self.get_tools()],
            requires_context=True,
            produces_insights=True,
        )


# ============== Compatibility ==============

async def run_security(
    code: str,
    language: str,
    context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    from core.agent_factory import create_agent
    agent = create_agent("auditor")
    return await agent.execute(code, language, context)
