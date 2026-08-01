# Architectural Decision Records (ADRs)

> This document captures the core design decisions, trade-offs, and reasoning behind the infrastructure choices in this zero-trust architecture. As a platform engineer, configuring a tool is easy; knowing *why* to choose it is what matters.

---

## ADR-001: Replacing kube-proxy with Cilium (eBPF)

**Status:** Accepted
**Context:** Kubernetes traditionally relies on `kube-proxy` (using iptables or IPVS) for Layer 4 load balancing and ClusterIP routing. As the cluster scales, iptables rules evaluate sequentially, introducing O(n) latency degradation. Furthermore, iptables operates purely at L3/L4, offering no L7 HTTP context for security.
**Decision:** We entirely bypassed `kube-proxy` (`kubeadm.skip-phases=addon/kube-proxy`) in favor of **Cilium**. 
**Reasoning & Trade-offs:**
- **Performance:** Cilium injects eBPF programs directly into the Linux kernel (XDP/tc). Packet routing happens at the socket level before traversing the traditional network stack.
- **Security:** We gain L7 NetworkPolicies (e.g., filtering HTTP POST/GET requests), which is impossible with standard Kubernetes NetworkPolicies.
- **Trade-off:** eBPF requires a modern Linux kernel. This increases the minimum OS requirements for the underlying bare-metal/VM nodes, but given this is an enterprise architecture, running a modern kernel is an acceptable baseline.

## ADR-002: Default-Deny Zero-Trust Network Policies

**Status:** Accepted
**Context:** By default, all pods in a Kubernetes cluster can communicate with all other pods. If a single web-facing pod is compromised, the attacker has unrestricted lateral movement across the internal network.
**Decision:** Implemented a strict default-deny NetworkPolicy posture across all application namespaces.
**Reasoning & Trade-offs:**
- **Security:** Forces explicit authorization for all traffic. The Flask app can *only* talk to Redis on port 6379, and nothing else.
- **Integration with IdP:** This lays the foundation for integrating our custom `SSO-Django` Identity Provider at the ingress edge. Once traffic passes the IdP authentication, the internal mesh strictly limits where that authenticated request can go.
- **Trade-off:** Developer friction. A junior engineer might struggle to debug a hanging `curl` command. This is explicitly why **Lab 05 (Netshoot & Hubble)** was created — to provide the team with the observability tools needed to debug a zero-trust mesh.

## ADR-003: Headless Services for Stateful Workloads (Redis)

**Status:** Accepted
**Context:** When deploying stateful workloads (like Redis or PostgreSQL databases) in Kubernetes, standard ClusterIP Services load-balance traffic via round-robin across all backing pods.
**Decision:** We utilize a **Headless Service** (`clusterIP: None`) paired with a **StatefulSet** for the Redis backend.
**Reasoning & Trade-offs:**
- **Identity:** Stateful applications often require clients to connect to a *specific* replica (e.g., the primary node for writes, or a read-replica for reads). A headless service bypasses the L4 load balancer entirely and returns the direct IP addresses (A records) of the individual pods via CoreDNS.
- **Trade-off:** Application clients must handle their own load balancing or topology awareness (e.g., using a Redis Sentinel client). Since our Flask app is designed for enterprise resilience, this is the correct pattern.

## ADR-004: Strict Pod Security Standards (PSS)

**Status:** Accepted
**Context:** Containers share the host's kernel. A compromised container running as `root` with a writable filesystem can easily be used to mount a host-level escape attack.
**Decision:** All deployments enforce strict SecurityContexts: `runAsNonRoot: true`, `readOnlyRootFilesystem: true`, and all Linux capabilities are explicitly dropped (`capabilities: drop: - ALL`).
**Reasoning & Trade-offs:**
- **Security:** Implements the principle of least privilege at the runtime level. Even if the Flask application logic is exploited, the attacker lands in an unprivileged, read-only cage.
- **Trade-off:** Requires highly optimized Dockerfiles (e.g., our custom multi-stage Dockerfile that explicitly defines a UID `10001` user and prevents Python from writing `.pyc` bytecode files to the read-only disk).

## Future Considerations: Integrating the Enterprise IdP

The next architectural phase will involve deploying `oauth2-proxy` alongside the NGINX Ingress controller. This will route all incoming edge traffic through the custom **SSO-Django Identity Provider** (from my other portfolio project), enforcing multi-tenant OAuth2/OIDC authentication *before* traffic ever enters the zero-trust cluster mesh.
