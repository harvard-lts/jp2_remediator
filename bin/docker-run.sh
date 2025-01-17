#!/bin/bash

## bash entrypoint
#docker run --rm --mount type=bind,source=${PWD},target=/app -it --entrypoint /bin/bash artifactory.huit.harvard.edu/lts/jp2_remediator $@

## Executable Docker image
docker run --rm --mount type=bind,source=${PWD},target=/data -it artifactory.huit.harvard.edu/lts/jp2_remediator $@

## Passing AWS credentials: If you want to use the s3 bucket option, create an .env file in the same directory with AWS credentials
# set -a
# source $(dirname "$0")/.env
# set +a

# docker run --rm \
#   --mount type=bind,source=${PWD},target=/data \
#   -e AWS_ACCESS_KEY_ID \
#   -e AWS_SECRET_ACCESS_KEY \
#   -e AWS_SESSION_TOKEN \
#   -it artifactory.huit.harvard.edu/lts/jp2_remediator "$@"