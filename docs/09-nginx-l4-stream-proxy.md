# NGINX L4 Stream Proxy: The TCP Prerequisite

> **This is the prerequisite that comes BEFORE Kubernetes.**
>
> Before the Ingress controller can route HTTP traffic, someone needs to ensure TCP traffic can reach the Ingress pods. That's the job of the Layer 4 load balancer.

---

## The TCP Boundary: Where Layer 4 Ends

```
                        ┌─────────────────────┐
                        │      CLIENT         │
                        │  https://myapp.com  │
                        └───────┬─────────────┘
                                │
                  ┌─────────────▼──────────────┐
                  │   CLOUD L4 LOAD BALANCER   │
                  │  (AWS NLB / Azure LB / etc.)│
                  │                            │
                  │  Routes on: IP + Port      │
                  │  • No HTTP awareness       │
                  │  • TCP health checks       │
                  │  • Single public IP        │
                  └─────────────┬──────────────┘
                                │ TCP (port 443)
                  ┌─────────────▼──────────────┐
                  │   NGINX INGRESS PODS       │
                  │  (L7 — but receives TCP)   │
                  │  • TLS termination         │
                  │  • HTTP routing            │
                  └─────────────┬──────────────┘
                                │ HTTP
                  ┌─────────────▼──────────────┐
                  │   K8s SERVICE (L4)         │
                  │  • ClusterIP + Port        │
                  │  • Routes to pods          │
                  └─────────────┬──────────────┘
                                │ TCP
                  ┌─────────────▼──────────────┐
                  │    BACKEND PODS            │
                  │  • Flask, Redis, etc.      │
                  └────────────────────────────┘
```

### Key Takeaway

| Layer | Load Balancer Type | What It Routes On | Our Example |
|-------|------|----------|----------|
| **L4 (External)** | Cloud NLB / CLB | IP + Port (TCP) | Single public IP → Ingress pods |
| **L7 (Ingress)** | NGINX Ingress | Host, Path, Headers | `myapp.com` → flask-app-service |
| **L4 (Internal)** | K8s ClusterIP Service | Service ClusterIP + Port | flask-app-service → pods |

**The L4 load balancer (cloud or Minikube auto-provisioned) is the GATEWAY.** Without it, there's no public IP for the Ingress controller to listen on.

---

## Minikube's Auto-Provisioned L4 Load Balancer

When you run:

```bash
minikube addons enable ingress
```

Minikube creates:

1. **Ingress-nginx-controller** Deployment (pods with NGINX)
2. **Service of type `LoadBalancer`** — this is your L4 LB!

```yaml
apiVersion: v1
kind: Service
metadata:
  name: ingress-nginx-controller
  namespace: ingress-nginx
spec:
  type: LoadBalancer  # ← This is your L4 load balancer!
  selector:
    app.kubernetes.io/component: controller
  ports:
    - name: http
      port: 80
      targetPort: 80
    - name: https
      port: 443
      targetPort: 443
```

**Minikube magic:** The `LoadBalancer` service gets a ClusterIP that minikube exposes via `minikube tunnel` or your local IP.

---

## The NGINX Stream Block (For Reference)

While our cluster uses **HTTP routing** (Ingress), NGINX can also do **TCP proxying** via the `stream` block.

### NGINX HTTP Block (L7) vs Stream Block (L4)

| Feature | `http` Block | `stream` Block |
|---------|------|--------|
| **What it proxies** | HTTP/HTTPS | TCP/UDP |
| **Where to put it** | Inside `nginx.conf` | Outside `http { }` |
| **Our usage** | Used by Ingress controller | NOT used in our stack |
| **Use case** | Web apps, APIs | Redis, MySQL, custom TCP |

### Example: NGINX as TCP Proxy for Redis

```nginx
# This is NOT used in our cluster — just for reference
stream {
    upstream redis_backend {
        server redis-0.redis-headless.default.svc.cluster.local:6379;
    }

    server {
        listen 6379;  # ← TCP port, not HTTP
        proxy_pass redis_backend;
        proxy_timeout 1s;
        proxy_responses 1;
    }
}
```

### When Would You Use This?

| Use Case | Why Stream Block? |
|----------|------------------|
| **Non-HTTP services** | Redis, MySQL, custom TCP protocols |
| **TCP health checks** | Ingress only does HTTP health checks |
| **Single IP for multiple services** | One NLB entry point → multiple TCP services |
| **TCP load balancing** | Distribute TCP connections (not HTTP) |

---

## Cloud Provider Setup: The Missing Link

If you're not using Minikube, here's what you need to configure:

### AWS: Network Load Balancer (NLB) → Ingress Controller

```hcl
resource "aws_lb" "ingress_nlb" {
  name               = "ingress-nginx-nlb"
  internal           = false
  load_balancer_type = "network"
  availability_zones = ["us-east-1a", "us-east-1b"]

  # TCP listener on port 443
  listener {
    port               = 443
    protocol           = "TCP"
    load_balancer_arn  = aws_lb.ingress_nlb.arn
    default_action {
      type             = "forward"
      target_group_arn = aws_lb_target_group.ingress.arn
    }
  }

  # TCP listener on port 80
  listener {
    port               = 80
    protocol           = "TCP"
    load_balancer_arn  = aws_lb.ingress_nlb.arn
    default_action {
      type             = "forward"
      target_group_arn = aws_lb_target_group.ingress.arn
    }
  }
}
```

### Azure: Standard Load Balancer

```hcl
resource "azurerm_lb" "ingress_lb" {
  name                = "ingress-lb"
  location            = azurerm_resource_group.example.location
  resource_group_name = azurerm_resource_group.example.name
  sku                 = "Standard"
  frontend_ip_configuration {
    name                 = "publicIPAddress"
    public_ip_address_id = azurerm_public_ip.example.id
  }
}
```

### GCP: TCP Load Balancer

```hcl
resource "google_compute_global_address" "ingress_ip" {
  name       = "ingress-static-ip"
  address_type = "EXTERNAL"
}

resource "google_compute_target_tcp_proxy" "ingress" {
  name             = "ingress-tcp-proxy"
  target_tcp_proxy {
    backend_service = google_compute_region_backend_service.ingress.id
  }
}
```

---

## Proxy Protocol: Preserving Client IP

When traffic passes through an L4 load balancer, the **source IP is lost** — the pod sees the LB's IP, not the client's IP.

### The Problem

```
Client (1.2.3.4) → NLB (10.0.0.10) → Ingress Pod
                 IP source: 1.2.3.4
                 Becomes: 10.0.0.10 (NLB's IP)
```

### The Solution: Proxy Protocol

Enable **proxy protocol** on both the L4 LB and the Ingress controller:

```yaml
# In ingress-config.yaml (deployments/04-ingress/)
apiVersion: v1
kind: ConfigMap
metadata:
  name: ingress-nginx-controller
  namespace: ingress-nginx
data:
  use-proxy-protocol: "true"  # ← Tells Ingress to read proxy protocol
```

**Cloud LB setup:**
- **AWS NLB**: Enable proxy protocol on target group
- **Azure LB**: Use "Proxy Protocol" setting
- **GCP TCP LB**: Enable proxy protocol on backend service

---

## Summary: What You Need to Know

| Topic | What to Do |
|-------|-----------|
| **Minikube** | `minikube addons enable ingress` — creates L4 LB automatically |
| **Cloud (AWS/Azure/GCP)** | Create Network Load Balancer → point to Ingress pods on ports 80/443 |
| **Client IP preservation** | Enable proxy protocol on LB + set `use-proxy-protocol: "true"` |
| **TLS** | Either: Cloud LB terminates TLS, OR passes through to Ingress |
| **Health checks** | Cloud LB: TCP check on port 443/80 (not HTTP!) |

---

## Cross-References

| Resource | Location |
|----------|----------|
| Minikube setup | `docs/01-install-minikube.md` |
| Ingress config | `deployments/04-ingress/` |
| Request flow | `docs/05-request-flow.md` |
| TCP/OSI model | `docs/06-tcp-osi.md` |
| Load balancing overview | `docs/08-load-balancer.md` |