# Lab 03: Ingress + TLS + Host Routing

## Concept

An **Ingress** acts as a Layer 7 load balancer — routing HTTP traffic to Services based on hostname and path. TLS termination happens at the Ingress controller.

This lab covers:
- Creating an Ingress that routes by hostname (`myapp.com` → flask-app, `mysecondapp.com` → second-app)
- Adding TLS to encrypt traffic
- Configuring the Ingress Controller (nginx) with a ConfigMap
- **ArgoCD Ingress** — exposing the GitOps management UI through the same Ingress

### Why ArgoCD Ingress is in this folder (not a separate lab)

Both are **Ingress resources** managed by the same nginx controller — they share:
- **One TLS secret** (`my-tls-secret`) — no need to duplicate certificates
- **One Ingress-nginx Controller** in the `ingress-nginx` namespace
- **One set of DNS entries** resolved to the same Minikube IP

They differ in **purpose**:
| | App Ingress (`ingress.yaml`) | ArgoCD Ingress (`argocd-ingress.yaml`) |
|---|---|---|
| **Routes to** | Your application pods | ArgoCD management UI |
| **Namespace** | `default` | `argocd` |
| **Backend protocol** | HTTP | HTTPS (ArgoCD requirement) |
| **Domain** | `myapp.com`, `mysecondapp.com` | `argocd.myapp.com` |

They share the same Ingress Controller, so they live together — but each has its own manifest file for clean separation.

## Manifests

| File | Purpose |
|------|-------|
| `ingress.yaml` | Host-based routing + TLS for `myapp.com` and `mysecondapp.com` |
| `ingress-config.yaml` | ConfigMap for nginx Ingress Controller (Brotli, proxy protocol) |
| `argocd-ingress.yaml` | Ingress for ArgoCD UI at `argocd.myapp.com` (HTTPS backend) |

## Prerequisites

Before applying this lab:
1. Ingress-nginx controller must be installed in Minikube
   ```bash
   minikube addons enable ingress
   ```
2. TLS secret must exist (create certs from Lab 06)
3. DNS must resolve all domains to Minikube's IP (add to `/etc/hosts`)

## How to Apply

```bash
# 1. Create TLS secret (replace with your actual cert paths)
kubectl create secret tls my-tls-secret \
  --cert=./server.crt \
  --key=./server.key \
  --dry-run=client -o yaml | kubectl apply -f -

# 2. Apply Ingress config (nginx controller settings)
kubectl apply -f ingress-config.yaml

# 3. Apply application Ingress rules
kubectl apply -f ingress.yaml

# 4. Apply ArgoCD Ingress rules (separate namespace, separate host)
kubectl apply -f argocd-ingress.yaml

# 5. Check
kubectl get ingress
kubectl get ingress -n argocd
```

## Access

```bash
# Add to /etc/hosts (Linux/Mac):
<minikube-ip>  myapp.com
<minikube-ip>  mysecondapp.com
<minikube-ip>  argocd.myapp.com

# Application access via HTTPS:
curl https://myapp.com -k
curl https://mysecondapp.com -k

# ArgoCD UI:
# Open https://argocd.myapp.com in browser
```

## How to Clean Up

```bash
kubectl delete -f ingress.yaml
kubectl delete -f argocd-ingress.yaml
kubectl delete -f ingress-config.yaml
kubectl delete secret my-tls-secret
```

## Revisiting This Lab

- Change `rewrite-target` annotation to `/index.html`
- Add a new host rule for a third app
- Test with HTTP vs HTTPS to see TLS enforcement
- Remove the ArgoCD Ingress and observe it becomes unreachable
- Add path-based routing (`/argo`) alongside host-based routing