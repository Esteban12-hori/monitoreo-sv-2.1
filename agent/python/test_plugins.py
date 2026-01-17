import sys
import os
from pathlib import Path
import json

# Add current directory to path
sys.path.append(str(Path(__file__).resolve().parent))

from agent import PluginManager

def test_plugins():
    print("Initializing PluginManager...")
    pm = PluginManager()
    
    print(f"Loaded {len(pm.plugins)} plugins.")
    for p in pm.plugins:
        print(f" - {p.__class__.__name__}")
        
    print("\nCollecting metrics...")
    data = pm.collect_all()
    
    print("\nMetrics collected:")
    print(json.dumps(data, indent=2))
    
    # Validation
    expected_keys = ["snmp_checks", "http_checks", "icmp_ping", "services", "processes"]
    found_keys = [k for k in expected_keys if k in data]
    print(f"\nFound expected new metrics: {found_keys}")

if __name__ == "__main__":
    test_plugins()
