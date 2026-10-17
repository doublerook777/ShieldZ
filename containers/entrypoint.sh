#!/bin/sh
# api       -> decision service, bound to 127.0.0.1 only (host network, ADR D8/D14)
# explainer -> outbox worker
# anything else is run as a command (make z-gate uses `bash -c ...`)
set -e
case "$1" in
  api)
    exec python -m uvicorn shieldz.service.app:create_app --factory \
      --host 127.0.0.1 --port 8000 --no-access-log
    ;;
  explainer)
    exec python -m shieldz.explainer.worker
    ;;
  *)
    exec "$@"
    ;;
esac
