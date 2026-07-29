# Lab 07: TLS Certificate Generation

## Concept

Self-signed TLS certificates are used for local development and testing. This lab generates a complete PKI chain:

1. **CA (Certificate Authority)** — the root of trust
2. **Server Certificate** — for the Ingress controller (must include all domains via SAN)
3. **Client Certificate** — for client authentication (optional)

## Why One Certificate for All Apps

The Ingress controller terminates TLS and routes to multiple apps by hostname. The certificate only needs to cover the **domain names**, not the backend apps. A single cert with SAN entries covers `myapp.com`, `mysecondapp.com`, and `argocd.myapp.com`.

## Generated Files

| File | Purpose |
|------|---------|
| `ca.crt` | Root CA certificate |
| `ca.key` | Root CA private key |
| `server.crt` | Server certificate signed by CA (covers all apps) |
| `server.key` | Server private key |
| `client.crt` | Client certificate signed by CA |
| `client.key` | Client private key |

## How to Generate (from scratch)

Run these commands in this folder. The server cert includes **SAN** entries for all hosts served by the Ingress:

```bash
# 1. Generate CA
openssl req -new -x509 -days 365 -nodes -out ca.crt -keyout ca.key -subj "/CN=MyLocalCA"

# 2. Generate server key + CSR with SAN for ALL domains
openssl req -new -nodes -out server.csr -keyout server.key \
  -subj "/CN=myapp.com" \
  -addext "subjectAltName=DNS:myapp.com,DNS:*.myapp.com"

# 3. Sign server cert with CA
openssl x509 -req -days 365 -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt

# 4. Generate client key + CSR
openssl req -new -nodes -out client.csr -keyout client.key -subj "/CN=client"

# 5. Sign client cert with CA
openssl x509 -req -days 365 -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt
```

## How to Create Kubernetes TLS Secret

```bash
kubectl create secret tls my-tls-secret \
  --cert=./server.crt \
  --key=./server.key \
  -n default
```

## How to Verify

```bash
# Verify server cert covers all domains
openssl x509 -in server.crt -text | grep -A2 "Subject Alternative Name"

# Verify server cert against CA
openssl verify -CAfile ca.crt server.crt

# Verify client cert against CA
openssl verify -CAfile ca.crt client.crt
```

## How to Clean Up

```bash
rm -f *.crt *.key *.csr *.srl
```

## Revisiting This Lab

- Change `-days 365` to `-days 1` to test certificate expiration
- Compare SAN-based single cert vs individual certs per domain (SAN is simpler and preferred for Ingress)
- Compare self-signed vs Let's Encrypt certs in terms of trust chain