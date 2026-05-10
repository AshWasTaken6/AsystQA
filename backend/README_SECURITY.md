# AsystQA Backend - Zero Trust Security Implementation

## Architecture Summary

AsystQA backend is a FastAPI-based code analysis service that implements a comprehensive **Zero Trust** security architecture. Every component enforces authentication, authorization, encryption, and audit logging.

## Security Features

### Identity & Access Management (IAM)

**Authentication:**
- JWT with RS256 signatures (RSA 2048-bit)
- 15-minute access tokens
- 7-day refresh tokens with rotation
- Session tracking with IP/User-Agent binding
- Automatic session expiration (24h)

**MFA (Multi-Factor Authentication):**
- TOTP (Google Authenticator compatible)
- WebAuthn/FIDO2 hardware keys
- Backup codes for recovery
- Configurable MFA requirement

**Authorization (RBAC):**
```
viewer    → code:analyze, history:read
analyst   → +code:submit, history:delete_own
admin     → +history:delete_all, config:*, user:*, audit:read
security  → audit:*, system:monitor
```

### Defense-in-Depth

**Network Layer:**
- CORS whitelisting (no wildcards in production)
- Rate limiting (100 req/min/IP default)
- Security headers (HSTS, CSP, X-Frame-Options)
- TLS 1.3 enforcement

**Container Security:**
- Non-root execution
- Read-only filesystem mounts
- Seccomp profile restrictions
- Resource limits (CPU/memory)

### Data Protection

**Encryption at Rest:**
- AES-256-GCM envelope encryption
- Per-operation data keys
- Master key in Vault/KMS
- Encrypted `history.json` → `history.json.enc`
- HMAC signatures for integrity

**Secret Redaction:**
Before storage, code is scanned and redacted:
- API keys, passwords, tokens → `[REDACTED-<type>-<hash>]`
- AWS credentials, private keys, connection strings
- Supports 15+ secret patterns
- Optional PII detection via Presidio

**Encryption in Transit:**
- Full TLS 1.3 with perfect forward secrecy
- Strong cipher suites (no RC4, 3DES, MD5)
- Certificate pinning (optional)
- Short certificate lifetimes (auto-renew)

### Monitoring & Analytics

**Audit Logging:**
All events logged to `logs/audit/audit.jsonl`:
- Authentication events
- Authorization decisions
- Data access requests
- System errors
- Configuration changes

Each entry includes:
- Timestamp + correlation ID
- Actor (user/IP/UA)
- Action/resource/outcome
- Metadata (context)

**UEBA:**
- Detects anomalous user behavior
- Failed login patterns
- Unusual access times/locations
- Bulk data exfiltration signs
- Alerts to Slack/PagerDuty

### Integrity & Compliance

**Immutable Logging:**
- Append-only files
- SHA-256 hash chaining
- HMAC signatures with separate key
- Daily rotation + compression
- 7-year retention

**Tamper Detection:**
- Real-time verification
- Chain continuity checks
- Alert on signature mismatch

**Compliance:**
- SOC2 ready
- GDPR data protection
- HIPAA safeguards (optional)
- ISO 27001 aligned

## Project Structure

```
backend/
├── main.py                    # FastAPI application entry
├── requirements.txt           # Python dependencies
├── .env.example              # Security configuration template
│
├── core/
│   ├── auth.py               # JWT authentication, MFA, sessions
│   ├── authorization.py      # RBAC, permission decorators
│   ├── config.py             # Configuration from env
│   ├── agent_registry.py     # Principal definition
│   └── middleware.py         # Correlation ID & basic rate limit
│
├── services/
│   ├── audit.py              # Immutable audit logging + integrity
│   ├── encryption.py         # AES-256-GCM envelope encryption
│   ├── memory.py             # Encrypted storage, migrations
│   ├── redaction.py          # Secret/PII detection & redaction
│   ├── metrics.py            # Prometheus metrics
│   ├── tasks.py              # Async task queue
│   └── tracing.py            # OpenTelemetry integration
│
├── api/
│   ├── routes.py             # Analysis endpoints (protected)
│   └── auth_routes.py        # Auth endpoints (public + MFA)
│
├── agents/
│   ├── planner.py            # Planning agent
│   ├── reviewer.py           # Quality review agent
│   ├── security.py           # Security analysis agent
│   └── tester.py             # Test generation agent
│
├── middleware/
│   └── security.py           # Auth, rate limiting, security headers
│
├── utils/
│   ├── logger.py             # Structured logging
│   └── audit.py              # Audit helper functions
│
├── schemas/
│   ├── auth.py               # Auth Pydantic models
│   ├── request.py            # Request schemas
│   └── response.py           # Response schemas
│
├── data/                     # Encrypted data storage
│   ├── history.json.enc
│   ├── history.sig
│   └── users.json
│
├── logs/
│   └── audit/
│       ├── audit.jsonl
│       ├── audit.hashes
│       └── audit-20250510.jsonl.gz  # Rotated logs
│
├── keys/                     # RSA keys + secrets (secure location!)
│   ├── jwt_private.pem
│   ├── jwt_public.pem
│   ├── encryption.key
│   └── integrity.key
│
└── scripts/
    └── generate_keys.py      # Key generation utility
```

## API Endpoints

### Authentication (`/auth`)
```
POST   /auth/login           → Get JWT tokens
POST   /auth/logout          → Revoke token
POST   /auth/refresh         → Refresh access token
POST   /auth/register        → Create user (admin only)
GET    /auth/mfa/setup       → Get MFA secret & QR
POST   /auth/mfa/verify      → Enable MFA
GET    /auth/me              → Current user info
```

### Analysis
```
POST   /analyze              → Submit code for analysis (auth required)
GET    /history              → Get analysis history (own only, admin all)
```

### Security Monitoring
```
GET    /security/status      → Security system health
GET    /security/audit/recent → Recent audit events (audit role)
```

All endpoints support `v1` prefix: `/api/v1/...`

## Quick Start

1. **Install dependencies**
```bash
cd backend
pip install -r requirements.txt
```

2. **Generate keys**
```bash
python scripts/generate_keys.py --output-dir ./keys
```

3. **Create configuration**
```bash
cp .env.example .env
# Edit .env with your keys
export JWT_PRIVATE_KEY=$(cat keys/jwt_private.pem | base64 -w0)
export JWT_PUBLIC_KEY=$(cat keys/jwt_public.pem | base64 -w0)
export ENCRYPTION_KEY=$(cat keys/encryption.key)
export AUDIT_INTEGRITY_SECRET=$(cat keys/integrity.key)
```

4. **Run the server**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

5. **Access API**
```
http://localhost:8000/docs          # Interactive docs (requires auth)
http://localhost:8000/openapi.json  # API spec
```

6. **Create admin user**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"admin@example.com","password":"ChangeMeNow!","roles":["admin"]}'
```

7. **Enable MFA**
```bash
# Login to get MFA setup
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"ChangeMeNow!"}'

# Setup MFA
curl -X GET "http://localhost:8000/api/v1/auth/mfa/setup" \
  -H "Authorization: Bearer <token>"

# Verify with TOTP from authenticator app
curl -X POST "http://localhost:8000/api/v1/auth/mfa/verify" \
  -H "Authorization: Bearer <token>" \
  -d '{"totp_code":"123456"}'
```

## Configuration

All settings via environment variables or `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | AsystQA Backend |
| `ENVIRONMENT` | dev/staging/prod | development |
| `DEBUG` | Enable debug mode | false |
| `JWT_PRIVATE_KEY` | RSA private key (base64) | - |
| `JWT_PUBLIC_KEY` | RSA public key (base64) | - |
| `ENCRYPTION_KEY` | AES-256 key (base64) | - |
| `MFA_REQUIRED` | Enforce MFA for all | false |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | true |
| `RATE_LIMIT_PER_MINUTE` | Max requests per minute | 100 |
| `AUDIT_LOG_DIR` | Audit log location | ./logs/audit |
| `ENCRYPTION_KEY_VAULT` | HashiCorp Vault URL | - |

## Testing

```bash
# Run unit tests
pytest tests/unit/

# Run security tests
pytest tests/security/ -v

# Verify memory integrity
python -c "from services.memory import verify_memory_integrity; print(verify_memory_integrity())"

# Check audit log chain
python -c "from services.audit import verify_integrity; verify_integrity(100)"

# Test redaction
python scripts/test_redaction.py
```

## Production Checklist

**Before deploying to production:**

- [ ] Generate strong RSA keys (4096-bit for extra security)
- [ ] Store keys in HashiCorp Vault or cloud KMS
- [ ] Enable TLS with valid certificates
- [ ] Configure SIEM log shipping
- [ ] Set up Prometheus + Grafana monitoring
- [ ] Enable rate limiting (adjust thresholds)
- [ ] Configure CORS with specific origins only
- [ ] Set up alerting (Slack/PagerDuty)
- [ ] Enable MFA for all admin users
- [ ] Perform penetration test
- [ ] Configure daily backups (encrypted)
- [ ] Set up disaster recovery plan
- [ ] Document incident response procedures
- [ ] Enable log rotation and archival
- [ ] Harden container profiles (seccomp, AppArmor)
- [ ] Review and reduce permissions (least privilege)
- [ ] Enable audit log integrity verification
- [ ] Schedule key rotation (annual)
- [ ] Set up secrets scanning in CI/CD

## Incident Response

If a security incident occurs:

1. **Preserve evidence** - Do not delete logs
2. **Isolate affected systems** (network quarantine)
3. **Revoke active sessions** for compromised accounts
4. **Rotate all keys** potentially exposed
5. **Review audit logs** for timeline reconstruction
6. **Notify stakeholders** (legal, PR, customers if required)
7. **Post-mortem analysis** and remediation

## License

Proprietary - Internal Use Only

---

**Version:** 1.0  
**Last Updated:** 2026-05-10  
**Architect:** Security Engineering Team
