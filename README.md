
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


