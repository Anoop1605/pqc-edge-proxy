#!/usr/bin/env bash
set -e
mkdir -p certs && cd certs
OPENSSL="/opt/openssl-3.5/bin/openssl"
export LD_LIBRARY_PATH="/opt/openssl-3.5/lib64"

$OPENSSL ecparam -name prime256v1 -genkey -noout -out server.key
$OPENSSL req -new -x509 -sha256 -key server.key -out server.crt -days 365 \
    -subj "/CN=pqc-proxy.local" -addext "subjectAltName=DNS:pqc-proxy.local,IP:10.0.1.2,IP:10.0.2.2"
echo "Certificates generated in certs/"