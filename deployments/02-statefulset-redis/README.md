# Lab 02: StatefulSet + Headless Service

## Concept

A **StatefulSet** manages stateful workloads with stable, unique network identities (e.g., `redis-0`, `redis-1`). Paired with a **Headless Service** (`clusterIP: None`), each Pod gets its own DNS entry.

This lab covers:
- Creating a Redis StatefulSet with a headless service
- Connecting to Redis via DNS: `redis-0.redis-headless.default.svc.cluster.local`
- Why StatefulSets matter (persistent identity, ordered deployment)

## Manifests

| File | Purpose |
|------|---------|
| `statefulset.yaml` | Redis StatefulSet (1 replica, redis:alpine) |
| `service.yaml` | Headless Service (clusterIP: None, port 6379) |

## How to Apply

```bash
# Deploy Redis StatefulSet + Headless Service
kubectl apply -f service.yaml
kubectl apply -f statefulset.yaml

# Check pods (they get stable names)
kubectl get pods
# Output: redis-0   1/1   Running

# Check headless service
kubectl get svc redis-headless
# Output: ClusterIP: None
```

## How to Connect from Flask App

The Flask app in Lab 01 connects to Redis using this DNS path:

```python
redis.Redis(
    host='redis-0.redis-headless.default.svc.cluster.local',
    port=6379
)
```

## How to Clean Up

```bash
kubectl delete -f service.yaml
kubectl delete -f statefulset.yaml
```

## Revisiting This Lab

- Add `replicas: 3` and observe `redis-0`, `redis-1`, `redis-2` being created
- Test DNS resolution inside another Pod: `nslookup redis-0.redis-headless.default.svc.cluster.local`