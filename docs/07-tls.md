# TLS (Transport Layer Security) Explained

This document explains TLS — the protocol that secures all HTTPS traffic in our cluster. It covers what TLS is, how it works, which OSI layer it operates on, and how it's used in our Kubernetes playground.

---

## What is TLS?

**TLS** (Transport Layer Security) is a cryptographic protocol that provides secure communication over a network. It was developed as a successor to SSL (Secure Sockets Layer), which is now deprecated.

### What TLS Protects Against

| Threat | How TLS prevents it |
|--------|---------------------|
| **Eavesdropping** | Data is encrypted — no one can read it |
| **Man-in-the-Middle (MITM)** | Certificates verify the server's identity |
| **Tampering** | Data integrity checks detect any modification |

### TLS vs. SSL

- **SSL** — The older protocol (versions 1.0, 2.0, 3.0) — **all versions are insecure and deprecated**
- **TLS** — The current standard (versions 1.0, 1.1, 1.2, **1.3** — TLS 1.3 is the latest and most secure)
- People use the terms interchangeably, but TLS is the correct modern term

---

## Which OSI Layer Does TLS Operate On?

**TLS operates at Layer 6: Presentation Layer.**

```
Layer 7 (Application)  →  HTTP (plaintext)
─────────────────────────
Layer 6 (Presentation) →  TLS (encryption/decryption)     ← TLS lives here
─────────────────────────
Layer 4 (Transport)    →  TCP
```

TLS sits **between** the Application layer (HTTP) and the Transport layer (TCP). It encrypts application data before it is sent over TCP and decrypts it on the receiving end.

This positioning is important: TLS does not change how TCP or IP works — it just adds a security layer on top of whatever protocol is above TCP.

---

## The TLS Handshake

When a client (browser) connects to a TLS-protected server, a handshake establishes the secure session:

```
Client                          Server (Ingress)
  │                                 │
  │  ── Client Hello ──────────────→│
  │  (supported TLS versions,       │
  │   cipher suites, random bytes)  │
  │                                 │
  │  ←── Server Hello ──────────────│
  │  (chosen TLS version,           │
  │   cipher suite)                 │
  │                                 │
  │  ←── Server Certificate ────────│
  │  (our server.crt signed by CA)  │
  │                                 │
  │  ←── Server Key Exchange ───────│
  │  (Diffie-Hellman parameters)    │
  │                                 │
  │  ←── Server Hello Done ─────────│
  │                                 │
  │  ── Client Key Exchange ───────→│
  │  (pre-master secret,            │
  │   encrypted with server's pub)  │
  │                                 │
  │  ── Change Cipher Spec ─────────│
  │  ←── Change Cipher Spec ────────│
  │                                 │
  │  ── Encrypted Handshake ───────→│
  │  ←── Encrypted Handshake ───────│
  │                                 │
  ═══════ Secure Channel Established ═══════
  │                                 │
  │  ── GET / HTTP/1.1 ────────────→│
  │     (encrypted in TLS)          │
  │                                 │
  │  ←── HTTP 200 OK ───────────────│
  │     (encrypted in TLS)          │
```

### Handshake Summary

| Step | Purpose |
|------|---------|
| **Client Hello** | Client sends supported TLS versions and encryption algorithms |
| **Server Hello** | Server picks the best TLS version and cipher suite |
| **Server Certificate** | Server sends its certificate (signed by the CA) for identity verification |
| **Key Exchange** | Both sides agree on a shared session key (via Diffie-Hellman) |
| **Change Cipher Spec** | Both switch to encrypted communication |
| **Encrypted Handshake** | Final verification that the handshake wasn't tampered with |
| **Secure Channel** | All subsequent data is encrypted with the session key |

> The session key is **ephemeral** — it exists only for this connection. A new key is generated for every new TLS session.

---

## TLS in Our Cluster

### Where TLS Happens

```
Client (Browser)
  │
  │ HTTPS (TLS 1.2/1.3 — encrypted)
  ▼
┌─────────────────────────────────┐
│  NGINX Ingress Pod              │
│  ┌─────────────────────────────┐│
│  │ TLS Termination (L6)        ││   ← TLS is decrypted here
│  │ server.crt / server.key     ││   ← stored in my-tls-secret
│  │ CA validates the cert chain ││
│  └─────────────────────────────┘│
└─────────────────────────────────┘
  │
  │ HTTP (unencrypted — inside cluster)
  ▼
┌─────────────────────────────────┐
│  Flask-App Pod                  │
│  app.py:5001 — receives plain   │   ← No TLS here
│  HTTP traffic                   │
└─────────────────────────────────┘
```

### Our TLS Certificate Setup

We use **self-signed certificates** generated in `deployments/07-tls-certs/`:

```
deployments/07-tls-certs/
├── ca.crt           ← Certificate Authority (root of trust)
├── ca.key           ← CA private key (NEVER share this)
├── server.crt       ← Server certificate (for myapp.com)
├── server.key       ← Server private key (kept secret)
├── server.csr       ← Certificate Signing Request
├── client.crt       ← Optional client certificate (mTLS)
├── client.key       ← Optional client private key
├── client.csr       ← Client CSR
├── san.cnf          ← Subject Alternative Names config
├── ca.srl           ← CA serial number file
└── README.md        ← Instructions for regenerating certs
```

### Certificate Chain

```
Client browser
  │
  │ Validates: server.crt → signed by → ca.crt
  │
┌─────────────────────────────────────────────┐
│  CA (Certificate Authority)                 │
│  ca.crt + ca.key (self-signed root)         │
│  │                                          │
│  │ signs with ca.key                        │
│  ▼                                          │
│  server.crt (signed by CA, CN=myapp.com)    │
│  SANs: myapp.com, mysecondapp.com           │
│  │                                          │
│  │ signed with ca.key                       │
│  ▼                                          │
│  client.crt (for mutual TLS if needed)      │
└─────────────────────────────────────────────┘
```

### Kubernetes Secret

The server certificate and private key are stored in a Kubernetes **Secret** that the Ingress controller reads:

```yaml
# From deployments/04-ingress/ingress.yaml
spec:
  tls:
  - hosts:
    - myapp.com
    - mysecondapp.com
    secretName: my-tls-secret      ← references this K8s Secret
```

The Secret is created with:
```bash
kubectl create secret tls my-tls-secret \
  --cert=server.crt \
  --key=server.key \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## TLS Termination vs. Passthrough

### TLS Termination (Our Setup)

```
Client → HTTPS → Ingress (decrypts) → HTTP → Pod
```

- TLS is **terminated at the Ingress**
- Pod receives plain HTTP (no TLS overhead)
- **Advantage:** Simplifies backend apps (they don't need TLS)
- **Trade-off:** Traffic between Ingress and pod is unencrypted (safe within the cluster)

### TLS Passthrough (Alternative)

```
Client → HTTPS → Ingress (passes through) → HTTPS → Pod
```

- TLS is **not terminated** at Ingress
- Ingress forwards encrypted traffic to the pod
- Pod must have its own TLS certificate
- **Advantage:** End-to-end encryption
- **Trade-off:** Ingress can't do L7 routing (doesn't see HTTP headers)

### Which Should You Use?

| Scenario | Recommendation |
|----------|---------------|
| Internal cluster only | **Termination** at Ingress (our setup) |
| External-facing, high security | **Passthrough** or end-to-end TLS |
| Development/learning | **Termination** (simpler) |

---

## Certificate Details

### Self-Signed CA (Certificate Authority)

```bash
# Generate CA private key
openssl genrsa -out ca.key 4096

# Generate CA certificate (valid for 365 days)
openssl req -new -x509 -days 365 -key ca.key -out ca.crt \
  -subj "/C=US/ST=State/L=City/O=OurOrg/OU=Dev/CN=OurCA"
```

> This CA is **self-signed** — we sign our own certificate instead of buying from a public CA (like Let's Encrypt). Browsers will show a warning for self-signed certs.

### Server Certificate

```bash
# Generate server key and CSR
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
  -subj "/C=US/ST=State/L=City/O=OurOrg/OU=Dev/CN=myapp.com"

# Sign server cert with CA
openssl x509 -req -days 365 -in server.csr \
  -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt \
  -extfile san.cnf
```

### Subject Alternative Names (SANs)

The `san.cnf` file allows the certificate to work for multiple domains:

```ini
[alt_names]
DNS.1 = myapp.com
DNS.2 = mysecondapp.com
DNS.3 = argocd.myapp.com
IP.1 = 127.0.0.1
```

---

## TLS in Context of the OSI Model

```
┌───────────────────────────────────────────────────────────────┐
│ Layer 7 (Application)                                         │
│ HTTP: GET / HTTP/1.1                                          │
│                                                               │
│ ──── Boundary: TLS operates here (Layer 6) ────────────────── │
│                                                               │
│ Layer 6 (Presentation) ← TLS LIVES HERE                       │
│ TLS: Encrypts HTTP data to ciphertext                         │
│                                                               │
│ Layer 5 (Session)                                             │
│ TCP session management                                        │
│                                                               │
│ ──── Data flows through layers ────────────────────────────── │
│                                                               │
│ Layer 4 (Transport)                                           │
│ TCP: port 443 (HTTPS)                                         │
│                                                               │
│ Layer 3 (Network)                                             │
│ IP: routing to Ingress pod IP                                 │
└───────────────────────────────────────────────────────────────┘
```

---

## Key Takeaways

| Concept | Detail |
|---------|--------|
| **What is TLS?** | Encryption protocol for secure communication |
| **OSI Layer** | Layer 6 (Presentation) — between Application and Transport |
| **In our cluster** | Terminated at NGINX Ingress; pods receive plain HTTP |
| **Our certs** | Self-signed CA + server cert + client cert (mTLS optional) |
| **K8s Secret** | `my-tls-secret` stores server.crt + server.key |
| **Forward secrecy** | Each TLS session gets a unique ephemeral key |
| **Production** | Use a real CA (Let's Encrypt, AWS ACM) instead of self-signed |

---

## Cross-References

| Resource | Location |
|---------|----------|
| TLS Certificates (source files) | `deployments/07-tls-certs/` |
| TLS Ingress config | `deployments/04-ingress/ingress.yaml` |
| Certificate generation instructions | `deployments/07-tls-certs/README.md` |
| Request flow (with TLS) | `docs/05-request-flow.md` |
| OSI model (TLS layer) | `docs/06-tcp-osi.md` |
| L4 vs L7 Load Balancing | `docs/08-load-balancer.md` |