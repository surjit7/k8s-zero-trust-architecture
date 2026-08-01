.PHONY: all help cluster cilium ingress argocd clean

# Colors for terminal output
GREEN := \033[0;32m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "Enterprise Zero-Trust K8s Architecture - Bootstrap"
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'

all: cluster cilium ingress argocd ## Run the complete bootstrap sequence

cluster: ## 1. Provision Minikube (eBPF mode, bypassing kube-proxy)
	@echo "$(GREEN)Starting Minikube without kube-proxy...$(NC)"
	minikube start \
		--network-plugin=cni \
		--cni=false \
		--extra-config=kubeadm.skip-phases=addon/kube-proxy \
		--nodes 3 \
		--cpus 2 \
		--memory 6144

cilium: ## 2. Install Cilium eBPF networking fabric
	@echo "$(GREEN)Installing Cilium CNI...$(NC)"
	cilium install --set kubeProxyReplacement=true
	@echo "$(GREEN)Waiting for Cilium to become healthy...$(NC)"
	cilium status --wait

ingress: ## 3. Enable NGINX Ingress controller
	@echo "$(GREEN)Enabling Minikube Ingress addon...$(NC)"
	minikube addons enable ingress

argocd: ## 4. Install ArgoCD for GitOps deployments
	@echo "$(GREEN)Installing ArgoCD...$(NC)"
	kubectl create namespace argocd || true
	kubectl apply -n argocd --server-side --force-conflicts \
		-f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
	@echo "$(GREEN)Waiting for ArgoCD server to be ready...$(NC)"
	kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=300s
	@echo "$(GREEN)ArgoCD Initial Admin Password:$(NC)"
	@kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d && echo ""

clean: ## Destroy the cluster and clean up
	@echo "$(GREEN)Destroying Minikube cluster...$(NC)"
	minikube delete
