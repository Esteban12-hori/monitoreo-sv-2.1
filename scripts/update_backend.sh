#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")/.."; pwd)"
SERVICE_NAME="monitor-backend"
PYTHON_ENV="$REPO_DIR/src/server/.venv"

cd "$REPO_DIR"

git fetch --all
git reset --hard origin/main
git pull

if [ -d "$PYTHON_ENV" ]; then
  . "$PYTHON_ENV/bin/activate"
  pip install -r src/server/requirements.txt
fi

if command -v npm >/dev/null 2>&1; then
  cd src/client
  npm install
  npm run build
  cd "$REPO_DIR"
fi

if command -v systemctl >/dev/null 2>&1; then
  sudo systemctl restart "$SERVICE_NAME"
fi
