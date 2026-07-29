# Installing Minikube on Local Machine

Minikube runs a single-node Kubernetes cluster inside a container on your local Linux machine.

## Prerequisites

- **Virtualization support** enabled in BIOS
- **Docker** installed (recommended driver)
- **kubectl** installed
- **helm** (optional, for ArgoCD installation)

## Install Minikube (Linux)

```bash
# Download the latest minikube binary
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64

# Install to /usr/local/bin
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Verify installation
minikube version
```

## Install Docker (if not already installed)

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Add current user to docker group (no sudo needed)
sudo usermod -aG docker $USER
newgrp docker

# Verify Docker is running
docker info
```

## Install kubectl (if not already installed)

```bash
# Download kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

# Install
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Verify
kubectl version --client
```

## Start Minikube

```bash
# Start with Docker driver (recommended for local development)
minikube start --driver=docker --cpus=4 --memory=6g --nodes=1
```

## Enable Ingress Addon

```bash
minikube addons enable ingress
```

## Verify Installation

```bash
# Check cluster info
minikube status

# Check nodes
kubectl get nodes

# Check that ingress addon is running
kubectl get pods -n ingress-nginx
```

## Useful Minikube Commands

| Command | Purpose |
|-- -------|--|
| `minikube start` | Start the cluster |
| `minikube stop` | Stop without deleting |
| `minikube delete` | Delete the cluster |
| `minikube ip` | Get the cluster IP |
| `minikube service <name>` | Access a service |
| `minikube addons list` | List available addons |
| `minikube dashboard` | Open Kubernetes dashboard |

## Troubleshooting

### VM is not running

```bash
minikube stop
minikube start
```

### Docker driver issues

```bash
# Ensure user is in docker group
sudo usermod -aG docker $USER
newgrp docker

# Then retry
minikube start --driver=docker
```

### Port conflicts

```bash
# Check for existing kubelet processes
ps aux | grep kubelet
```
