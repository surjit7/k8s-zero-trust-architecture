# Lab 02: Second App Deployment

## Concept

Deploying a second Flask application alongside the first — the same pattern scaled to multiple services. Each app gets its own Deployment + ClusterIP Service, and the Ingress routes between them by hostname.

This lab covers:
- Creating a Deployment for a second service
- Exposing it via **ClusterIP** (internal-only, accessed through Ingress)
- Ingress host-based routing to differentiate between apps

## Manifests

| File | Purpose |
|------|---------|
| `deployment.yaml` | Second app Deployment (1 replica, port 5001) |
| `service.yaml` | ClusterIP Service routing to port 5001 (internal-only) |

## How to Apply

```bash
# Build and load the image
docker build -t second-app:v1 -f ../../apps/second-app/Dockerfile ../../apps/second-app/
minikube image load second-app:v1

# Deploy
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml

# Check it
kubectl get pods
kubectl get svc
```

## How to Clean Up

```bash
kubectl delete -f service.yaml
kubectl delete -f deployment.yaml
```

## Revisiting This Lab

- Change `replicas: 1` to `replicas: 3` and observe load balancing
- Verify Ingress routes `mysecondapp.com` to this app