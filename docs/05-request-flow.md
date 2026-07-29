# Request Flow: Client → Ingress → Service → Pod

This document traces a single HTTP request from your browser all the way to the backend Flask pod and back. It covers both the **external** (client → cluster) and **internal** (cluster → pod → Redis) flows.

---

## Full Architecture Flow

```
┌─────────────┐
│   Browser    │   ← You type https://myapp.com
└──────┬──────┘
       │ DNS resolves myapp.com → Minikube IP
       │ HTTPS (TLS encrypted)
       ▼
┌─────────────────────────────────────────┐
│  Minikube Node + NGINX Ingress Pod      │   ← L7 Load Balancer
│  (listens on port 443/https)            │
│                                         │
│  1. Receives request with Host: myapp.com│
│  2. Reads TLS cert → terminates TLS     │
│  3. Routes by host → flask-app-service  │
│     Route by path → / → flask-app       │
└──────────────┬──────────────────────────┘
               │ HTTP (unencrypted inside cluster)
               │ ClusterIP: 10.96.xxx:8080
               ▼
┌─────────────────────────────────────────┐
│  Flask-App Service (ClusterIP)          │   ← L4 Load Balancer
│  Selector: app=flask-app                │
│  Port: 8080 → targetPort: 5001          │
│                                         │
│  • Load balances across all matching pods │
│  • Resolves endpoints via kube-proxy    │
└──────────────┬──────────────────────────┘
               │ TCP connection
               │ Pod IP: 10.244.xxx:5001
               ▼
┌─────────────────────────────────────────┐
│  Flask-App Pod (app.py:5001)            │   ← Backend application
│                                         │
│  1. Receives HTTP request on :5001     │
│  2. Processes request                   │
│  3. May connect to Redis for cache      │
└──────────────┬──────────────────────────┘
               │
               │ TCP connection
               │ Pod IP: 10.244.xxx:6379
               ▼
┌─────────────────────────────────────────┐
│  Redis Service (Headless)               │
│  Selector: app=redis                    │
│  Port: 6379                             │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Redis Pod (redis-server:6379)          │   ← Data store
│                                         │
│  1. Receives Redis protocol request     │
│  2. Looks up / stores key-value data    │
└─────────────────────────────────────────┘
```

---

## Step-by-Step: External Flow (Client → Pod)

### Step 1: DNS Resolution
```
Browser: https://myapp.com
→ DNS looks up myapp.com
→ Returns Minikube node IP (e.g., 192.168.49.2)
```
> In production, DNS points to a cloud load balancer IP. In Minikube, you add entries to `/etc/hosts`:
> ```
> 127.0.0.1  myapp.com
> 127.0.0.1  mysecondapp.com
> ```

### Step 2: TLS Handshake (HTTPS)
```
Browser → Minikube IP:443
→ TLS Client Hello
→ NGINX Ingress responds with server certificate (from my-tls-secret)
→ Shared session key established
→ All data now encrypted
```
> TLS termination happens at the **Ingress** (not at the pod). The pod receives plain HTTP.

### Step 3: HTTP Request to Ingress
```
GET / HTTP/1.1
Host: myapp.com
```
> The NGINX Ingress controller reads the `Host` header and matches it against the **Ingress** resource rules (`deployments/04-ingress/ingress.yaml`).

### Step 4: Ingress Routing Decision
```
Rule matched:
  host: myapp.com
  path: /
  → backend service: flask-app-service
  → port: 8080
```
> NGINX forwards the request to the Kubernetes Service `flask-app-service`.

### Step 5: Service → Pod Discovery
```
Service (ClusterIP: 10.96.xxx:8080)
  selector: app=flask-app
  → kube-proxy finds matching pods
  → resolves endpoints (pod IPs, port 5001)
  → load balances across replicas (if >1)
```
> The Service acts as an **L4 load balancer** — it only knows IPs and ports, nothing about HTTP.

### Step 6: Pod Receives Request
```
GET / HTTP/1.1
Host: myapp.com

→ flask-app (Python, port 5001) receives the request
→ Processes the route
→ Returns HTTP response
```

### Step 7: Response Returns (Reverse Path)
```
Pod → Service → Ingress → Browser
```
> The response travels the exact reverse path. The browser decrypts the TLS-encrypted response.

---

## Step-by-Step: Internal Flow (Pod → Redis)

When the Flask pod needs cached data, it makes an internal call:

### Step 8: Pod → Redis Service
```
Flask Pod (10.244.1.5:5001)
  → DNS lookup: redis-service.default.svc.cluster.local:6379
  → Headless Service resolves to actual Redis pod IPs
  → Connects directly to Redis pod IP:6379
```
> A **Headless Service** (no ClusterIP) returns the individual pod IPs, allowing the client to connect directly to a specific pod rather than load balancing.

### Step 9: Redis Processing
```
Redis Pod:
  1. Receives Redis protocol command (GET, SET, etc.)
  2. Looks up key in memory
  3. Returns value to Flask pod
```

### Step 10: Flask Responds to Client
```
Flask Pod:
  1. Assembles HTTP response with cached data
  2. Sends back through Ingress
  3. Browser renders the page
```

---

## Multi-App Routing (Second App)

The same flow applies for `mysecondapp.com`, but the Ingress routes to a different backend:

```
Browser → https://mysecondapp.com
  → Ingress matches host: mysecondapp.com
  → Routes to: second-app-service:8080
  → Service selector: app=second-app
  → second-app pod on port 5001
```

Both apps share the **same NGINX Ingress controller** — it's one pod doing L7 routing for multiple services.

---

## Key Concepts Summary

| Concept | Where it happens | What it does |
|---------|-----------------|--------------|
| **DNS** | Browser/OS | Resolves domain → IP |
| **TLS Handshake** | Ingress (L6) | Encrypts the connection |
| **HTTP Routing** | Ingress (L7) | Routes by Host/Path headers |
| **IP Load Balancing** | Service/kube-proxy (L4) | Routes by IP + Port |
| **Endpoint Resolution** | Service → Pod IPs | Finds actual pod addresses |
| **Application Logic** | Pod (Layer 7) | Processes request, returns response |

---

## Visual Summary: Two Flows Side by Side

```
EXTERNAL FLOW (client to pod)          INTERNAL FLOW (pod to redis)
─────────────────────────────────────  ─────────────────────────────────
Browser                                Flask Pod (10.244.1.5)
    │                                      │
    ▼ (HTTPS, TLS)                         ▼ Redis protocol
Ingress (L7 routing)              Redis Service (Headless)
    │                                      │
    ▼ (HTTP, ClusterIP)                   ▼ TCP/IP
Service (L4 routing)               Redis Pod (10.244.2.3)
    │
    ▼ (TCP, Pod IP)
Flask Pod (10.244.1.5)
```

---

## Debugging Commands

```bash
# 1. Check Ingress is serving traffic
kubectl get ingress -n ingress-nginx

# 2. Check Service endpoints
kubectl get endpoints flask-app-service
kubectl get endpoints second-app-service

# 3. Test Ingress routing (external)
curl -k https://myapp.com --resolve 'myapp.com:443:127.0.0.1'

# 4. Test from inside the cluster (internal)
kubectl exec -it <flask-pod> -- curl http://redis-service:6379

# 5. Check which pods are backing a service
kubectl describe service flask-app-service

# 6. View Ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
```

---

## Cross-References

| Resource | Location |
|----------|----------|
| Ingress YAML | `deployments/04-ingress/ingress.yaml` |
| TLS Secret | `deployments/07-tls-certs/` (certs) → `my-tls-secret` (K8s) |
| Flask Service | `deployments/01-deployment/service.yaml` |
| Second App Service | `deployments/02-second-app/service.yaml` |
| Redis StatefulSet | `deployments/03-statefulset-redis/statefulset.yaml` |
| Network Policies | `deployments/06-network-policy/` |