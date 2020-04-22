FROM python:alpine
LABEL maintainer="Patrice Ferlet <metal3d@gmail.com>"\
      description="Autoconfigure Nginx to proxy ingresses on one port"

RUN set -xe; \
    mkdir -p /opt/lb-controller /opt/nginx-config; \
    chmod a+rw /opt/nginx-config

ADD requirements.txt /opt/lb-controller/

VOLUME /opt/nginx-config
WORKDIR /opt/lb-controller
RUN set -xe; \
    pip install -r requirements.txt

ADD src/main.py /opt/lb-controller/

ENTRYPOINT ["python"]
CMD ["main.py"]
