# Enterprise Zero-Trust Kubernetes Architecture Reference

> A comprehensive reference implementation demonstrating a secure, zero-trust Kubernetes architecture. This repository serves as a guide through the layers of modern application infrastructure — from hardened containers up through TLS termination, eBPF-accelerated networking, and GitOps-driven deployment.

---

## 🧭 Architectural Overview

This architecture enforces zero-trust principles by asserting that no entity is implicitly trusted. Every network hop, inter-service communication, and client request must be strictly verified, authenticated, and authorized.

> **Core Thesis**: Modern infrastructure is not a perimeter — it's a **chain of trust**. Every hop between pod, service, and external client must be verified, encrypted, and auditable.

| Module | Topic | Layer | Key Capabilities Demonstrated |
|-----|-----|-----|-----|
| [01-deployment](deployments/01-deployment/) | L4 Deployments & Services | L4 | PSS compliance, Rolling updates, replica management, ClusterIP internals |
| [02-second-app](deployments/02-second-app/) | Multi-App Ingress Routing | L7 | Advanced host-based Ingress routing |
| [03-statefulset-redis](deployments/03-statefulset-redis/) | StatefulSets & Headless Services | L4 | Stable network identity for stateful workloads with strict security contexts |
| [04-ingress](deployments/04-ingress/) | Ingress + TLS + ArgoCD | L7 + L6 | Host-based routing, TLS termination, GitOps management |
| [05-troubleshooting](deployments/05-troubleshooting-netshoot/) | Interactive Netshoot & Observability | L3-L7 | Debugging DNS, TCP, and visualizing eBPF drops via Hubble |
| [06-network-policy](deployments/06-network-policy/) | Zero Trust Networking | L3-L4 | eBPF Pod-level firewall — strict ingress/egress isolation |
| [07-tls-certs](deployments/07-tls-certs/) | TLS PKI Foundation | L6 | Self-signed CA → server cert → client cert (mTLS prep) |

| **Table of Contents** | Section |
|------|------|
| 🧭 [Architectural Overview](#-architectural-overview) | Lab overview & architecture |
| 🏗️ [Load Balancing Chain](#-where-the-load-balancer-fits) | L4 to L7 traffic flow |
| 🚫 [Zero Trust Model](#-zero-trust-network-model) | Trust boundaries, enforcement chain, PKI |
| ⚙️ [Kubernetes Integration](#-kubernetes-integration) | Control plane, component mapping, flow |
| 🚀 [Getting Started](#-getting-started) | Prerequisites & setup |
| 🔄 [Deployment Workflow](#-deployment-workflow) | Operational loop |

### 🏗️ Where the Load Balancer Fits

> Load balancing is **not a single construct** — it is a chain of responsibility distributed across network layers.

```text
              ┌───────────────────────────────────────────────────────┐
              │                    CLIENT (Browser)                   │
              │  HTTPS://myapp.com:443                                │
              └───────────────────────┬───────────────────────────────┘
                                      │
                                      │ ① DNS: myapp.com → public IP
                                      │ ② TCP: SYN/ACK
                                      │ ③ TLS: ClientHello → ServerHello
                                      ▼
       ┌───────────────────────────────────────────────────────────────────┐
       │                  CLOUD/EXTERNAL L4 LOAD BALANCER                  │
       │  (AWS CLB/NLB, Azure LB, or Minikube's auto-provisioned Service)  │
       │                                                                   │
       │  Routes on: IP + Port ONLY (Layer 4)                              │
       │  • No HTTP awareness — just forwards raw TCP                      │
       │  • Health checks at TCP level                                     │
       │  • Single entry point → distributes to Ingress pods               │
       │                                                                   │
       │  ┌─────────┐  ┌─────────┐  ┌─────────┐                            │
       │  │ Ingress │  │ Ingress │  │ Ingress │ ← TCP round-robin          │
       │  │  Pod    │  │  Pod    │  │  Pod    │                            │
       │  └────┬────┘  └────┬────┘  └────┬────┘                            │
       └───────┼────────────┼────────────┼─────────────────────────────────┘
               │            │            │
               │ TCP        │ TCP        │ TCP
               ▼            ▼            ▼
      ┌────────────────────────────────────────────────────────────────────┐
      │                   NGINX INGRESS CONTROLLER (L7)                    │
      │  • TLS termination (decrypts → HTTP)                               │
      │  • Host-based routing (myapp.com → flask-app)                      │
      │  • Path-based routing (/api → api-service)                         │
      │  • Header inspection, rate limiting, compression                   │
      └────────────────────┬───────────────────────────────────────────────┘
                           │ HTTP (inside cluster)
                           ▼
      ┌────────────────────────────────────────────────────────────────────┐
      │               KUBERNETES SERVICE (ClusterIP) — L4 LB               │
      │  • Routes on: Service ClusterIP + Port                             │
      │  • Round-robin across pod IPs                                      │
      │  • Endpoints discovery via Cilium (eBPF)                           │
      └────────────────────┬───────────────────────────────────────────────┘
                           │ TCP
                           ▼
              ┌──────────────────────────────────────────────┐
              │                  Backend Pod                 │
              │  • Flask API: app.py on port 5001            │
              │  • Redis: port 6379                          │
              │  • Processes HTTP/Redis protocol             │
              └──────────────────────────────────────────────┘
```

### Why This Chain Exists

| Layer | Load Balancer Type | Purpose |
|-------|-------------------|---------|
| **L4 (External)** | Cloud CLB/NLB or Minikube LoadBalancer Service | Single IP → cluster, TCP health checks, cross-zone distribution |
| **L7 (Ingress)** | NGINX Ingress Controller | Smart routing by Host/Path/Headers, TLS termination |
| **L4 (Internal)** | Kubernetes ClusterIP Service | Distribute HTTP traffic to healthy pods via eBPF |

**Key Insight**: Each layer addresses **distinct concerns**. Enterprise production environments require all three:
1. **L4 external LB** → Provides public IP ingress and edge TCP health checks.
2. **L7 Ingress** → Evaluates HTTP traffic, enforces TLS, and routes intelligently.
3. **L4 Service** → Distributes traffic within the cluster securely.

---

## 🚀 Getting Started

### Prerequisites

| Tool | Purpose |
|------|-----|
| [Minikube](https://minikube.sigs.k8s.io/) | Local Kubernetes cluster environment |
| [Docker](https://www.docker.com/) | Container image construction |
| [kubectl](https://kubernetes.io/docs/reference/kubectl/) | Cluster control plane interaction |
| [ArgoCD](https://argo-cd.readthedocs.io/) | GitOps continuous delivery controller |
| [Cilium](https://cilium.io/) | eBPF networking fabric (L4 routing, L3-L4 isolation) |

> **💡 Architectural Note:** Cilium completely replaces `kube-proxy` for **L4 load balancing**. It provides high-performance **L3-L4 NetworkPolicies** directly at the kernel level via eBPF, bypassing the limitations of iptables.

### Initialization

```bash
# 1. Provision Minikube with Cilium (eBPF mode, bypassing kube-proxy)
minikube start \
  --network-plugin=cni \
  --cni=false \
  --extra-config=kubeadm.skip-phases=addon/kube-proxy \
  --nodes 3 \
  --cpus 2 \
  --memory 6144

# 2. Deploy the Cilium CNI
cilium install --set kubeProxyReplacement=true

# 3. Verify Cilium health
cilium status --wait

# 4. Enable Ingress
minikube addons enable ingress

# 5. Bootstrap GitOps (ArgoCD)
kubectl create namespace argocd
kubectl apply -n argocd \
  --server-side \
  --force-conflicts \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 6. Access ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8001:443

# 7. Retrieve initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d; echo
```

---

## 🔒 TLS & PKI Setup

Before the Ingress controller can terminate TLS, cryptographic material is required. This module generates a self-signed PKI chain and provisions a Kubernetes `Secret`.

```bash
# Generate certs (see deployments/07-tls-certs/ for full instructions)
openssl req -new -x509 -days 365 -nodes \
  -out ca.crt -keyout ca.key -subj "/CN=InternalCA"

openssl req -new -nodes -out server.csr -keyout server.key \
  -subj "/CN=myapp.com" \
  -addext "subjectAltName=DNS:myapp.com,DNS:*.myapp.com"

openssl x509 -req -days 365 -in server.csr \
  -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt

# Create the TLS Secret
kubectl create secret tls my-tls-secret \
  --cert=server.crt \
  --key=server.key \
  --namespace=argocd
```

---

## 📖 Technical Capabilities Covered

| Component | Enterprise Implementation |
|---------|-----|
| ✅ **Deployments** | Hardened SecurityContexts, Liveness/Readiness probes, strict resource constraints. |
| ✅ **Services** | `ClusterIP` and `Headless` exclusive internal routing (No direct NodePorts). |
| ✅ **StatefulSets** | Stable network identity for persistent workloads (Redis) with non-root execution. |
| ✅ **Ingress** | TLS 1.3 termination, host-based routing, edge protection. |
| ✅ **NetworkPolicies** | eBPF-enforced pod-level firewall — default-deny ingress/egress isolation. |
| ✅ **ArgoCD** | GitOps continuous deployment preventing configuration drift. |
| ✅ **Cilium** | High-performance eBPF replacement for kube-proxy. |

---

## 🌐 Documentation References

| Doc | Topic |
|-----|-----|
| [Request Flow](docs/05-request-flow.md) | Browser → Ingress → Service → Pod → Redis tracing |
| [TCP & OSI Model](docs/06-tcp-osi.md) | Network layer mapping and TCP handshake lifecycle |
| [TLS Explained](docs/07-tls.md) | Cryptographic handshake and termination patterns |
| [L4 vs L7 Load Balancing](docs/08-load-balancer.md) | Services (L4) vs Ingress (L7) architectural differences |
| [NGINX L4 Stream Proxy](docs/09-nginx-l4-stream-proxy.md) | Proxy protocol and TCP pass-through requirements |

---

## 🏗️ System Architecture

```text
                      ┌────────────────┐
                      │   Ingress      │
                      │ (TLS + Routing)│
                      └──────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
       myapp.com         mysecondapp.com  argocd.myapp.com
              │              │              │
       ┌───┬──┴──────┐ ┌─────┴──────┐ ┌─────┴──────┐
       │  flask-app  │ │ second-app │ │  ArgoCD UI │
       │  (ClusterIP)│ │ (ClusterIP)│ │  (GitOps)  │
       └───┬─────────┘ └──────┬─────┘ └─────┬──────┘
           │                               
       ┌───┴─────────────┐
       │   Redis         │
       │(StatefulSet)    │
       │(NetPol + Cilium)│
       └─────────────────┘
```

---

## 📁 Repository Structure

```text
k8s-zero-trust-architecture/
├── README.md                ← You are here
├── apps/
│   ├── flask-app/           ← Enterprise Flask API + Hardened Dockerfile
│   └── second-app/          ← Supplemental Application Source
├── deployments/             ← Declarative Kubernetes Manifests
│   ├── 01-deployment/       # L4 Deployments, Services, SecurityContexts
│   ├── 02-second-app/
│   ├── 03-statefulset-redis/# Stateful Layer Definitions
│   ├── 04-ingress/          # L7 Routing & Ingress Configuration
│   ├── 05-troubleshooting-netshoot/ # Interactive Netshoot & Hubble Debugging Lab
│   ├── 06-network-policy/   # Zero-Trust Egress/Ingress Policies
│   └── 07-tls-certs/        # PKI and Certificate Management
└── docs/                    ← Detailed Architecture Documentation
```

---

## 🔄 Deployment Workflow

The deployment lifecycle is structured for iterative validation:

```bash
# 1. Provision cluster (Initial setup)
minikube start --network-plugin=cni --cni=cilium

# 2. Build & publish hardened image
docker build -t flask-app:v1 -f apps/flask-app/Dockerfile apps/flask-app/
minikube image load flask-app:v1

# 3. Apply declarative state
kubectl apply -f deployments/01-deployment/

# 4. Validate infrastructure
kubectl get pods,svc,ingress -o wide

# 5. Teardown
kubectl delete -f deployments/01-deployment/
```

---

## 🛡️ Security Posture

- **Internal Abstraction**: Workloads utilize **ClusterIP** or **Headless** services exclusively.
- **Controlled Ingress**: External access is strictly mediated by the Ingress controller with enforced TLS termination.
- **Micro-Segmentation**: **NetworkPolicies** mandate a default-deny zero-trust model at the workload level.
- **eBPF Enforcement**: **Cilium** delivers observable, kernel-level packet enforcement, bypassing iptables for superior performance and security.
- **Pod Security Standards (PSS)**: Applications run as unprivileged, non-root users (`uid: 10001`) with read-only filesystems and explicitly dropped capabilities.

---

## 🚫 Zero Trust Network Model

Modern infrastructure demands the deprecation of perimeter-based defenses. This architecture implements **zero-trust** at every network tier: all connections are untrusted by default and mandate verification.

### Core Tenet

> **Never trust. Always verify.** Every workload, service, and external actor is classified as hostile until explicitly authenticated and authorized.

| Boundary | Enforcement Mechanism | OSI Layer | Technology |
| :--- | :--- | :--- | :--- |
| **External to Cluster** | L4 Firewall / Load Balancer | L4 | Cloud Provider LB |
| **Edge to Ingress** | TLS 1.3, Strict SNI Matching | L7 | NGINX Ingress |
| **Ingress to Workload** | Host/Path Routing, WAF Rules | L7 | NGINX Rules |
| **Inter-Workload** | Label-based allowlists, Protocol/Port restriction | L3 / L4 | K8s NetworkPolicy (Cilium) |
| **Egress (Outbound)** | FQDN/CIDR filtering | L3 / L4 | Cilium Egress Policies |
| **Container Runtime** | Dropped Capabilities, Seccomp profiles | L7 (Kernel) | Pod Security Standards |

### Enforcement Chain Sequence

1. **Default Deny**: Cilium's eBPF drops all traffic lacking explicit permission.
2. **Ingress Authorization**: NetworkPolicies restrict traffic to application pods exclusively from the Ingress controller.
3. **Egress Allow-listing**: Application pods are constrained to reach only authorized backend data stores (e.g., Redis).
4. **Cryptographic Assertion**: The Ingress mandates valid TLS presentation from the client.
5. **PKI Verification**: Lab `07-tls-certs` provisions the required CA material for future Mutual TLS (mTLS) integration.

---

## ⚙️ Kubernetes Integration

Kubernetes provides the orchestration fabric binding these advanced patterns together. This architecture demonstrates how disparate primitives chain to form a cohesive, enterprise-grade platform.

### Component Mapping

| Primitive | Role within Architecture | Enterprise Justification |
|-------|---------|------|
| **Deployment** | Stateless API Workloads | Ensures high availability via RollingUpdates and PodDisruptionBudgets |
| **Service (ClusterIP)** | Internal L4 Load Balancing | Abstracts pod volatility behind stable virtual IPs |
| **Headless Service** | StatefulSet Identity | Enables direct pod addressability required by clustered datastores |
| **StatefulSet** | Persistent Workloads | Guarantees ordered provisioning and stable network identity |
| **Ingress** | L7 Edge Proxy | Consolidates TLS termination and intelligent routing |
| **NetworkPolicy** | Workload Micro-firewall | Enforces zero-trust isolation at OSI Layers 3 & 4 |
| **Cilium (eBPF)** | Datapath & Networking | Replaces kube-proxy for accelerated throughput and advanced observability |

### Reconciliation Flow

```text
1. Infrastructure Engineer commits to Git Repository
         │
2. ArgoCD detects configuration drift and reconciles API Server state
         │
3. Kubernetes Scheduler allocates Pods to Nodes based on Resource Requests
         │
4. Cilium (eBPF) injects packet forwarding rules into Kernel
         │
5. NGINX Ingress provisions L7 routing paths
         │
6. L4 Services establish ClusterIP endpoints
         │
7. NetworkPolicies engage to isolate and protect workloads
         │
8. Traffic path is secured: Client → LB → Ingress → Service → Pod
```