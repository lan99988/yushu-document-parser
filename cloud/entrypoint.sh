#!/bin/sh
set -eu

set -- api-server --host 0.0.0.0 --port 8000 --tier "${MINERU_TIER:-standard}"
if [ -n "${MINERU_API_KEY:-}" ]; then
  set -- "$@" --api-key "$MINERU_API_KEY"
fi

exec mineru-kit "$@"
