#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

$DIR/build.sh

# TAG=$(date +"%Y%m%d%H%M")
TAG=$(git rev-parse HEAD | cut -c1-10)
IMAGE="infuseai/primehub-admission:${TAG}"

if [ "${GITHUB_ACTIONS}" == "true" ]; then
    echo "::set-output name=image_name::$IMAGE"
fi

echo "publish image at $IMAGE"
docker tag primehub-admission $IMAGE
docker push $IMAGE
