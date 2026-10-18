#!/bin/zsh
set -e
cd "${0:A:h:h}"
exec .venv/bin/python -m tools.start_local_service
