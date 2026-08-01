# TCP & The OSI Model: Networking Foundations

This document explains the OSI model and TCP — the two foundational networking concepts that make Kubernetes networking possible. Everything in this playground (Services, Ingress, TLS, NetworkPolicies) builds on these layers.

---

## The OSI Model: 7 Layers of Networking

The OSI (Open Systems Interconnection) model standardizes how networked systems communicate. Each layer has a specific job.

### Layer Reference Table

| Layer | Name | What it does | Protocol/Example | In Our Cluster |
|-------|------|--------------|------------------|----------------|
| **7** | Application | User-facing data exchange | HTTP, HTTPS, DNS, Redis protocol | Flask app (`app.py`), Browser |
| **6** | Presentation | Data format, encryption, compression | TLS/SSL, SSL, encryption | TLS termination at NGINX Ingress |
| **5** | Session | Manages connections/dialogues | TCP sessions, WebSocket | Ingress ↔ Pod, Pod ↔ Redis connections |
| **4** | Transport | End-to-end reliability, port routing | **TCP**, UDP | **All Kubernetes Services**, kube-proxy |
| **3** | Network | Routing across networks, addressing | **IP**, ICMP | Pod IPs, ClusterIPs, Node IPs |
| **2** | Data Link | Frame delivery on a single network | Ethernet, VLAN, MAC | Minikube bridge network, CNI plugin |
| **1** | Physical | Raw bit transmission | Cables, WiFi, radio signals | Network cables, WiFi, cloud networking |

---

## Layer 7: Application Layer

**Job:** Handle application-level communication between processes.

### What happens here:
- HTTP requests/responses (`GET /`, `Host: myapp.com`)
- DNS lookups (`myapp.com` → `10.96.xxx`)
- Redis protocol (`GET mykey`, `SET mykey value`)

### In our cluster:
- The **Flask app** (`app.py`) serves HTTP at port 5001 — it speaks HTTP (Layer 7)
- The **browser** sends HTTP requests (Layer 7)
- **Redis** speaks the Redis protocol (Layer 7)

---

## Layer 6: Presentation Layer

**Job:** Translate, encrypt, and compress data so the Application layer can use it.

### What happens here:
- **TLS encryption** — converts plaintext HTTP to encrypted bytes
- Data format conversion (JSON ↔ binary, UTF-8 encoding)
- Compression (gzip)

### In our cluster:
- **NGINX Ingress** terminates TLS — it decrypts HTTPS → HTTP
- The data is encrypted at Layer 6 before leaving the browser
- Decrypted at Layer 6 at the Ingress pod
- Pods receive **plain HTTP** (no TLS between Ingress and pod in our setup)

---

## Layer 5: Session Layer

**Job:** Establish, manage, and tear down connections between applications.

### What happens here:
- Connection lifecycle (open → maintain → close)
- Session persistence (keeping a user on the same server)

### In our cluster:
- **TCP connections** between Ingress → Pod and Pod → Redis are Layer 5 sessions
- Kubernetes maintains endpoint lists that represent active sessions

---

## Layer 4: Transport Layer ← Where Load Balancing Happens

**Job:** Reliable (or unreliable) end-to-end delivery using ports.

### Two protocols at Layer 4:

#### TCP (Transmission Control Protocol) — Reliable
- Connection-oriented: handshake before data
- Guaranteed delivery: lost packets are retransmitted
- Ordered: packets arrive in sequence
- Flow control: adjusts send rate based on receiver capacity
- **Used by:** all our Services, Ingress, Redis, HTTP

#### UDP (User Datagram Protocol) — Unreliable
- Connectionless: fire-and-forget
- No guarantee of delivery or ordering
- Faster: less overhead (no handshake)
- **Used by:** DNS queries (sometimes), video streaming, real-time data

### Port Mapping in Our Cluster

```
Service Port (what clients use)  →  targetPort (what the pod listens on)
─────────────────────────────────────────────────────────────────────────────
flask-app-service:8080           →  flask-app pod:5001
second-app-service:8080          →  second-app pod:5001
redis-service:6379               →  redis pod:6379 (same port)
```

> The **Service** is a Layer 4 load balancer. It routes traffic based solely on **IP address + port**. It does NOT inspect HTTP headers, URLs, or application data.

### How Kubernetes Services Work at Layer 4

```
Client → Service ClusterIP:8080
         │
         ├→ Pod-A:5001 (10.244.1.5)
         ├→ Pod-B:5001 (10.244.1.6)   ← round-robin or random
         └→ Pod-C:5001 (10.244.1.7)
```

`kube-proxy` on each node maintains iptables/IPVS rules that translate the Service IP to an actual pod IP. This is pure Layer 4 — IP routing with port translation.

---

## Layer 3: Network Layer

**Job:** Route packets across different networks using IP addresses.

### What happens here:
- IP addressing (IPv4/IPv6)
- Routing between networks (subnets)
- NAT (Network Address Translation)

### In our cluster:
- **Pod IPs** (10.244.x.x) — individual pod addresses
- **ClusterIPs** (10.96.x.x) — virtual service addresses
- **Node IPs** (192.168.x.x) — Minikube VM addresses
- CNI plugin (e.g., Cilium, Calico) routes packets between pods on different nodes

---

## Layer 2 & 1: Data Link & Physical

### Layer 2 — Data Link
- Ethernet frames, MAC addresses
- Minikube creates a bridge network (`docker0` or `br-*`)
- CNI plugin manages pod-to-pod networking on this bridge

### Layer 1 — Physical
- Network cables, WiFi signals, cloud virtual networking
- Not something we configure — it's the underlying infrastructure

---

## TCP Deep Dive

### Three-Way Handshake

Before any data is sent over TCP, a connection must be established:

```
Client                      Server
  │                           │
  │───── SYN ────────────────→│   "I want to connect"
  │                           │
  │←──── SYN-ACK ─────────────│   "OK, I'm ready"
  │                           │
  │───── ACK ────────────────→│   "Great, let's talk"
  │                           │
  │════════ Connection Established ════════
  │                           │
  │───── HTTP GET / ─────────→│   Data transfer begins
  │                           │
  │←──── HTTP 200 OK ─────────│
  │                           │
  │───── FIN ────────────────→│   "I'm done"
  │←──── FIN-ACK ─────────────│   "OK, connection closed"
```

### Why TCP Matters in Kubernetes

1. **Kubernetes Services are TCP by default** — every `Service` type (ClusterIP, NodePort, LoadBalancer) uses TCP unless explicitly set to UDP
2. **Ingress uses TCP** — the NGINX Ingress controller accepts TCP connections from clients and creates TCP connections to backend pods
3. **NetworkPolicies control TCP** — firewall rules at Layer 3/4 filter by TCP/UDP and port numbers
4. **Reliability** — TCP ensures packets arrive even if the underlying network is unreliable (packet loss, reordering)

### Connection Flow with Port Translation

```
Client → Ingress (port 443)
         │
         │ TCP connection (Layer 4 translation)
         │ ClusterIP:8080 → PodIP:5001
         ▼
     Flask Pod (port 5001)
         │
         │ New TCP connection
         │ ClusterIP:6379 → RedisPodIP:6379
         ▼
     Redis Pod (port 6379)
```

Each hop creates a **new TCP connection** — the Service does not forward the socket; it creates a new one to the backend pod.

---

## How Layers Map to Our Cluster Components

```
┌─────────────────────────────────────────────────────┐
│  Browser (you)                                      │
│  Layer 7: HTTP                                      │
│  Layer 6: TLS (encryption)                          │
│  Layer 4: TCP → Layer 3: IP                         │
└───────────────┬─────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────┐
│  NGINX Ingress Pod                                  │
│  Layer 7: HTTP routing (Host/Path headers)          │
│  Layer 6: TLS termination (decrypts HTTPS → HTTP)   │
│  Layer 4: TCP → Layer 3: IP                         │
└───────────────┬─────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────┐
│  Kubernetes Service (ClusterIP)                     │
│  Layer 4: TCP load balancing (IP + port)            │
│  Layer 3: IP routing to pod endpoints               │
└───────────────┬─────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────┐
│  Flask-App Pod                                      │
│  Layer 7: Flask HTTP server (app.py)                │
│  Layer 4: TCP → Layer 3: IP                         │
│  Layer 7: Redis protocol (if caching)               │
└───────────────┬─────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────┐
│  Redis Pod                                          │
│  Layer 7: Redis protocol (key-value store)          │
│  Layer 4: TCP → Layer 3: IP                         │
└─────────────────────────────────────────────────────┘
```

---

## Key Takeaways

| Concept | Layer | Why it matters for Kubernetes |
|---------|-------|-------------------------------|
| **HTTP/HTTPS** | L7 | What our apps speak; Ingress routes by this |
| **TLS** | L6 | Encrypts data; terminated at Ingress |
| **TCP** | L4 | K8s Services use TCP for all routing |
| **IP** | L3 | Every pod, service, and node has an IP |
| **NetworkPolicies** | L3-L4 | Firewalls that filter by TCP/UDP + port |

---

## Cross-References

| Resource | Location |
|------|-- --------|
| Ingress YAML (L7 routing) | `deployments/04-ingress/ingress.yaml` |
| Service YAML (L4 routing) | `deployments/01-deployment/service.yaml` |
| NetworkPolicies (L3-L4 firewall) | `deployments/06-network-policy/` |
| TLS Certs (L6 encryption) | `deployments/07-tls-certs/` |
| Request flow (all layers) | `docs/05-request-flow.md` |
| TLS Explained | `docs/07-tls.md` |