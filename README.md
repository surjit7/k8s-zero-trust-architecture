# k8splay 🧪

> A hands-on Kubernetes playground for learning and rehearsing core concepts.
> Runs locally with **Minikube** + deployed via **ArgoCD** (GitOps).

## What's Inside

| Lab | Topic | Description |
|-----|-------|-------------|
| [01-deployment](deployments/01-deployment/) | Deployments + Services | Rolling out replicas, ClusterIP-only access |
| [02-second-app](deployments/02-second-app/) | Second App Deployment | Multi-app Ingress routing with ClusterIP |
| [03-statefulset-redis](deployments/03-statefulset-redis/) | StatefulSet + Headless Service | Redis with stable network identity |
| [04-ingress](deployments/04-ingress/) | Ingress + TLS + Host Routing + ArgoCD | Routing multiple apps via domain names, TLS, and exposing ArgoCD management UI |
| [06-network-policy](deployments/06-network-policy/) | NetworkPolicies | Ingress and egress isolation (zero-trust networking) |
| [07-tls-certs](deployments/07-tls-certs/) | TLS Certificate Generation | Generating self-signed CA, server, and client certs |

## Apps

| App | Description |
|-----|-------------|
| [flask-app](apps/flask-app/) | Flask web app + Redis cache (Dockerized) |
| [second-app](apps/second-app/) | Second Flask app for multi-host Ingress routing |

## Getting Started

### Prerequisites

- **Minikube** — local Kubernetes cluster
- **Docker** — build container images
- **ArgoCD** — GitOps deployment (syncs from this repo)
- **kubectl** — interact with the cluster

### Quick Start

1. [Install Minikube](docs/01-install-minikube.md)
2. [Install ArgoCD](docs/02-install-argocd.md)
3. [Build Docker images](docs/03-docker-build.md)
4. Pick a lab from the table above and follow the README in that folder

## Concepts Covered

- ✅ **Deployments** — Rolling updates, replica management
- ✅ **Services** — ClusterIP, headless (all internal, no NodePort)
- ✅ **StatefulSets** — Persistent identity for Redis
- ✅ **Ingress** — HTTP routing, TLS termination, multi-host
- ✅ **NetworkPolicies** — Pod-level firewall rules (ingress + egress)
- ✅ **ArgoCD** — GitOps continuous deployment
- ✅ **Docker** — Containerizing Python apps
- ✅ **TLS/Certs** — Self-signed CA, server, and client certificates

## Architecture

```
                    ┌───────────┐
                    │   Ingress  │
                    │ (TLS + Routing) │
                    └─────┬─────┘
                          │
            ┌─────────────┼──────────────┐
            │             │              │
     myapp.com       mysecondapp.com  argocd.myapp.com
            │             │              │
     ┌──────┴───────┐ ┌──┴────────┐ ┌──┴───────┐
     │ flask-app    │ │ second-app │ │ ArgoCD   │
     │ (ClusterIP) │ │ (ClusterIP) │ │ UI        │
     └──────┬───────┘ └───────────┘ └──────────┘
            │
     ┌──────┴───────┐
     │   Redis      │
     │ (StatefulSet)│
     │ (NetworkPol) │
     └──────────────┘
```

## Directory Layout

```
k8splay/
├── README.md              ← You are here
├── apps/
│   ├── flask-app/         ← Flask app source + Dockerfile
│   └── second-app/        ← Second app source + Dockerfile
├── deployments/           ← K8s manifests, organized by concept
│   ├── 01-deployment/
│   ├── 02-second-app/
│   ├── 03-statefulset-redis/
│   ├── 04-ingress/        ← App Ingress + ArgoCD Ingress (same controller)
│   ├── 06-network-policy/
│   └── 07-tls-certs/
└── docs/                  ← Installation & setup guides
    ├── 01-install-minikube.md
    ├── 02-install-argocd.md
    ├── 03-docker-build.md
    └── 04-gitops-flow.md
```

## Rehearsal Workflow

Each lab is designed to be revisited independently:

```bash
# 1. Start local cluster
minikube start

# 2. Build & load Docker images
docker build -t my-app:v5 -f apps/flask-app/Dockerfile apps/flask-app/
minikube image load my-app:v5

# 3. Apply a lab
kubectl apply -f deployments/01-deployment/

# 4. Clean up
kubectl delete -f deployments/01-deployment/
```

## Security Posture

All services use **ClusterIP** or **Headless** types — no services are exposed directly to the outside world. External access flows exclusively through the Ingress controller with TLS termination, following a least-privilege networking approach.

## License

This is a personal learning repo. Use at your own risk. 🎓