![logo](https://github.com/InfuseAI/primehub/raw/master/docs/media/logo.png?raw=true "PrimeHub")


[![primehub-admission](https://img.shields.io/docker/pulls/infuseai/primehub-admission?label=docker%20pulls)](https://hub.docker.com/r/infuseai/primehub-admission)

# PrimeHub Admission

PrimeHub-admission is a critical component of [PrimeHub](https://github.com/infuseai/primehub).

## Features

PrimeHub-admission utilized [Dynamic Admission Control](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/) of Kubernetes to implement several PrimeHub features, including:
- Resource validation, check if certain group/user exceeds the given resource limit.
- PVC check - Check if a PVC is no longer exists before user pod is allocated.
- Image mutation - Modify image prefix for air-gapped environment.
- License Check - Check if a License is valid for current platform.

## Enable Admission Webhook

You can specify which primehub-admission features to enable by giving the corresponding label to the Kubernetes namespace.

```
# To enable Resource validation, PVC check, and License Check
kubectl label ns hub primehub.io/admission-webhook=enabled

# To enable Image mutation
kubectl label ns hub primehub.io/image-mutation-webhook=enabled
```

## Deployment

To deploy PrimeHub-Admission as a Kubernetes component, please check [PrimeHub HelmChart](https://github.com/InfuseAI/primehub/tree/master/chart/templates/admission).
