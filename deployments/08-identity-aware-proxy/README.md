# Lab 08: Identity-Aware Proxy (Zero-Trust Identity)

This lab demonstrates how to implement an Identity-Aware Proxy (IAP) using `oauth2-proxy` and NGINX Ingress annotations. This is the ultimate "Zero-Trust" pattern: unauthenticated traffic is blocked at the cluster edge, meaning your backend Python pods use 0% CPU processing unauthorized requests.

## How It Works

1. A user attempts to visit `https://myapp.com`.
2. The NGINX Ingress Controller intercepts the request.
3. Due to the `auth-url` annotation, NGINX asks `oauth2-proxy` if the user has a valid session.
4. If they don't, NGINX uses the `auth-signin` annotation to redirect them to the Identity Provider (IdP).
5. The user logs into the IdP (e.g., your custom `SSO-Django` project) and is redirected back to `oauth2-proxy`.
6. `oauth2-proxy` sets a secure cookie and tells NGINX the user is allowed in.
7. NGINX forwards the traffic to the Flask app, injecting the user's email into the HTTP headers (`X-Auth-Request-Email`).

## Prerequisites

You must have an OIDC-compliant Identity Provider (IdP). If you are using your custom `SSO-Django` project:
1. Register a new OAuth2 Client Application in Django.
2. Set the Redirect URI to `https://myapp.com/oauth2/callback`.
3. Copy the Client ID and Client Secret into the `oauth2-proxy.yaml` secret.

## Deployment

1. Review and apply the proxy deployment (ensure you updated the secret with your IdP credentials):
```bash
kubectl apply -f oauth2-proxy.yaml
```

2. Apply the new protected ingress:
```bash
kubectl apply -f protected-ingress.yaml
```

## Validation

Try to visit `https://myapp.com`. Instead of seeing the Flask app, you will immediately be redirected to your IdP's login page. Once you authenticate, you will be seamlessly redirected back to your Flask app!
