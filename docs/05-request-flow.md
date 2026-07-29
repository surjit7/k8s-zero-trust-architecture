# Request Flow: Client → Ingress → Service → Pod → Redis

> Every request in this cluster passes through a deterministic chain of layers. This document traces them all — ports, protocols, service names, selectors — so you know exactly what happens between `curl` and `return 200`.

---

## 1. End-to-End Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLIENT (Your Machine)                          │
│  Browser / curl  ·  HTTPS → myapp.com:443                              │
└──────────────────────┬──────────────────────────────────────────────────┘
                       │
                       │  ① DNS: myapp.com → 127.0.0.1 (minikube)
                       │  ② TCP: 127.0.0.1:443
                       │  ③ TLS: ClientHello → Server cert → key exchange
                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    MINIKUBE: Ingress-NGINX Controller                     │
│  Pod: ingress-nginx-controller-*  ·  Service: ingress-nginx-controller  │
│  Listens: 0.0.0.0:443 (HTTPS), 0.0.0.0:80 (HTTP)                      │
│  TLS cert: secret `my-tls-secret` (namespace: argocd or default)        │
│                                                                         │
│  Routing table (from Ingress resource):                                 │
│  ┌───────────────────┬──────────────────────────────────────────────┐   │
│  │ Host: myapp.com   │ Host: mysecondapp.com                        │   │
│  │ Path: / (Prefix)  │ Path: / (Prefix)                             │   │
│  │ → flask-app-svc   │ → second-app-svc                             │   │
│  │   :8080           │   :8080                                      │   │
│  └───────────────────┴──────────────────────────────────────────────┘   │
│                                                                         │
│  Internals:                                                             │
│    nginx.ingress.kubernetes.io/rewrite-target: /                       │
│    (strips prefix path before forwarding to backend)                    │
└──────────────────────┬──────────────────────────────────────────────────┘
                       │
                       │  ④ HTTP (inside cluster, plain text)
                       │     Host: myapp.com (preserved)
                       │     Path: /
                       │     → flask-app-service.default.svc.cluster.local:8080
                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     FLASK-APP SERVICE (ClusterIP)                        │
│  Name: flask-app-service  ·  Namespace: default                         │
│  Type: ClusterIP  ·  ClusterIP: auto-assigned (e.g., 10.96.0.123)      │
│  Selector: app=flask-app  ·  Protocol: TCP                             │
│  Port: 8080 → targetPort: 5001                                         │
│                                                                         │
│  Endpoints (kube-proxy / Cilium CNI populates):                        │
│    - 10.244.0.15:5001 (flask-app-pod-1)                               │
│    - 10.244.0.16:5001 (flask-app-pod-2)  [if replica > 1]             │
│                                                                         │
│  Load balancing: round-robin across endpoints (L4 NAT)                  │
└──────────────────────┬──────────────────────────────────────────────────┘
                       │
                       │  ⑤ HTTP (still plain text)
                       │     GET / HTTP/1.1
                       │     Host: myapp.com
                       │     → 10.244.0.15:5001 (one of the pods)
                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       FLASK-APP POD                                      │
│  Name: flask-app-*  ·  Container port: 5001                            │
│  App: Flask (Python)  ·  Binds to 0.0.0.0:5001                        │
│                                                                         │
│  Request lifecycle:                                                     │
│    1. Receives raw HTTP on :5001 (after TLS was terminated at ingress) │
│    2. Flask router matches the path (/ → /index or /)                  │
│    3. May perform Redis cache lookup (GET/SET) via DNS resolution      │
│    4. Returns HTTP response (e.g., 200 OK, JSON body)                  │
│    5. Response → kube-proxy/Cilium → Ingress controller → Client        │
└─────────────────────────────────────────────────────────────────────────┘

INTERNAL FLOW (Flask Pod → Redis):

┌──────────────┐     DNS + TCP        ┌──────────────────────────────┐
│ Flask Pod    │  ────────────────→   │ redis-master-0               │
│ (10.244.0.15)│  redis-headless:6379  │  Port: 6379 (Redis protocol)│
│              │                       │                              │
│ Flask code:  │                       │  Redis server:               │
│   redis.get()│  ←──────  VALUE ────  │   1. Parses Redis command    │
│   redis.set()│                       │   2. Looks up key in RDB/AOF │
└──────────────┘                       │   3. Returns raw bytes         │
                                        └──────────────────────────────┘
```

---

## 2. Detailed Step-by-Step (External Request)

### Step 1: DNS Resolution

```
Client resolves myapp.com → 127.0.0.1

How: /etc/hosts entry (Minikube)
  127.0.0.1  myapp.com
  127.0.0.1  mysecondapp.com
  127.0.0.1  argocd.myapp.com

In production: DNS A record → cloud Load Balancer IP (e.g., AWS ALB)
```

### Step 2: TCP Three-Way Handshake (Layer 4)

```
Client                          Ingress Controller (port 443)
  │ SYN                           │
  │───────────────────────────────│→
  │                               │
  │  SYN-ACK                      │
  │←──────────────────────────────│
  │                               │
  │  ACK                          │
  │───────────────────────────────│→
  │                               │
  │  ★ TCP connection ESTABLISHED │
```

### Step 3: TLS 1.3 Handshake (Layer 6 — Presentation)

```
Client                          Ingress Controller
  │ ClientHello (cipher suites)   │
  │───────────────────────────────│→
  │                               │
  │  ServerHello + cert chain     │
  │  (my-tls-secret: server.crt)  │
  │←──────────────────────────────│
  │                               │
  │  Key exchange (ECDHE)         │
  │───────────────────────────────│→
  │                               │
  │  ★ Session keys derived       │
  │  ★ All subsequent data encrypted
```

### Step 4: HTTP Request to Ingress (Layer 7 — Application)

```
GET / HTTP/1.1
Host: myapp.com
Accept: text/html
User-Agent: Mozilla/5.0
...
```

The Ingress controller receives the decrypted HTTP request and reads:
- **Host header:** `myapp.com`
- **Path:** `/`
- **Method:** `GET`

It matches against the Ingress resource (`deployments/04-ingress/ingress.yaml`):

```yaml
rules:
- host: myapp.com
  http:
    paths:
    - path: /
      pathType: Prefix
      backend:
        service:
          name: flask-app-service
          port:
            number: 8080
```

Match found → forward to `flask-app-service:8080`.

### Step 5: Ingress → Service (L4 NAT / LB)

```
Ingress controller → ClusterIP Service

Source:   Ingress pod IP (e.g., 10.244.0.5)
Dest:     flask-app-service ClusterIP (e.g., 10.96.100.50:8080)

What the Service does:
  1. Matches selector: app=flask-app
  2. Looks up Endpoints (populated by controller manager)
  3. Picks an endpoint (round-robin)
  4. NATs destination to pod IP:port (e.g., 10.244.0.15:5001)

The Service does NOT understand HTTP — it only knows IPs and ports.
```

### Step 6: Service → Pod (CNI / kube-proxy)

```
Request arrives at pod 10.244.0.15:5001

Cilium (or kube-proxy) handles:
  - iptables/IPVS rules → redirect to correct pod network namespace
  - Connection tracking (conntrack) → return traffic follows same flow

The pod's network namespace receives:

GET / HTTP/1.1
Host: myapp.com
Accept: text/html
...

Port 5001 → Flask process bound to 0.0.0.0:5001
```

### Step 7: Flask Application Processing

```
Flask receives:
  Method:   GET
  Path:     /
  Host:     myapp.com

Flask router:
  / → index_view()
    ├─ Check Redis cache: redis.get("page:index")
    │   → cache miss → continue
    ├─ Query database / compute response
    ├─ Set cache: redis.set("page:index", <result>, ex=300)
    └─ Return HTTP 200 + HTML/JSON body
```

### Step 8: Response (Reverse Path)

```
Flask Pod (10.244.0.15:5001)
  → Cilium/kube-proxy → Service ClusterIP (10.96.100.50:8080)
    → Ingress controller (10.244.0.5:random)
      → TLS encrypt
      → TCP/IP
        → Client browser
```

---

## 3. Detailed Step-by-Step (Internal: Flask → Redis)

### Step 9: Flask Resolves Redis Address

```
Flask code (app.py):
  redis_client = redis.Redis(host='redis-headless', port=6379)

DNS resolution inside the pod:
  redis-headless.default.svc.cluster.local
    → Headless Service (no ClusterIP)
    → Returns actual pod IPs:
      - 10.244.1.20 (redis-master-0:6379)
      - 10.244.1.21 (redis-slave-0:6379)  [if applicable]

Headless Service behavior:
  - No ClusterIP is assigned (spec.clusterIP: None)
  - DNS returns A records for each pod IP
  - Client picks one IP directly (no load balancing via Service)
```

### Step 10: Redis Protocol Exchange (Layer 7 — Redis Protocol)

```
Flask Pod                    Redis Pod (10.244.1.20:6379)
  │ TCP connection established  │
  │                             │
  │ *2                          │  ← Redis RESP2 (RESP3 for modern)
  │ $4                          │
  │ GET                         │  ← Redis command
  │ $11                       │
  │ page:index                  │  ← Key
  │                             │
  │                             │  ← Redis processes:
  │                             │    1. Parse RESP command
  │                             │    2. Lookup key in dataset
  │                             │    3. Check TTL
  │                             │
  │ $13                       │  ← Response
  │ "cached_value"              │
```

### Step 11: Flask Assembles Final Response

```
Flask receives Redis value → inserts into HTML template → returns HTTP 200.
Response travels reverse path → client renders.
```

---

## 4. Multi-App Routing (Second App)

Same chain, different routing:

```
Client: https://mysecondapp.com
  ↓ DNS
  127.0.0.1
  ↓ HTTPS (TLS)
Ingress controller (port 443)
  ↓ Host match: mysecondapp.com
Rules:
  host: mysecondapp.com
  path: / (Prefix)
  → backend: second-app-service:8080
  ↓ Service: second-app-service (ClusterIP)
  selector: app=second-app
  port: 8080 → targetPort: 5001
  ↓ Endpoints
  second-app pod (10.244.0.x:5001)
  ↓ Flask app
  HTTP 200
  ↓ reverse path
  Client
```

---

## 5. ArgoCD Routing

```
Client: https://argocd.myapp.com:8001
  ↓ port-forward (kubectl manages the connection)
  kubectl port-forward svc/argocd-server -n argocd 8001:443
  ↓ TLS (ArgoCD server presents its own cert)
ArGoCD API server (port 443)
  ↓ gRPC + HTTP API
  ArgoCD UI (react frontend)
```

> `argocd.myapp.com` also routes through the **same** Ingress controller
> (via `deployments/04-ingress/argocd-ingress.yaml`), but during local
> development you'll use `port-forward` instead of hitting the Ingress.

---

## 6. Complete Request/Response Lifecycle

```
  T+0s    Browser: https://myapp.com
  T+1ms   DNS: myapp.com → 127.0.0.1
  T+2ms   TCP SYN → 127.0.0.1:443
  T+3ms   TLS handshake (ServerHello, cert, key exchange)
  T+5ms   GET / HTTP/1.1 → Host: myapp.com (encrypted)
  T+6ms   Ingress: terminates TLS, reads Host header
  T+7ms   Ingress: matches rule → flask-app-service:8080
  T+8ms   Service: selector app=flask-app → endpoint 10.244.0.15:5001
  T+9ms   Cilium: NATs packet to pod IP
  T+10ms  Flask: receives GET / on :5001 (plaintext)
  T+11ms  Flask: redis.get("page:index") → cache miss
  T+12ms  Flask: queries Redis (redis-master-0:6379)
  T+13ms  Redis: GET page:index → (nil)
  T+14ms  Flask: renders HTML, sets redis.set("page:index", <data>)
  T+15ms  Flask: returns HTTP 200 + body
  T+16ms  Response: pod → Service → Ingress → TLS encrypt → client
  T+17ms  Browser: renders page
```

---

## 7. Network Protocol Stack (Per Layer)

```
┌─────────────────────────────────────────────────────────┐
│  LAYER  │ PROTOCOL          │ HAPPENS HERE              │
├─────────┼───────────────────┼───────────────────────────┤
│  L7     │ HTTP/1.1 + TLS   │ Browser ↔ Ingress (TLS)   │
│(App)    │                  │ Ingress ↔ Flask (HTTP)    │
│         │                  │ Flask ↔ Redis (RESP)      │
├─────────┼───────────────────┼───────────────────────────┤
│  L6     │ TLS/SSL           │ Ingress terminates TLS   │
│(Pres)   │                  │ (encryption/decryption)    │
├─────────┼───────────────────┼───────────────────────────┤
│  L5     │ (Session)         │ TLS session keys          │
├─────────┼───────────────────┼───────────────────────────┤
│  L4     │ TCP + UDP         │ Client ↔ Ingress (443)   │
│(Trans)  │                  │ Ingress → Service (8080)  │
│         │                  │ Service → Pod (5001)      │
│         │                  │ Pod → Redis (6379)        │
├─────────┼───────────────────┼───────────────────────────┤
│  L3     │ IP (IPv4)         │ kube-proxy/Cilium routes  │
│(Network)│                  │ ClusterIP → Pod IP NAT    │
├─────────┼───────────────────┼───────────────────────────┤
│  L2     │ Ethernet/ARP      │ CNI (Cilium/eBPF)         │
│(Link)   │                  │ Pod → node → overlay        │
└─────────┴───────────────────┴───────────────────────────┘
```

---

## 8. Exact Data at Each Hop

### Hop 1: Browser → Minikube

```
[IP_HDR]
  src: 127.0.0.1
  dst: 127.0.0.1
[TCP_HDR]
  src_port: 54321 (ephemeral)
  dst_port: 443 (HTTPS)
[TLS_RECORD]
  record_type: application_data
  version: TLS 1.3
  length: <N>
[HTTP_HDR]
  GET / HTTP/1.1
  Host: myapp.com
```

### Hop 2: Ingress → Service

```
[IP_HDR]
  src: 10.244.0.5 (Ingress pod IP)
  dst: 10.96.100.50 (flask-app-service ClusterIP)
[TCP_HDR]
  src_port: 42310
  dst_port: 8080 (Service port)
[HTTP_HDR]  (TLS was terminated, plaintext inside cluster)
  GET / HTTP/1.1
  Host: myapp.com
  X-Forwarded-For: 127.0.0.1
  X-Real-IP: 127.0.0.1
```

### Hop 3: Service → Pod

```
[IP_HDR]    (NAT performed by Cilium/kube-proxy)
  src: 10.244.0.5
  dst: 10.244.0.15 (flask-app pod IP)
[TCP_HDR]   (targetPort translation)
  src_port: 42310
  dst_port: 5001 (container port)
[HTTP_HDR]  (unchanged)
  GET / HTTP/1.1
  Host: myapp.com
```

---

## 9. Key Resources (Exact Names)

| Resource | Name | Namespace | Port | Selector |
|----------|------|-----------|------|----------|
| Ingress | `flask-ingress` | default | 443/80 | — |
| Ingress | `argocd-ingress` | default | 443/80 | — |
| TLS Secret | `my-tls-secret` | default/argocd | — | — |
| Flask Service | `flask-app-service` | default | 8080 → 5001 | `app=flask-app` |
| Second App Service | `second-app-service` | default | 8080 → 5001 | `app=second-app` |
| Redis Service | `redis-headless` | default | 6379 (headless) | `app=redis` |
| ArgoCD Service | `argocd-server` | argocd | 443 | — |

---

## 10. Debugging Commands

```bash
# Verify Ingress rules are loaded
kubectl get ingress -n default -o yaml | grep -A 10 'rules:'

# Check Service endpoints (are pods attached?)
kubectl get endpoints flask-app-service -o wide
kubectl get endpoints second-app-service -o wide
kubectl get endpoints redis-headless -o wide

# Verify TLS cert is mounted on Ingress
kubectl describe ingress flask-ingress -n default | grep -i tls

# Test Ingress routing (bypass browser)
curl -k https://myapp.com --resolve 'myapp.com:443:127.0.0.1'

# Test from inside a pod (internal HTTP)
kubectl exec -it <flask-pod> -n default -- \
  curl -s http://flask-app-service:8080/health

# Test Redis connectivity from Flask pod
kubectl exec -it <flask-pod> -n default -- \
  redis-cli -h redis-headless ping

# Verify Cilium eBPF map entries
cilium endpoint list
cilium ipmap list

# View Ingress controller logs (real-time routing decisions)
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx \
  --tail=50 | grep 'myapp.com'

# Port-forward ArgoCD UI (no Ingress needed)
kubectl port-forward svc/argocd-server -n argocd 8001:443
# then visit: https://localhost:8001
```

---

## 11. Cross-References

| Topic | Document |
|-------|----------|
| Ingress YAML | `deployments/04-ingress/ingress.yaml` |
| ArgoCD Ingress YAML | `deployments/04-ingress/argocd-ingress.yaml` |
| Flask Service | `deployments/01-deployment/service.yaml` |
| Second App Service | `deployments/02-second-app/service.yaml` |
| Redis StatefulSet | `deployments/03-statefulset-redis/statefulset.yaml` |
| Network Policies | `deployments/06-network-policy/` |
| TLS Certs | `deployments/07-tls-certs/` |
| Request Flow (this doc) | `docs/05-request-flow.md` |
| TCP / OSI Model | `docs/06-tcp-osi.md` |
| TLS Explained | `docs/07-tls.md` |
| L4 vs L7 Load Balancing | `docs/08-load-balancer.md` |