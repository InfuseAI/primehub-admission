#! /bin/bash

echo "Uninstall primehub-admission ..."
kubectl delete ValidatingWebhookConfiguration resources-validation-webhook || true
kubectl delete MutatingWebhookConfiguration pod-image-mutating-webhook || true

kubectl get deploy --all-namespaces | grep -E 'resources-validation-webhook|pod-image-replacing-webhook' | awk '{print $1, $2}' | xargs -I{} kubectl delete deploy -n {}
kubectl get service --all-namespaces | grep -E 'resources-validation-webhook\S*|pod-image-replacing-webhook\S*' | awk '{print $1, $2}' | xargs -I{} kubectl delete service -n {}

kubectl get secret --all-namespaces | grep -E 'gitlab-primehub-registry-pull' | awk '{print $1, $2}' | xargs -I{} kubectl delete secret -n {}
kubectl get secret --all-namespaces | grep -E 'resources-validation-webhook\S*|pod-image-replacing-webhook\S*' | awk '{print $1, $2}' | xargs -I{} kubectl delete secret -n {}

kubectl get serviceaccount --all-namespaces | grep -E 'admission-webhook-sa' | awk '{print $1, $2}' | xargs -I{} kubectl delete serviceaccount -n {}
kubectl delete ClusterRoleBinding admission-webhook-crb

kubectl label ns hub primehub.io/image-mutation-webhook- || true
kubectl label ns primehub primehub.io/image-mutation-webhook- || true

kubectl label ns hub primehub.io/resources-validation-webhook- || true
kubectl label ns primehub primehub.io/resources-validation-webhook- || true