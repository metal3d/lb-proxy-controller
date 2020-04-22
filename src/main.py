import time
import os
import shlex
import logging
from hashlib import sha256
from kubernetes import client, config
from kubernetes.stream import stream


logging.getLogger().setLevel(logging.INFO)

nginx_config = """
user  nginx;
worker_processes  auto;

error_log  /var/log/nginx/error.log warn;
pid        /var/run/nginx.pid;


events {
    worker_connections  1024;
}

stream {
    include /etc/nginx/upstreams.conf;

    server {
        listen     80;
        #TCP traffic will be forwarded to the specified server
        proxy_pass controller;
    }

    server {
        listen     443;
        #TCP traffic will be forwarded to the specified server
        proxy_pass controller-ssl;
    }
}
"""


upstream_template = '''
upstream controller {
%s
}
upstream controller-ssl {
%s
}
'''

try:
    config.load_kube_config()
except Exception:
    config.load_incluster_config()

v1 = client.CoreV1Api()
ext = client.ExtensionsV1beta1Api()

timeout = 5


def command(cmd, podselector, namespace='kube-system'):
    """ Execute a command in a given pod """

    pods = v1.list_namespaced_pod(
        namespace,
        label_selector=podselector,
        timeout_seconds=timeout
    )

    for pod in pods.items:
        podname = pod.metadata.name
        logging.info("contacting %s" % podname)
        try:
            conn = stream(
                v1.connect_get_namespaced_pod_exec,
                podname,
                namespace,
                container='nginx',
                command=shlex.split(cmd),
                stderr=True, stdin=True,
                stdout=True, tty=False,
            )
            logging.info(conn)
        except Exception as e:
            logging.exception(e)


def get_ingress_ips():
    """ Return IPs that are assigned to ingresses """
    ips = set()
    try:
        ingresses = ext.list_ingress_for_all_namespaces(
            timeout_seconds=timeout
        )
        for ingress in ingresses.items:
            status = ingress.status.load_balancer.ingress
            for i in status:
                ips.add(i.ip)
    except Exception as e:
        logging.exception(e)

    return list(ips)


if __name__ == "__main__":
    logging.info("Starting service")
    sig = ""
    nginx_namespace = os.environ.get('LB_NGINX_NS', 'kube-system')
    nginx_selector = os.environ.get('LB_NGINX_SELECTOR')

    while True:
        logging.info("Get IPs of ingresses...")
        ips = get_ingress_ips()
        http = []
        ssl = []
        for ip in ips:
            http.append("\tserver %s:80;" % ip)
            ssl.append("\tserver %s:443;" % ip)

        http.sort()
        ssl.sort()

        http = "\n".join(http)
        ssl = "\n".join(ssl)

        upstream = upstream_template % (http, ssl)

        # get a signature for that configuration
        thissig = sha256(upstream.encode()).digest().hex()

        # if signature changed, so write new configuration and reload nginx
        if thissig != sig:
            logging.info("Signature changed %s" % sig)
            # write conf in shared volume
            logging.info("Writing nginx configuration...")
            with open('/opt/nginx-config/nginx.conf', 'w') as f:
                f.write(nginx_config)
            with open('/opt/nginx-config/upstreams.conf', 'w') as f:
                f.write(upstream)
            logging.info("done !")

            logging.info("Try to reload nginx...")
            # command("nginx -t", nginx_selector, nginx_namespace)
            command("nginx -s reload", nginx_selector, nginx_namespace)
            logging.info("done !")

            # keep new signature
            sig = thissig

        time.sleep(10)
