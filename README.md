# Auto "one-point" load balancer for ingress-controllers

This project proposes an easy to use solution to automate a service creation that binds an **unique IP address to ingress-controllers IPs**. 

This is very usefull if you are using an external load balancer controller in Kubernetes.

For example, with Scaleway provider, you can create a kubernetes cluster with their "Kapsule" solution. This cluster allows you to install an ingress-controller but you only can use service type "LoadBalancer" to automate LB creation. 

There are 2 problems:

- at first, the LB will hit the service port, not the ingress-controller, so you cannot use cert-manager to automate SSL certificates
- secondly, there will be one LB per service, that means 1 IP per services and several LB to pay

You can, of cours, manually create LB, but you need to detect if nodes are down and respawned with new IP. And if you've got auto-scaling for nodes, so you need to change yourself the LB configuration.

This project proposes to create one service with type "LoadBalancer" - it binds ports 80 and 443 (for now) to a Nginx container that is configured to make TCP forward (instead of http forward).

A sidecar container checks ingress-controllers IPs and make the configuration changes in nginx container (by creating upstreams). 

This way, **every connections on the LB is redirected to nginx which forwards everything to ingress-controller IP**.

## Installation

Be sure that you already have installed an ingress-controller (nginx-controller, haproxy-controller...)

```
git clone https://github.com/metal3d/lb-proxy-controller.git
cd lb-proxy-controller
helm install lbproxy chart/lb-proxy-controller --namespace=kube-system
```

Then check LB External IP given by Kubernetes (here, XX.XX.XX.XX):

```
kubectl -n kube-system get svc lbproxy-nginx-lb-controller
NAME                          TYPE           CLUSTER-IP      EXTERNAL-IP    PORT(S)                      AGE
lbproxy-nginx-lb-controller   LoadBalancer   10.39.246.162   XX.XX.XX.XX   80:31853/TCP,443:32337/TCP   3m
```

You can now use that IP for all websites.


## Note:

- This Python script is really young and can have some bugs. Fill me an issue if needed.
- The installation process create a cluster role and cluster rolebinding, you need to be kubernetes administrator to deploy the solution


