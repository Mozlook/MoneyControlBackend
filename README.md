# MoneyControlBackend

## Authentication – JWT (RS256) design

**Goal:** stateless access tokens signed with RS256; refresh tokens are random secrets stored server-side (hashed) with rotation.

### JWS header (protected)

- `alg`: **RS256** (RSASSA-PKCS1-v1_5 with SHA-256).
- `kid`: key identifier (e.g., UUID). Used to pick the correct public key during verification and to enable key rotation.
- `typ`: **"JWT"** (recommended to reduce content-type mix-up).

**Why:** Header describes _how_ the token is signed and _which key_ was used. RS256 separates signing (private key) from verification (public key). `kid` enables smooth rotations. See RFC 7515 (JWS) and JWT BCP.  
Sources: RFC 7515; JWT BCP (RFC 8725). :contentReference[oaicite:0]{index=0}

### JWT claims (payload)

- **Registered claims** (RFC 7519):
  - `iss` (issuer): e.g., `moneycontrol-backend`
  - `aud` (audience): e.g., `moneycontrol-api`
  - `sub` (subject): **user UUID** (from `users.id`)
  - `exp` (expiration): UNIX seconds
  - `iat` (issued-at): UNIX seconds
  - `jti` (JWT ID): random UUID
  - `nbf` (not-before): _optional_; usually omitted
- **Private claims**:
  - `email`: included for convenience (not used for authorization decisions)

**Why:** Keep payload minimal and verifiable. `iss`/`aud` bind the token to the right issuer and API; `sub` identifies the user; `exp` and `iat` bound token lifetime; `jti` helps trace/blacklist. See RFC 7519 + BCP.  
Sources: RFC 7519; JWT BCP (RFC 8725). :contentReference[oaicite:1]{index=1}

### Validation rules (API)

1. Require `Authorization: Bearer <token>`.
2. Parse header, select public key by `kid`; **reject** tokens where `alg` ≠ `RS256` or header `typ` ≠ `"JWT"`.
3. Verify signature with the selected public key.
4. Verify claims:
   - `iss` == `AUTH_ISSUER`
   - `aud` contains `AUTH_AUDIENCE`
   - `exp` not expired (allow small clock skew, e.g. 60s)
   - (optional) `nbf` ≤ now
5. Treat `email` as informational only (never an authz source).

**Why:** These checks are the core BCP guidance: fix the algorithm, validate issuer/audience/time, and keep claims minimal.  
Sources: JWT BCP (RFC 8725). :contentReference[oaicite:2]{index=2}

### Token lifetimes & rotation

- **Access token TTL:** `15m`
- **Refresh token TTL:** `30d`
- **Rotation:** every refresh returns a **new** refresh token and **revokes** the previous one (single-use). Reuse of an old refresh token indicates theft; optionally revoke the whole session family.

**Why:** Rotation narrows abuse windows and enables reuse detection; recommended by modern OAuth/JWT practices.  
Source: JWT BCP (RFC 8725). :contentReference[oaicite:3]{index=3}

### Environment variables (example)

- `AUTH_JWT_PRIVATE_KEY_PATH`: path to RSA private key (PEM)
- `AUTH_JWT_PUBLIC_KEY_PATH`: path to RSA public key (PEM)
- `AUTH_JWT_KID`: key identifier (e.g., UUID v4)
- `AUTH_ISSUER`: e.g., `moneycontrol-backend`
- `AUTH_AUDIENCE`: e.g., `moneycontrol-api`
- `AUTH_ACCESS_TOKEN_TTL`: e.g., `15m`
- `AUTH_REFRESH_TOKEN_TTL`: e.g., `720h` (30 days)
- `AUTH_REFRESH_OVERLAP`: optional concurrency window for rotation, e.g., `5s`

### References

- **JWT** (structure & claims): RFC 7519. :contentReference[oaicite:4]{index=4}
- **JWS** (header, `alg`, `kid`, signature): RFC 7515. :contentReference[oaicite:5]{index=5}
- **Best Current Practices** (security guidance): RFC 8725. :contentReference[oaicite:6]{index=6}
