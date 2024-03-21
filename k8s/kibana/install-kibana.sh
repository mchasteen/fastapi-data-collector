#!/bin/bash
#helm repo add elastic https://helm.elastic.co
#helm repo update
helm upgrade --install elasticsearch-kibana kibana \
  --repo https://helm.elastic.co \
  --namespace fastapi-data-collector --create-namespace \
  -f ./values-kibana.yaml
#sleep 30
#helm install my-awx-operator awx-operator/awx-operator -n awx --create-namespace -f ./values.yaml
#kubectl get secret -n awx awx-admin-password -o jsonpath="{.data.password}" | base64 --decode ; echo

