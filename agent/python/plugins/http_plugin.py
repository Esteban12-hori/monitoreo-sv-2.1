
import time
import requests
from agent_base import AgentPlugin

class HttpMonitorPlugin(AgentPlugin):
    def collect(self):
        targets = [
            {"name": "Internet", "url": "https://www.google.com", "timeout": 2},
            {"name": "Localhost", "url": "http://127.0.0.1", "timeout": 1}
        ]
        results = []
        for t in targets:
            start = time.time()
            try:
                resp = requests.get(t["url"], timeout=t["timeout"])
                latency = (time.time() - start) * 1000 # ms
                results.append({
                    "name": t["name"],
                    "url": t["url"],
                    "status": "up" if resp.status_code < 400 else "error",
                    "code": resp.status_code,
                    "latency_ms": round(latency, 2)
                })
            except Exception as e:
                results.append({
                    "name": t["name"],
                    "url": t["url"],
                    "status": "down",
                    "error": str(e)
                })
        
        return {"http_checks": results}
