# GitOps Flow with ArgoCD

This repo is designed as an ArgoCD GitOps target. When you commit changes to this repo, ArgoCD automatically applies them to your cluster.

## How It Works

```
Git (This Repo)  →  ArgoCD watches commits  →  ArgoCD applies manifests  →  Cluster
```

## Workflow

### 1. Make a Change

```bash
# Edit a manifest
vim deployments/01-deployment/deployment.yaml

# Commit and push
git add .
git commit -m "Update flask replicas to 3"
git push origin main
```

### 2. ArgoCD Syncs Automatically

If your ArgoCD application is configured with `Sync Policy: Automatic`:

- ArgoCD detects the new commit
- Compares Git state with cluster state
- Applies the diff
- Updates health status

### 3. Monitor

```bash
# Check sync status
argocd app get k8splay

# View events
argocd app events k8splay

# Check health
argocd app get k8splay --health
```

## Manual Sync

If sync policy is `Manual`:

```bash
# Sync via CLI
argocd app sync k8splay

# Sync via UI
# ArgoCD UI → App → Sync button

# Force sync (override conflicts)
argocd app sync k8splay --force
```

## ArgoCD Application Structure

```
ArgoCD App Name: "k8splay"
├── Sync Policy:  Automated
├── Repository:   https://github.com/surjit7/k8splay.git
├── Path:         deployments/01-deployment
├── Namespace:    default
├── Self-Heal:    true  (revert manual changes)
└── Prune:        true  (delete orphaned resources)
```

## Best Practices

| Practice | Reason |
|-- --------|--|
| **Small commits** | Easier to rollback and debug |
| **One lab per PR** | Isolates changes |
| **Test with kubectl first** | Before trusting ArgoCD |
| **Enable self-heal** | Keep cluster in sync with Git |
| **Use namespaces** | Isolate labs (default, dev, staging) |
| **Tag releases** | Track which manifest version deploys what |

## Rollback

```bash
# Rollback via CLI
argocd app rollback k8splay

# Rollback via UI
# ArgoCD UI → App → Rollback → select revision → Rollback
```

## Troubleshooting

### Manifests not applied

```bash
# Check ArgoCD logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller -f

# Force refresh
argocd app sync k8splay --refresh
```

### Drift detection (cluster differs from Git)

```bash
# See what's different
argocd app diff k8splay

# Re-sync to Git state
argocd app sync k8splay --prune --force
```

### ArgoCD can't reach the repo

```bash
# Add SSH/HTTPS credentials to ArgoCD
argocd repo add https://github.com/surjit7/k8splay.git \
  --name k8splay \
  --enable-oci-scanning