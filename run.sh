#!/bin/sh
docker run --rm -it \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp \
  --volume "$PWD/stocktracker.json:/app/stocktracker.json" \
  stocktracker
