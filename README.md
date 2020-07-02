![logo](https://github.com/InfuseAI/primehub/raw/master/docs/media/logo.png?raw=true "PrimeHub")

[![primehub-admission](https://img.shields.io/docker/pulls/infuseai/primehub-admission?label=ce%20docker%20pulls)](https://hub.docker.com/r/infuseai/primehub-admission)

# PrimeHub Admission

PrimeHub-admission is a critical component of [PrimeHub](https://github.com/infuseai/primehub).

## Development

We are using `Pipenv` to manage python environment.

* `pipenv install --dev` to install all dependencies you needed for development.
* `pipenv install package_name` to install a new package for production environment.
* `pipenv lock --requirements > requirements.txt` whenever installed a new package for production environment
* `pipenv install package_name --dev` to install a new package for development environment.
* `pipenv shell` to activate the python environment.
* `exit` to exit the activated python environment.

Please do not directly modify `requirements.txt`. This file is automatically modified when running `build.sh` or `publish.sh`.

### Build Image in Local
If you want to build image in local, please use `build.sh`.

### Deploy Image to Docker Hub
When push commit, there is a manual job in the primehub repo.

OR

You can also publish image manually:  
1. Login to your docker hub account
2. Run `publish.sh`

### Run Tests

`PYTHONPATH=src py.test --cov=.`

## Enable Admission Webhook

Enable primehub-admission for a specific namespace.
```
kubectl label ns hub primehub.io/resources-validation-webhook=enabled
kubectl label ns hub primehub.io/image-mutation-webhook=enabled
kubectl label ns hub primehub.io/pvc-check-webhook=enabled
```
