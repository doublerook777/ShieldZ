#!/bin/sh
# api       -> decision service, bound to 127.0.0.1 only (host network, ADR D8/D14).
#              SHIELDZ_WORKERS=N runs N processes; history, outbox and pepper are shared safely.
# explainer -> outbox worker
# anything else is run as a command (make z-gate uses `bash -c ...`)
set -e
case "$1" in
  api)
    exec python -m shieldz.service.serve
    ;;
  explainer)
    exec python -m shieldz.explainer.worker
    ;;
  *)
    exec "$@"
    ;;
esac
