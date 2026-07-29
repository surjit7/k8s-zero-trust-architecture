# Installing ArgoCD

ArgoCD is a GitOps continuous deployment tool that synchronizes your cluster state with your Git repository. In this repo, ArgoCD watches commits and automatically applies manifests.

## Install ArgoCD

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Verify installation
kubectl get pods -n argocd
```

## Access ArgoCD UI

### Via Port-Forward (Quick)

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Open https://localhost:8080 in browser
# Ignore the TLS warning (self-signed cert)
```

### Via Ingress (Permanent)

See [Lab 03](../deployments/03-ingress/) for the ArgoCD Ingress manifest (`argocd-ingress.yaml`).

## Login

```bash
# Get the admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Login via CLI
argocd login localhost:8080 --insecure --username admin --password <password>
```

## Configure ArgoCD to Watch This Repo

### Via UI

1. Open ArgoCD UI
2. Click **New App**
3. Fill in:
   - **Name:** `k8splay`
   - **Project:** `default`
   - **Sync Policy:** `Automatic`
   - **Repository URL:** `https://github.com/surjit7/k8splay.git` (or your fork)
   - **Revision:** `main`
   - **Path:** `deployments/01-deployment` (or any lab path)
   - **Destination Server:** `https://kubernetes.default.svc`
4. Click **Create**

### Via CLI

```bash
argocd app create k8splay \
  --repo https://github.com/surjit7/k8splay.git \
  --path deployments/01-deployment \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace default \
  --sync-policy automated \
  --self-heal \
  --prune
```

## ArgoCD Concepts

| Concept | Description |
|-- --------|--|
| **Application** | A mapping of Git path to a cluster namespace |
| **Repo** | Git repository containing manifests |
| **Sync Policy** | `Manual` (approve manually) or `Automatic` (auto-sync) |
| **Self-Heal** | ArgoCD reverts cluster to Git state if manually changed |
| **Prune** | Delete resources in cluster that are not in Git |
| **Health Status** | ArgoCD evaluates if the app is `Healthy`, `Progressing`, or `Degraded` |

## Useful ArgoCD Commands

| Command | Purpose |
|-- -------|--|
| `argocd app list` | List all applications |
| `argocd app get <name>` | Get app details |
| `argocd app sync <name>` | Force sync |
| `argocd app rollback <name>` | Rollback to previous revision |
| `argocd app diff <name>` | Show cluster vs Git diff |

## Troubleshooting

### App stuck in `Progressing`

```bash
# Check events
kubectl get events -n argocd --sort-by=.lastTimestamp

# Check ArgoCD logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller -f
```

### Sync failed

```bash
# Check app events
argocd app events <name>

# Manual sync
argocd app sync <name> --force
```

### ArgoCD UI not accessible

```bash
# Check if ingress addon is enabled
minikube addons list

# Check ArgoCD server pod
kubectl get pods -n argocd -l app.kubernetes.io/name=argocd-server