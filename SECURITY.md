# AsystQA Security Architecture

## Overview

AsystQA implements a comprehensive **Zero Trust** security model that assumes no implicit trust within the network. Every request, user, and service is authenticated, authorized, and encrypted.

## Security Layers

### Layer 1: Identity & Access Management (IAM)

#### Authentication
- **JWT-based authentication** with RS256 signatures
- Short-lived access tokens (15 minutes)
- Refresh tokens (7 days) with rotation
- Session-based with IP and User-Agent tracking
- Automatic session expiration (24h inactivity)

#### Multi-Factor Authentication (MFA)
- **TOTP** support (Google Authenticator, Authy)
- **WebAuthn/FIDO2** hardware security keys (YubiKey)
- **Biometric** via platform authenticators (Windows Hello, Touch ID)
- MFA required for admin operations (configurable)
- Backup codes for account recovery

#### Authorization (RBAC)
Four-tier role system with least privilege:
| Role | Permissions |
|------|-------------|
| `viewer` | Read code analysis, view history |
| `analyst` | Submit code, delete own history |
| `admin` | Full system access, user management |
| `security_officer` | Audit read-only, monitoring |

**Permission model granular to action + resource:**
- `code:analyze`
- `history:read`
- `history:delete_all`
- `config:read/write`
- `audit:read/export`
- `system:monitor`

**Implementation:** `core/authorization.py` with `@require_permission` decorators.

### Layer 2: Defense-in-Depth Architecture

#### Network Security
- **API Gateway** pattern with rate limiting (100 req/min IP default)
- **Strict CORS** whitelisting (remove wildcard in production)
- **Security Headers:**
  - `Strict-Transport-Security: max-age=31536000`
  - `Content-Security-Policy`
  - `X-Frame-Options: DENY`
  - `X-Content-Type-Options: nosniff`

#### Container Hardening
- **Non-root container execution**
- **Read-only filesystem** for application code
- **Seccomp/AppArmor** profiles (deploy-time config)
- **Resource limits** (CPU, memory)
- **Docker content trust** for image verification

#### Inter-Service Communication
- **TLS 1.3** enforced on all connections
- **Mutual TLS (mTLS)** for service-to-service auth (planned)
- SPIFFE/SPIRE for service identity (future)

### Layer 3: Data Protection & Encryption

#### Data at Rest
- **AES-256-GCM** envelope encryption for all stored data
- **Master key** stored in HashiCorp Vault or KMS
- **Per-analysis data key** rotation
- **SHA-256 integrity hashes** with HMAC signatures
- Encrypted `history.json` → `history.json.enc`

**Storage Flow:**
1. Serialize data to JSON
2. Generate random DEK (data encryption key)
3. Encrypt data with AES-256-GCM DEK
4. Encrypt DEK with KEK (master key from Vault)
5. Compute HMAC signature for integrity
6. Write encrypted envelope + signature atomically

**File Structure:**
```
data/
  history.json.enc    # Encrypted envelope
  history.sig         # HMAC signature file
  users.json          # Encrypted user store (contains password hashes)
  keys/               # Optional key material (Vault recommended)
```

#### Data in Transit
- **TLS 1.3** minimum (no TLS 1.2 in production)
- Strong cipher suites only (AES-256-GCM, CHACHA20-POLY1305)
- **Perfect Forward Secrecy** (ECDHE)
- **Certificate pinning** (optional for high-value clients)
- Automatic certificate renewal (Let's Encrypt/ACM)

#### Secret Redaction
Before storage, submitted code is scanned for secrets:
- API keys (`api_key`, `apikey`, `token`)
- Passwords (`password`, `passwd`, `pwd`)
- Private keys (PEM blocks, SSH keys)
- AWS credentials (`AKIA...`)
- Connection strings, JWT secrets, etc.

**Detection methods:**
- **Custom regex patterns** for known secret formats
- **Presidio NLP** for PII (optional)
- **Language-specific** patterns (env var access)

**Redaction process:**
1. Detect secrets and PII
2. Replace with tokens: `[REDACTED-api_key-abc123]`
3. Process **only redacted code** in pipeline
4. Store secret mapping encrypted separately
5. Restoration requires MFA + audit log entry

**Benefits:**
- Secrets never appear in logs/storage
- Compliant with data leakage prevention (DLP)
- Mitigates credential stuffing attacks

### Layer 4: Continuous Monitoring & Behavioral Analytics

#### Audit Logging
**Every security-relevant event is logged:**
- Authentication (success/failure)
- Authorization (grant/deny)
- Data access (who, what, when)
- Configuration changes
- System errors

**Log format (JSONL, one per line):**
```json
{
  "timestamp": "2025-05-10T14:30:00Z",
  "event_id": "uuidv4",
  "correlation_id": "uuid",
  "actor": {
    "user_id": "...",
    "ip": "1.2.3.4",
    "user_agent": "..."
  },
  "action": "code.analyze",
  "resource": {"type": "code_submission", "id": "uuid"},
  "outcome": "success|failure",
  "metadata": {"language": "python", "size": 1024}
}
```

**Features:**
- **Append-only** (no overwrites)
- **Chain of hashes** with HMAC for tamper detection
- **Automatic rotation** (daily or size-based)
- **Long-term archival** (compressed, WORM storage)
- **SIEM integration** (Elastic, Splunk, Datadog)

#### UEBA (User & Entity Behavior Analytics)
**Baseline profiling:** Each user's normal behavior
- Login times (9am-5pm EST)
- Preferred languages
- Typical code sizes
- Access patterns

**Anomaly detection:**
- **Statistical methods:** Z-score, IQR for outliers
- **ML models:** Isolation Forest, One-Class SVM
- **Real-time alerts:** Slack/PagerDuty webhooks

**Example anomalies:**
```
[WARNING] 3 failed logins from IP 1.2.3.4 in 5 minutes
[CRITICAL] User admin logged in from new country (CN → US)
[MEDIUM] Bulk download: 100 history entries in 1 minute
[HIGH] Code submission with exfiltration patterns (base64 blobs)
```

### Layer 5: Integrity & Auditing

#### Immutable Audit Trail
Audit logs are:
1. **Append-only** (no delete/update)
2. **Signed** with HMAC (key stored separately)
3. **Hashed-chain** to detect tampering
4. **Encrypted** at rest
5. **Replicated** to remote SIEM

**Verification commands:**
```bash
# Verify last 100 entries
python -m services.audit --verify --tail 100

# Full integrity check
python -m services.audit --verify --all
```

#### Tamper Detection
- **Daily integrity scans** (automated)
- **Real-time alerts** on signature mismatch
- **Chain continuity** verification (Merkle tree)
- **Immutable storage** (WORM/S3 Object Lock)

#### Forensic Readiness
All data is **immutable and traceable**:
- Complete user activity timeline
- Full request/response correlation IDs
- Code analysis snapshots
- Administrative action trails

**Export formats:** JSON, CSV, STIX/TAXII (for sharing with CERTs)

## Getting Started

### Prerequisites
- Python 3.11+
- OpenSSL (for key generation)
- Optional: HashiCorp Vault

### Quick Start

1. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

2. **Generate key pair for JWT:**
```bash
# Private key (keep secret!)
openssl genrsa -out jwt_private.pem 2048

# Public key (safe to distribute)
openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem
```

3. **Generate encryption key:**
```bash
openssl rand -base64 32  # 256-bit key
```

4. **Create `.env` file:**
```bash
cp .env.example .env
# Edit .env with your keys
```

5. **Initialize database/migrations:**
```bash
python main.py  # Automated on startup
```

6. **Create admin user (first run):**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "ChangeMeNow!",
    "roles": ["admin"]
  }'
```

7. **Enable MFA for admin:**
```bash
# Step 1: Get MFA secret
curl -X GET "http://localhost:8000/api/v1/auth/mfa/setup" \
  -H "Authorization: Bearer <token>"

# Step 2: Verify with TOTP from app
curl -X POST "http://localhost:8000/api/v1/auth/mfa/verify" \
  -H "Authorization: Bearer <token>" \
  -d '{"totp_code": "123456"}'
```

### Production Deployment

1. **Use environment variables or secret store** (never commit keys)
2. **Enable TLS** with valid certificates (certbot/ACM)
3. **Configure Vault** for key management
4. **Set up SIEM** (Elastic Cloud, Splunk, etc.)
5. **Enable rate limiting** (100 req/min per IP)
6. **Deploy as Docker containers** with security profiles
7. **Configure log shipping** to remote storage
8. **Set up monitoring** (Prometheus + Grafana)
9. **Regular penetration testing** (quarterly)
10. **Key rotation schedule** (annual)

## Security Operations

### Incident Response

**Breach detected →** Alert via PagerDuty → Isolate systems → Preserve logs → Forensic analysis

**Compromised account →** Immediate lockout → MFA reset → Password rotate → Access review

**Data exfiltration →** SIEM alerts → File integrity monitoring → Legal notification (72h GDPR)

### Compliance

Feature | SOC2 | ISO 27001 | HIPAA | GDPR
--------|------|-----------|-------|------
Encryption at rest | ✓ | ✓ | ✓ | ✓
MFA | ✓ | ✓ | ✓ | ✓
Audit logging | ✓ | ✓ | ✓ | ✓
Access controls | ✓ | ✓ | ✓ | ✓
Incident response | ✓ | ✓ | ✓ | ✓

## Monitoring & Observability

### Key Metrics (Prometheus)
```yaml
- auth.login_success_total
- auth.login_failure_total
- auth.mfa_success_total
- auth.mfa_failure_total
- code.scans_total
- code.scan_duration_seconds
- rate_limit.exceeded_total
- audit.logs_written_total
- memory.encryption_errors_total
```

### Dashboards (Grafana)
- **Auth Overview:** Login success rate, MFA enrollment, active sessions
- **Security Events:** Failed logins, anomalies, rate limits
- **System Health:** Encryption errors, memory integrity, uptime
- **Usage:** Scans per user, top vulnerabilities, language distribution

## Testing

### Security Test Suite
```bash
# Run all security tests
pytest tests/security/

# Penetration testing
python -m security.penetration_test

# Integrity verification
python -m services.audit --verify

# Dependency scanning
pip-audit
safety check
```

### Built-in Checks
- **Startup probes:** `/healthz`, `/readyz`, `/livez` include security checks
- **Memory integrity:** Verified on startup and hourly
- **Log rotation:** Daily or 100MB limits
- **Certificate expiry:** Monitored with alerts

## Architecture Diagrams

### Request Flow
```
Client → TLS → API Gateway → Auth Middleware → RBAC → Rate Limit → 
Pipeline (Redact → Analyze → Report) → Encrypted Storage → 
Audit Log (immutable) → SIEM
```

### Data Flow
```
Code submission
  ↓
Redaction (secrets removed)
  ↓
Pipeline agents (analyze redacted code)
  ↓
Results stored (no original code)
  ↓
Audit trail (who accessed what when)
```

## Contributing

When adding features:
1. **Always audit log** security-relevant actions
2. **Apply least privilege** - default deny, grant explicitly
3. **Encrypt sensitive data** - never log raw secrets
4. **Validate input** - sanitize all user content
5. **Add tests** - include security test cases

## References

- [NIST Zero Trust Architecture](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-207.pdf)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [CIS Controls v8](https://www.cisecurity.org/controls/)
- [SANS 20 Critical Security Controls](https://www.sans.org/critical-security-controls/)

## License

Internal use only. Confidential.

---

**Last Updated:** 2026-05-10  
**Version:** 1.0  
**Owner:** Security Engineering
