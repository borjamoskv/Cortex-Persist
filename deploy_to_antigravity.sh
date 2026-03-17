#!/bin/bash
# NODO SOBERANO ANTIGRAVITY — GCP DEPLOYMENT
# Ω₃ Byzantine Default — Premium Network Tier for <40ms latency.

PROJECT_ID="forward-tape-489302-m7"
ZONE="us-central1-a"
INSTANCE_NAME="antigravity"

echo "🚀 Materializando Nodo Soberano en GCP ($PROJECT_ID)..."

gcloud compute instances create $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=n2-standard-4 \
    --network-interface=address=,network-tier=PREMIUM,subnet=default \
    --maintenance-policy=MIGRATE \
    --provisioning-model=STANDARD \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --tags=cortex-relay,http-server,https-server \
    --create-disk=auto-delete=yes,boot=yes,device-name=$INSTANCE_NAME,image=projects/ubuntu-os-cloud/global/images/ubuntu-2204-jammy-v20240307,mode=rw,size=50,type=projects/$PROJECT_ID/zones/$ZONE/diskTypes/pd-ssd \
    --labels=managed-by=antigravity,version=v8-1

echo "✅ Nodo solicitado. Configura firewall para el puerto 8080/9998 si es necesario."
