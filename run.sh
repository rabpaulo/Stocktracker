#!/bin/sh
SCRIPT_PATH=$(readlink -f "$0")
PROJECT_DIR=$(dirname "$SCRIPT_PATH")

exec docker run --rm -it \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp \
  --volume "$PROJECT_DIR/config/config.json:/app/config/config.json" \
  stocktracker "$@"
