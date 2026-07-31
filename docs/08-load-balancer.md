# Load Balancing: L4 vs L7 Explained

This document explains Layer 4 and Layer 7 load balancing — how traffic is distributed across multiple backend instances in Kubernetes and cloud environments.

---

## What is a Load Balancer?

A **load balancer** distributes incoming network traffic across multiple backend servers (pods, VMs, containers). It acts as a single entry point that intelligently routes traffic to the right destination.

### Why We Need Load Balancers

| Problem | Load Balancer Solution |
|---------|------------------------|
| Single point of failure | Distributes traffic → if one backend fails, others handle the load |
| Scalability | Spread load across many instances → handle more traffic |
| Zero-downtime deployments | Route traffic to healthy pods while updating others |
| Centralized security | Terminate TLS, enforce policies at one point |

---

## Load Balancer Types by OSI Layer

| Type | OSI Layer | Routes on | Example |
|------|-----------|-----------|---------|
| **L4 (Transport)** | Layer 4 (Transport) | IP address + Port | AWS CLB, K8s ClusterIP Service |
| **L7 (Application)** | Layer 7 (Application) | HTTP headers, paths, cookies, TLS | AWS ALB, NGINX Ingress, HAProxy |

---

## Layer 4 Load Balancer

### How It Works

L4 load balancers operate at the **Transport layer** (TCP/UDP). They forward packets based **only** on:

- **Source IP address**
- **Destination IP address**
- **Source port**
- **Destination port**

They do **not** inspect the content of the data being transmitted.

### L4 Load Balancer Diagram

```
              ┌────────────────────────────────┐
              │        L4 Load Balancer        │
              │     (IP + Port Only — Layer 4) │
              │  • AWS CLB/NLB, Azure LB       │
              │  • K8s ClusterIP Service       │
              └───────────────┬────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
          ┌─────────┐   ┌─────────┐   ┌─────────┐
          │ Pod-A:  │   │ Pod-B:  │   │ Pod-C:  │
          │ 8080    │   │ 8080    │   │ 8080    │
          │ 10.244  │   │ 10.244  │   │ 10.244  │
          └─────────┘   └─────────┘   └─────────┘
         Round-robin / Least connections / Source IP hash
```

Traffic is distributed by:
- **Round-robin** — sequential distribution
- **Least connections** — send to least-busy backend
- **Random selection** — random backend pick
- **Source IP hash** — sticky to client IP

### What L4 Cannot Do

| Feature | L4 Support | Reason |
|---------|------------|--------|
| Host-based routing (`myapp.com` → App A) | ❌ | No access to HTTP Host header |
| Path-based routing (`/api` → App A) | ❌ | No access to HTTP URL path |
| TLS termination | ❌ | Doesn't understand TLS application data |
| Cookie-based session affinity | ❌ | Can't read HTTP cookies |
| Header-based routing (User-Agent, X-Auth) | ❌ | Can't inspect HTTP headers |

### L4 Load Balancers in Our Cluster

```
┌─────────────────────────────────────┐
│  Kubernetes Service (ClusterIP)     │  ← This IS an L4 load balancer
│  selector: app=flask-app            │  Routes on: IP + Port only
│  ports: 8080 → 5001                 │  Uses: kube-proxy (iptables/IPVS)
└─────────────────────────────────────┘
```

Every **Kubernetes Service** (ClusterIP, NodePort, LoadBalancer) is an L4 load balancer. It routes traffic based on **Service ClusterIP + Port** to the **pod IP + targetPort**. It knows nothing about HTTP, domains, or URLs.

### When to Use L4

| Use Case | Example |
|----------|---------|
| Database connections | MySQL, PostgreSQL, Redis (internal) |
| gRPC services | Microservices talking over gRPC |
| TCP/UDP-based protocols | SSH, custom protocols |
| Simple load distribution | When you just need to spread TCP traffic |

---

## Layer 7 Load Balancer

### How It Works

L7 load balancers operate at the **Application layer** (HTTP/HTTPS). They can inspect the **full content** of the request:

- **Host header** (`myapp.com`)
- **URL path** (`/api/users`, `/health`)
- **HTTP method** (`GET`, `POST`, `PUT`)
- **Cookies** (`session_id=xyz`)
- **Custom headers** (`X-Auth-Token`)
- **TLS certificate** (for mutual TLS)

### L7 Load Balancer Diagram

```
                  L7 Load Balancer (NGINX Ingress)
                  (HTTP/HTTPS — reads full request)
                       │
          ┌────────────┼────────────┐
          │            │            │
  Host: myapp.com  Host:          Path: /api  Path: /health
  Path: /          mysecondapp.com
          │            │
          ▼            ▼
     flask-app    second-app
     Pods         Pods
```

### L7 Routing Rules in Our Cluster

```yaml
# From deployments/04-ingress/ingress.yaml
spec:
  rules:
  - host: myapp.com                # L7: routes by Host header
    http:
      paths:
      - path: /                    # L7: routes by URL path
        backend:
          service: flask-app-service
          port: 8080

  - host: mysecondapp.com          # L7: routes to different app
    http:
      paths:
      - path: /
        backend:
          service: second-app-service
          port: 8080
```

### What L7 Can Do That L4 Cannot

| Feature | L7 Support | How It Works |
|---------|------------|--------------|
| Host-based routing | ✅ | Reads `Host: myapp.com` header |
| Path-based routing | ✅ | Reads `GET /api/users` path |
| TLS termination | ✅ | Decrypts HTTPS → HTTP |
| Cookie/session affinity | ✅ | Sets `sticky` cookies |
| Header-based routing | ✅ | Inspects `X-Auth-Token`, etc. |
| Rate limiting | ✅ | Limits requests per IP/path |
| Request/response modification | ✅ | Rewrites URLs, adds headers |
| Compression | ✅ | gzip/brotli compression |

### When to Use L7

| Use Case | Example |
|----------|---------|
| Web applications | HTTP routing by domain/URL |
| Microservices API gateway | `/api/v1/users` → user-service |
| Multi-tenant apps | `tenant1.app.com` → tenant1 pods |
| HTTPS termination | SSL/TLS handling |
| Blue/green deployments | Route by header (`X-Env: staging`) |

---

## L4 vs L7: Side-by-Side Comparison

| Feature | L4 (Transport) | L7 (Application) |
|---------|----------------|------------------|
| **OSI Layer** | Layer 4 | Layer 7 |
| **Routes on** | IP + Port | Host, Path, Headers, Cookies, TLS |
| **Speed** | Faster (less processing) | Slightly slower (parsing HTTP) |
| **TLS** | Pass-through only | Termination at LB |
| **Visibility** | Blind to content | Sees full request/response |
| **Security** | Basic (IP/port rules) | Advanced (WAF, rate limiting, JWT) |
| **Example in our cluster** | `ClusterIP Service` | `NGINX Ingress` |
| **Cloud example** | AWS CLB, AWS NLB | AWS ALB, GCP HTTP LB |
| **Use when you need** | Simple load distribution | Smart routing, HTTPS, headers |

---

## Our Cluster's Load Balancer Chain

Our architecture uses **both** L4 and L7 load balancers in sequence:

```
                  ┌─────────────────────────────┐
                  │  Client (Browser)           │
                  │  HTTPS://myapp.com          │
                  └───────────┬─────────────────┘
                              │
                  ┌───────────▼─────────────────┐
                  │  L7 Load Balancer           │
                  │  NGINX Ingress              │
                  │  ───────────────────────────│
                  │  • TLS termination          │
                  │  • Host routing (myapp.com) │
                  │  • Path routing (/)         │
                  │  • Header inspection        │
                  └───────────┬─────────────────┘
                              │ HTTP (unencrypted)
                  ┌───────────▼─────────────────┐
                  │  L4 Load Balancer           │
                  │  ClusterIP Service          │
                  │  ───────────────────────────│
                  │  • IP + port routing        │
                  │  • Round-robin across pods  │
                  │  • Endpoint discovery       │
                  └───────────┬─────────────────┘
                              │ TCP
                  ┌───────────▼─────────────────┐
                  │  Backend Pod                │
                  │  flask-app:5001             │
                  │  ───────────────────────────│
                  │  • Processes request        │
                  │  • Returns HTTP response    │
                  └─────────────────────────────┘
```

### Why Both L7 + L4?

```
L7 (Ingress) decides:   "Which service should handle this request?"
L4 (Service) decides:   "Which pod in that service should get it?"
```

- **L7** handles the smart routing (which domain/path → which service)
- **L4** handles the distribution within that service (which pod replica)
- They work together — L7 routes to a Service, the Service routes to a Pod

---

## Cloud Provider Load Balancer Comparison

| Cloud | L4 Load Balancer | L7 Load Balancer |
|-------|------------------|------------------|
| **AWS** | Classic LB (CLB), Network LB (NLB) | Application LB (ALB) |
| **GCP** | TCP Proxy, HTTP(S) LB (L4 mode) | HTTP(S) LB, HTTPS LB |
| **Azure** | Basic LB, Standard LB | Application Gateway |
| **Kubernetes** | Service type: `LoadBalancer`, `ClusterIP` | Ingress controller (NGINX, Traefik) |
| **Our cluster** | `ClusterIP Service` (L4) | `NGINX Ingress` (L7) |

---

## NetworkPolicies: The Firewall Side of Load Balancing

While load balancers **distribute** traffic, **NetworkPolicies** **restrict** it:

```
┌───────────────────────────────────────────────────┐
│  NetworkPolicy (deployments/06-network-policy/)   │
│                                                   │
│  ingress:                                         │
│    - from:                                        │
│        - namespaceSelector: {name: ingress-nginx} │  ← Allow from Ingress
│        - podSelector: {app: flask-app}            │
│      ports:                                       │
│        - protocol: TCP                            │
│          port: 5001                               │
│                                                   │
│  egress:                                          │
│    - to:                                          │
│        - podSelector: {app: redis}                │
│      ports:                                       │
│        - protocol: TCP                            │
│          port: 6379                               │
└───────────────────────────────────────────────────┘
```

NetworkPolicies operate at **Layer 3/4** — they filter traffic by IP and port, acting as a micro-firewall.

---

## Key Takeaways

| Concept | Detail |
|---------|--------|
| **L4 (Transport)** | Routes on IP + port; fast, blind to content |
| **L7 (Application)** | Routes on HTTP headers/paths; smart, sees content |
| **Our L4** | ClusterIP Services (kube-proxy) |
| **Our L7** | NGINX Ingress controller |
| **Why both** | L7 picks the service, L4 picks the pod |
| **Layer 6** | TLS encryption sits between L7 and L4 |

---

## Cross-References

| Resource | Location |
|----------|----------|
| Ingress config (L7 routing) | `deployments/04-ingress/ingress.yaml` |
| Service config (L4 routing) | `deployments/01-deployment/service.yaml` |
| TLS termination (L6) | `docs/07-tls.md` |
| TLS certificates | `deployments/07-tls-certs/` |
| NetworkPolicies (L3-L4 firewall) | `deployments/06-network-policy/` |
| Full request flow | `docs/05-request-flow.md` |
| OSI model (all layers) | `docs/06-tcp-osi.md` |
| NGINX L4 Stream Proxy (NEW) | `docs/09-nginx-l4-stream-proxy.md` |