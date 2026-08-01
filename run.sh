#!/bin/sh
cd ~/Projects/Stocktracker || exit 1
set -eu

PROJECT_DIR=$(CDPATH= cd -P "$(dirname "$0")" && pwd)
IMAGE=stocktracker:local

docker build --tag "$IMAGE" "$PROJECT_DIR"

exec docker run --rm -it \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp \
  --volume "$PROJECT_DIR/config/config.json:/app/config/config.json" \
  "$IMAGE" "$@"
