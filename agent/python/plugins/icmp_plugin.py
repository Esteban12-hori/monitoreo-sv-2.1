
import platform
import subprocess
import re
from agent_base import AgentPlugin

class IcmpMonitorPlugin(AgentPlugin):
    def collect(self):
        target = "8.8.8.8"
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "1", target]
        
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, text=True)
            # Parse time=Xms
            # Windows: "Media = 12ms" or "time=12ms"
            # Linux: "time=12.3 ms"
            latency = 0
            if "time=" in output.lower():
                match = re.search(r"time[=<]([\d\.]+)\s*ms", output.lower())
                if match:
                    latency = float(match.group(1))
            elif "media =" in output.lower(): # Spanish Windows
                 match = re.search(r"media = ([\d]+)ms", output.lower())
                 if match:
                    latency = float(match.group(1))
            
            return {
                "icmp_ping": {
                    "target": target,
                    "status": "up",
                    "latency_ms": latency
                }
            }
        except subprocess.CalledProcessError:
            return {
                "icmp_ping": {
                    "target": target,
                    "status": "down"
                }
            }
        except Exception:
            return {"icmp_ping": {}}
