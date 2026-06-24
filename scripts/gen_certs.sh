#!/usr/bin/env bash
# Genera un certificado self-signed para Nginx (TLS 1.3, RNF-002).
set -euo pipefail
DIR="$(dirname "$0")/../infra/nginx/certs"
mkdir -p "$DIR"
openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
  -keyout "$DIR/server.key" -out "$DIR/server.crt" \
  -subj "/C=CL/O=Ejercito de Chile/CN=localhost"
echo "Certificados generados en $DIR"
