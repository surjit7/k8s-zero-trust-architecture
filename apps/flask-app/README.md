# Flask App

A Flask web app that stores visit counts in Redis — used to learn Kubernetes Deployment, Service, Ingress, NetworkPolicies, and StatefulSets.

## What's Inside

| File | Purpose |
|------|--------|
| `app.py` | Flask app source (Redis integration, ProxyFix for Ingress) |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container build instructions |

## How to Run Locally (Outside Kubernetes)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
python app.py

# 3. Access
curl http://localhost:5001
```

> **Note:** `app.py` connects to Redis at `redis-0.redis-headless.default.svc.cluster.local:6379` — this only works inside Kubernetes. For local testing, comment out the Redis connection or use a local Redis instance.

## How to Build Docker Image

```bash
docker build -t my-app:v5 .
```

## How to Load into Minikube

```bash
minikube image load my-app:v5
```

## How to Deploy (via Kubernetes)

See [Lab 01](../../deployments/01-deployment/) for the Deployment + Service manifests.

## App Routes

| Route | Description |
|-------|-|
| `GET /` | Returns visitor count + client IP |

## Revisiting This Lab

- Change `replicas` in the Deployment and observe multiple Flask Pods responding
- Add a new route `/health` and update the manifest