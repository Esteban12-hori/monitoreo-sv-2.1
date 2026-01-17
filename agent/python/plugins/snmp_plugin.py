from agent_base import AgentPlugin
import time
import logging

try:
    from pysnmp.hlapi import SnmpEngine, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
    try:
        from pysnmp.hlapi import getCmd, CommunityData
    except ImportError:
        from pysnmp.hlapi.v1arch import getCmd, CommunityData
    PYSNMP_AVAILABLE = True
except Exception:
    PYSNMP_AVAILABLE = False


class SnmpMonitorPlugin(AgentPlugin):
    def collect(self):
        if not PYSNMP_AVAILABLE:
            return {"snmp_checks": [{"status": "error", "message": "pysnmp not available"}]}

        targets = [
            {"name": "Localhost SNMP", "ip": "127.0.0.1", "community": "public", "oid": "1.3.6.1.2.1.1.1.0"}
        ]

        results = []
        for t in targets:
            try:
                iterator = getCmd(
                    SnmpEngine(),
                    CommunityData(t["community"], mpModel=1),
                    UdpTransportTarget((t["ip"], 161), timeout=1.0, retries=0),
                    ContextData(),
                    ObjectType(ObjectIdentity(t["oid"]))
                )

                errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

                if errorIndication:
                    results.append({"name": t["name"], "status": "down", "error": str(errorIndication)})
                elif errorStatus:
                    results.append({"name": t["name"], "status": "error", "error": errorStatus.prettyPrint()})
                else:
                    val = varBinds[0][1].prettyPrint()
                    results.append({"name": t["name"], "status": "up", "value": val})
            except Exception as e:
                results.append({"name": t["name"], "status": "down", "error": str(e)})

        return {"snmp_checks": results}
