# Building Docker Images

This guide covers building container images for the apps in this repo.

## Prerequisites

- **Docker** installed and running
- **Docker Compose** (optional)

## Build App Images

### Flask App (Lab 1)

```bash
# Build image
docker build -t my-app:v5 -f apps/flask-app/Dockerfile apps/flask-app/

# Test locally
docker run -p 5001:5001 my-app:v5

# Push to Docker Hub (optional)
docker tag my-app:v5 <your-dockerhub-username>/my-app:v5
docker push <your-dockerhub-username>/my-app:v5
```

### Second App (Lab 3)

```bash
# Build image
docker build -t my-second-app:v1 -f apps/second-app/Dockerfile apps/second-app/

# Test locally
docker run -p 5002:5001 my-second-app:v1
```

## Load Images into Minikube

Images built locally won't be available inside Minikube by default. You need to load them:

### Docker Driver (Recommended)

```bash
# Load a single image
minikube image load my-app:v5

# Load all images at once
minikube image load my-app:v5 my-second-app:v1
```

### KVM2 / VirtualBox Driver

```bash
# Option 1: Use minikube's embedded docker
eval $(minikube docker-env)
docker build -t my-app:v5 -f apps/flask-app/Dockerfile apps/flask-app/

# The image is already in minikube — no need to load!

# When done, reset shell:
eval $(minikube docker-env -u)
```

## Deploy Without Docker (Using ImagePullPolicy: Never)

Since `imagePullPolicy: Never` is set in the manifests, you **must** have the image locally:

```bash
# Ensure the image is in minikube
minikube image load my-app:v5

# Then apply
kubectl apply -f deployments/01-deployment/
```

## Dockerfile Best Practices

| Practice | Example |
|-- -------|--|
| Use multi-stage builds | Reduce final image size |
| Pin base image versions | `FROM python:3.11-slim` (not `latest`) |
| Cache dependencies first | `COPY requirements.txt` before `COPY . .` |
| Use `.dockerignore` | Exclude `.git`, `__pycache__`, etc. |

## Useful Docker Commands

| Command | Purpose |
|-- -------|--|
| `docker images` | List all images |
| `docker rmi <image>` | Remove an image |
| `docker build -t <name> <path>` | Build an image |
| `docker run <image>` | Run a container |
| `docker ps` | List running containers |
| `docker inspect <image>` | Inspect image details |
| `minikube image ls` | List images in minikube |
| `minikube image inspect <image>` | Inspect minikube image |