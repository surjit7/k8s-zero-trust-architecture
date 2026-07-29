# Lab 01: Deployments + Services

## Concept

A **Deployment** manages replicated Pods and handles rolling updates. A **Service** exposes them inside the cluster.

This lab covers:
- Creating a Deployment with a specific container image
- Exposing the app via **ClusterIP** (internal-only, accessed through Ingress)

## Manifests

| File | Purpose |
|------|---------|
| `deployment.yaml` | Flask app Deployment (1 replica, port 5001) |
| `service.yaml` | ClusterIP Service routing to port 5001 (internal-only) |

## How to Apply

```bash
# Start Minikube first
minikube start

# Build and load the image
docker build -t my-app:v5 -f ../apps/flask-app/Dockerfile ../apps/flask-app/
minikube image load my-app:v5

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

- Change `replicas: 1` to `replicas: 3` and observe scaling
- Test with `type: ClusterIP` to confirm access via Ingress only
