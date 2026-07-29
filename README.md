# k8splay 🧪

> Kubernetes, but make it fun. A hands-on playground where networking, security, and GitOps collide — and actually make sense.

---

## 🧭 What's Inside

This repo is a **guided journey** through the layers that hold modern apps together — from raw containers up through TLS termination, zero-trust networking, and GitOps-driven deployment. Each lab stands alone, but together they paint the full picture.

| Lab | Topic | What You'll Walk Away With |
|-----|------|------|
| [01-deployment](deployments/01-deployment/) | Deployments + Services | Rolling updates, replica management, ClusterIP internals |
| [02-second-app](deployments/02-second-app/) | Multi-App Ingress Routing | Serving two apps on one Ingress controller |
| [03-statefulset-redis](deployments/03-statefulset-redis/) | StatefulSets + Headless Services | Stable network identity for stateful workloads |
| [04-ingress](deployments/04-ingress/) | Ingress + TLS + ArgoCD | Host-based routing, TLS termination, GitOps management |
| [06-network-policy](deployments/06-network-policy/) | NetworkPolicies | Pod-level firewall rules (zero-trust networking) |
| [07-tls-certs](deployments/07-tls-certs/) | TLS Certificate Generation | Self-signed PKI: CA → server cert → client cert |

### Apps

| App | What It Does |
|-----|-|
| [flask-app](apps/flask-app/) | Flask web app backed by Redis — your canary for everything |
| [second-app](apps/second-app/) | Second Flask app — forces real host-based Ingress routing |

---

## 🚀 Getting Started

### Prerequisites

| Tool | Why You Need It |
|------|-|
| [Minikube](https://minikube.sigs.k8s.io/) | Your local Kubernetes cluster |
| [Docker](https://www.docker.com/) | Build & load container images |
| [kubectl](https://kubernetes.io/docs/reference/kubectl/) | Talk to the cluster |
| [ArgoCD](https://argo-cd.readthedocs.io/) | GitOps — because `kubectl apply` doesn't scale |
| [Cilium](https://cilium.io/) | eBPF-powered networking & security (replaces kube-proxy) |

### One-Time Setup

> **TL;DR** — spin up the cluster with Cilium, install ArgoCD, and you're in business.

```bash
# 1. Start Minikube with Cilium (eBPF, no kube-proxy)
minikube start \
  --network-plugin=cni \
  --cni=cilium \
  --extra-config=kubeadm.skip-phases=addon/kube-proxy

# 2. Verify Cilium is healthy
cilium status --wait

# 3. Enable the Ingress addon
minikube addons enable ingress

# 4. Create ArgoCD namespace
kubectl create namespace argocd

# 5. Install ArgoCD (server-side apply to avoid conflicts)
kubectl apply -n argocd \
  --server-side \
  --force-conflicts \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 6. Port-forward to ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8001:443

# 7. Get the initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d; echo
```

Head to **<https://localhost:8001>** and log in. The password is the one you just extracted.

---

## 🔒 TLS Setup

Before the Ingress can terminate TLS, you need a certificate. This lab generates a self-signed PKI chain and creates a Kubernetes `Secret` from it.

```bash
# Generate certs (see deployments/07-tls-certs/ for full instructions)
openssl req -new -x509 -days 365 -nodes \
  -out ca.crt -keyout ca.key -subj "/CN=MyLocalCA"

openssl req -new -nodes -out server.csr -keyout server.key \
  -subj "/CN=myapp.com" \
  -addext "subjectAltName=DNS:myapp.com,DNS:*.myapp.com"

openssl x509 -req -days 365 -in server.csr \
  -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt

kubectl create secret tls my-tls-secret \
  --cert=server.crt \
  --key=server.key \
  --namespace=argocd
```

---

## 📖 Concepts Covered

| Concept | What It Solves |
|---------|-|
| ✅ **Deployments** | Rolling updates, replica management |
| ✅ **Services** | ClusterIP + Headless — all internal, no NodePorts |
| ✅ **StatefulSets** | Stable identity for stateful workloads (Redis) |
| ✅ **Ingress** | HTTP routing, TLS termination, multi-host |
| ✅ **NetworkPolicies** | Pod-level firewall — ingress + egress isolation |
| ✅ **ArgoCD** | GitOps continuous deployment |
| ✅ **Cilium** | eBPF networking — fast, observable, secure |
| ✅ **Docker** | Containerizing Python apps |
| ✅ **TLS/Certs** | Self-signed CA, server, and client certificates |

---

## 🌐 Networking Docs

These explain the *why* behind the *what*.

| Doc | Topic |
|-----|-|
| [Request Flow](docs/05-request-flow.md) | Browser → Ingress → Service → Pod → Redis — full trace |
| [TCP & OSI Model](docs/06-tcp-osi.md) | All 7 layers, TCP handshake, K8s mapping |
| [TLS Explained](docs/07-tls.md) | Handshake, our cert setup, termination vs passthrough |
| [L4 vs L7 Load Balancing](docs/08-load-balancer.md) | Services (L4) vs Ingress (L7), cloud comparison |

---

## 🏗️ Architecture

```
                      ┌──────────────┐
                      │   Ingress    │
                      │ (TLS + Routing)│
                      └──────┬───────┘
                             │
              ┌──────────────┼──────────────┐
              │              │               │
       myapp.com         mysecondapp.com  argocd.myapp.com
              │              │               │
       ┌───┬──┴──────┐ ┌───┴──────┐ ┌───┴───────┐
       │  flask-app   │ │ second-app │ │  ArgoCD UI │
       │  (ClusterIP) │ │ (ClusterIP)│ │  (GitOps)  │
       └───┬──────┘  └──────┬──────┘ └─────┬───────┘
           │               │               │
       ┌───┴──────┐
       │   Redis  │
       │ (StatefulSet)│
       │ (NetPol + Cilium)│
       └──────────┘
```

---

## 📁 Directory Layout

```
k8splay/
├── README.md                ← You are here
├── apps/
│   ├── flask-app/           ← Flask + Redis source + Dockerfile
│   └── second-app/          ← Second app source + Dockerfile
├── deployments/             ← K8s manifests by concept
│   ├── 01-deployment/
│   ├── 02-second-app/
│   ├── 03-statefulset-redis/
│   ├── 04-ingress/          ← App Ingress + ArgoCD Ingress
│   ├── 06-network-policy/
│   └── 07-tls-certs/
└── docs/                    ← Setup & theory guides
    ├── 01-install-minikube.md
    ├── 02-install-argocd.md
    ├── 03-docker-build.md
    ├── 04-gitops-flow.md
    ├── 05-request-flow.md
    ├── 06-tcp-osi.md
    ├── 07-tls.md
    └── 08-load-balancer.md
```

---

## 🔄 Rehearsal Workflow

Each lab is designed to be revisited in isolation. Here's the loop:

```bash
# 1. Start cluster (first time only)
minikube start --network-plugin=cni --cni=cilium

# 2. Build & load image
docker build -t flask-app:v1 -f apps/flask-app/Dockerfile apps/flask-app/
minikube image load flask-app:v1

# 3. Apply a lab
kubectl apply -f deployments/01-deployment/

# 4. Inspect
kubectl get pods,svc,ingress -o wide

# 5. Clean up
kubectl delete -f deployments/01-deployment/
```

---

## 🛡️ Security Posture

- All services use **ClusterIP** or **Headless** — no services exposed to the outside
- External access flows **only** through the Ingress controller with TLS termination
- **NetworkPolicies** enforce zero-trust at the pod level
- **Cilium** provides observable, eBPF-based enforcement — faster and more secure than iptables

---

## License

This is a personal learning repo. Use at your own risk. 🎓