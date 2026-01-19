#!/bin/bash
set -e

# If environment variables are provided, generate/overwrite config
if [ -n "$SERVER_URL" ]; then
    echo "Generating configuration from environment variables..."
    cat <<EOF > agent.config.json
{
  "server": "$SERVER_URL",
  "server_id": "${SERVER_ID:-$(hostname)}",
  "token": "${TOKEN}",
  "interval": ${INTERVAL:-60},
  "verify": "${VERIFY_TLS:-true}"
}
EOF
fi

# Run the agent
echo "Starting Agent..."
exec python agent.py "$@"
