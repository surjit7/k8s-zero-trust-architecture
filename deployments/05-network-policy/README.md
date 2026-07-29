# Lab 05: NetworkPolicies (Ingress + Egress)

## Concept

**NetworkPolicies** are Kubernetes' equivalent of a firewall — they control what traffic is allowed between Pods at the IP/port level. By default, all Pods can communicate. A NetworkPolicy can lock this down to **zero-trust** — allowing only explicitly permitted traffic.

This lab covers:
- **Ingress Policy** — Restrict Redis to only accept connections from the Flask app
- **Egress Policy** — Restrict Flask to only connect to Redis and DNS

## Manifests

| File | Purpose |
|------|---------|
| `networking-policy-myapp.yaml` | Ingress Policy: Redis only accepts from Flask app on port 6379 |
| `network-flask-app.yaml` | Egress Policy: Flask app can only reach Redis and DNS |

## How to Apply

```bash
# Apply both policies (order doesn't matter)
kubectl apply -f networking-policy-myapp.yaml  # Redis ingress rules
kubectl apply -f network-flask-app.yaml         # Flask egress rules

# Check policies
kubectl get networkpolicies
```

## What This Blocks

| Scenario | Before Policy | After Policy |
|----------|---------------|-------------|
| Pod A → Redis | ✅ Allowed | ❌ Blocked |
| Flask → Redis | ✅ Allowed | ✅ Allowed |
| Flask → Google DNS | ✅ Allowed | ✅ Allowed |
| Flask → any other pod | ✅ Allowed | ❌ Blocked |

## How to Clean Up

```bash
kubectl delete -f networking-policy-myapp.yaml
kubectl delete -f network-flask-app.yaml
```

## Revisiting This Lab

- Delete the DNS egress rule and watch Flask Pods fail to connect to Redis
- Add a new `app: nginx` to the Redis ingress policy and test that it's allowed
- Run `kubectl describe networkpolicy` to see effective rules