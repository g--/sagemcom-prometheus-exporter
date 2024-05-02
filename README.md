
# Sagemcom Prometheus Exporter

I threw this exported together quickly to work with Telco's provided router
(aka CPE), which they called "Bell Home Hub 4000".  I've only tested it with
my router. I welcome PRs to make it work with others.

## quickstart

change the host and password as needed:

```
docker run -p 8000:8000 -e SAGEMCOM_HOST=192.168.0.1 -e SAGEMCOM_PASSWORD=sekret  -it geoffo/sagemcom-prometheus-exporter
```

and point prometheus at port 8000.

## Low Memory Checker

If you pass in the arguments `memorycheck <number of MiB>` it will reboot the
device if the device currently has less than the given amount of memory free.
Great for running at a cron job in the middle of the night.

for example:


```
docker run -p 8000:8000 -e SAGEMCOM_HOST=192.168.0.1 -e SAGEMCOM_PASSWORD=sekret  -it geoffo/sagemcom-prometheus-exporter python main.py memorycheck 250
```

and point prometheus at port 8000.

## GCP DNS updater

```
docker run -p 8000:8000 -e SAGEMCOM_HOST=192.168.0.1 -e SAGEMCOM_PASSWORD=sekret \
    --mount type=bind,source="gcloud-creds-ip-updater.json,target=/credentials.json,readonly \
    -e GOOGLE_APPLICATION_CREDENTIALS=/credentials.json  \
    -e TARGET_ZONE=my-gcp-zone-resource-name  \
    -e TARGET_DOMAIN=the.domain.name.example.com.  \
    -it geoffo/sagemcom-prometheus-exporter:local_ipupdate python main.py updatedns-gcp
```

This requires [gcp credentials--see gcp
documentation](https://cloud.google.com/docs/authentication/application-default-credentials).
In the example above, it's using the `GOOGLE_APPLICATION_CREDENTIALS` file method.

## kubernetes

```
cat <<EOF | kubectl create -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sagemcom-prometheus-exporter
  labels:
    app: sagemcom-prometheus-exporter
spec:
  replicas: 1
  selector:
    matchLabels:
      app: sagemcom-prometheus-exporter
  template:
    metadata:
      labels:
        app: sagemcom-prometheus-exporter
    spec:
      containers:
      - name: exporter
        image: geoffo/sagemcom-prometheus-exporter
        ports:
        - containerPort: 8000
        env:
        - name: SAGEMCOM_HOST
          value: 192.168.0.1
        - name: SAGEMCOM_PASSWORD
          valueFrom:
            secretKeyRef:
                name: sagemcom-credentials
                key: password
                optional: false
EOF

cat <<EOF | microk8s kubectl create -f -
apiVersion: v1
kind: Secret
metadata:
  labels:
    k8s-app: sagemcom-prometheus-exporter
  name: sagemcom-credentials
  namespace: default
type: Opaque
data:
  password: CHANGEMECHANGEME
EOF


```

If you're using the prometheus operator:

```
cat <<EOF | microk8s kubectl create -f -
apiVersion: v1
kind: Service
metadata:
  name: sagemcom-prometheus-exporter
  labels:
    app: sagemcom-prometheus-exporter
spec:
  selector:
    app: sagemcom-prometheus-exporter
  ports:
    - protocol: TCP
      port: 8000
      targetPort: 8000
EOF


cat <<EOF | kubectl create -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  labels:
    k8s-app: sagemcom-prometheus-exporter
    release: kube-prom-stack
  name: sagemcom-prometheus-exporter
spec:
  endpoints:
  - path: /
    targetPort: 8000
    scheme: http
    interval: 10s
  selector:
    matchLabels:
        app: sagemcom-prometheus-exporter
EOF
```


