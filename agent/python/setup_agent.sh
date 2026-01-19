#!/bin/bash
set -e

echo "========================================================"
echo "              UpKeep Agent - Easy Setup"
echo "========================================================"
echo

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found."
    exit 1
fi
echo "[OK] Python3 found."

# 2. Create Venv
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
else
    echo "[INFO] Virtual environment exists."
fi

# 3. Install Dependencies
echo "[INFO] Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# 4. Config
if [ ! -f "agent.config.json" ]; then
    echo
    echo "========================================================"
    echo "                  Configuration"
    echo "========================================================"
    read -p "Server URL (e.g. http://192.168.1.10:8000): " SERVER_URL
    read -p "Server ID (e.g. server-01): " SERVER_ID
    read -p "Token (optional): " TOKEN
    
    cat <<EOF > agent.config.json
{
  "server": "$SERVER_URL",
  "server_id": "${SERVER_ID}",
  "token": "${TOKEN}",
  "interval": 60
}
EOF
    echo "[OK] Configuration saved."
else
    echo "[INFO] agent.config.json exists. Skipping."
fi

# 5. Create Start Script
cat <<EOF > start_agent.sh
#!/bin/bash
cd "\$(dirname "\$0")"
source venv/bin/activate
echo "Starting Agent..."
python3 agent.py
EOF
chmod +x start_agent.sh

echo
echo "========================================================"
echo "              Setup Complete!"
echo "========================================================"
echo "Run ./start_agent.sh to start the agent."
