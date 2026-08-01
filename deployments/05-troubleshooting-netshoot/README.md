# Lab 05: Enterprise Troubleshooting & Network Visualization

> In a zero-trust architecture, you can't just assume the network is working. When traffic drops, you need the tools to prove *why* it dropped. This lab introduces `netshoot` (the Swiss Army knife of network debugging) and Cilium Hubble (eBPF observability).

## 🎯 What We Are Proving
1. **Internal DNS Resolution**: How services find each other in Kubernetes.
2. **Network Connectivity**: Verifying Layer 4 (TCP) and Layer 7 (HTTP) flows.
3. **Zero-Trust Enforcement**: Watching a NetworkPolicy drop unauthorized traffic in real-time.

---

## 🛠️ Step 1: Deploy Netshoot

First, we deploy a pod that has all the network debugging tools pre-installed (`curl`, `dig`, `nc`, `tcpdump`, etc.).

```bash
kubectl apply -f netshoot.yaml
```

Wait for it to run:
```bash
kubectl get pod netshoot
```

---

## 🔍 Step 2: The Junior Engineer's Playground

Now, we `exec` into the container. This puts you inside the cluster's network namespace.

```bash
kubectl exec -it netshoot -- bash
```

*(You are now inside the pod! Run the following commands)*

### 1. Test DNS Resolution (CoreDNS)
Let's see how the Flask app finds the Redis pod. We will query the Headless Service.

```bash
# Query the DNS A records for Redis
dig +short redis-headless.default.svc.cluster.local

# Notice it returns the direct Pod IP(s), not a load-balanced ClusterIP!
```

### 2. Test Layer 4 TCP Connectivity
Can we reach Redis on port 6379? We use `nc` (netcat) to test raw TCP connections.

```bash
nc -vz redis-headless.default.svc.cluster.local 6379
# Expected output: Connection to redis-headless... 6379 port [tcp/redis] succeeded!
```

### 3. Test Layer 7 HTTP Connectivity
Can we hit our Flask app internally without going through the Ingress?

```bash
curl -s http://flask-app-service.default.svc.cluster.local:80/livez
# Expected output: Service Alive
```

*(Type `exit` to leave the netshoot pod)*

---

## 🛑 Step 3: Proving Zero-Trust (The Drop)

If you haven't already applied the Network Policies from Lab 06, do it now. This will enforce a default-deny posture.

```bash
kubectl apply -f ../06-network-policy/
```

Now, let's try to reach Redis again from our `netshoot` pod.

```bash
kubectl exec -it netshoot -- nc -vz redis-headless.default.svc.cluster.local 6379
# EXPECTED: The command will hang indefinitely. 
# Why? Because netshoot does NOT have the label `app: flask-app` required by the Redis NetworkPolicy!
```

Hit `Ctrl+C` to cancel the hanging command.

---

## 👁️ Step 4: Visualizing the Drop with Hubble

In a real enterprise environment, a hanging terminal isn't enough. We need observability. Let's look at what Cilium eBPF saw.

1. Open a new terminal window on your host machine.
2. Enable Hubble Port Forwarding:
   ```bash
   cilium hubble port-forward&
   ```
3. Open the Hubble UI:
   ```bash
   cilium hubble ui
   ```
4. This will open a browser window. Select the `default` namespace.
5. In your first terminal, run the failing `nc` command again.
6. Look at the Hubble UI — you will see a red line and a **DROPPED** status from `netshoot` to `redis`. This is eBPF enforcing your zero-trust architecture at the kernel level!

---

## 🧹 Cleanup

```bash
kubectl delete -f netshoot.yaml
```
