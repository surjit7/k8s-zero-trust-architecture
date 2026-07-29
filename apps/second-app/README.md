# Second App

A minimal Flask app used to demonstrate **multi-host Ingress routing** — routing between `myapp.com` and `mysecondapp.com` through a single Ingress controller.

## What's Inside

| File | Purpose |
|------|--------|
| `app2.py` | Second Flask app (session affinity via cookies) |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container build instructions |

## How to Run Locally (Outside Kubernetes)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
python app2.py

# 3. Access
curl http://localhost:5001
```

## How to Build Docker Image

```bash
docker build -t my-second-app:v1 .
```

## How to Load into Minikube

```bash
minikube image load my-second-app:v1
```

## How to Deploy (via Kubernetes)

See [Lab 03](../../deployments/03-ingress/) for the Deployment + Service + Ingress manifests.

## Why This App?

This app demonstrates **session affinity** via a `backend_session` cookie — useful for learning:
- Sticky sessions / cookie-based affinity
- How load balancing distributes requests across pods
- Why multiple hosts on one Ingress matter

## App Routes

| Route | Description |
|-------|-|
| `GET /` | Returns "Hello from app 2" + PID (useful for observing pod distribution) |

## Revisiting This Lab

- Deploy with `replicas: 3` and watch the PID change across requests
- Test session affinity: send multiple requests and check if `backend_session` cookie persists
- Add a new host to `ingress.yaml` and route to this app