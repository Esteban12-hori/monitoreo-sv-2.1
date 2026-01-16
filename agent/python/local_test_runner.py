import argparse
import json
import logging
import threading
import time
from datetime import datetime, timezone
from math import sin, pi
from pathlib import Path

import requests


def setup_logging():
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "local_test.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(threadName)s] %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
    )


def register_server(base_url: str, server_id: str, token: str, timeout: int = 10):
    url = base_url.rstrip("/") + "/api/register"
    payload = {"server_id": server_id, "token": token}
    r = requests.post(url, json=payload, timeout=timeout)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Fallo registrando servidor {server_id}: {r.status_code} {r.text}")
    return r.json()


def generate_metrics(scenario: str, index: int, step: int):
    t = step
    base_cpu = 20 + 5 * sin(2 * pi * t / 60)
    base_mem = 30 + 5 * sin(2 * pi * t / 90)
    base_disk = 40
    if scenario == "stress-cpu":
        cpu_total = min(100.0, base_cpu + 50)
        mem_used = min(90.0, base_mem + 10)
        disk_percent = min(95.0, base_disk + 5)
    elif scenario == "memory-leak":
        cpu_total = min(80.0, base_cpu + index * 3)
        mem_used = min(98.0, base_mem + step * 0.5)
        disk_percent = min(95.0, base_disk + step * 0.2)
    elif scenario == "io-spikes":
        cpu_total = min(90.0, base_cpu + (20 if step % 10 < 3 else 0))
        mem_used = min(85.0, base_mem + (10 if step % 15 < 5 else 0))
        disk_percent = min(99.0, base_disk + (30 if step % 8 < 2 else 0))
    else:
        cpu_total = min(70.0, max(5.0, base_cpu))
        mem_used = min(80.0, max(10.0, base_mem))
        disk_percent = min(80.0, max(10.0, base_disk))
    per_core = [max(0.0, min(100.0, cpu_total + (i - index) * 2)) for i in range(4)]
    mem_total = 8192.0
    mem_used_abs = mem_total * mem_used / 100.0
    mem_free_abs = max(0.0, mem_total - mem_used_abs)
    mem_cache_abs = mem_total * 0.1
    disk_total = 256.0
    disk_used_abs = disk_total * disk_percent / 100.0
    disk_free_abs = max(0.0, disk_total - disk_used_abs)
    docker_running = 1 if scenario != "offline" else 0
    containers = []
    if docker_running:
        containers.append({"name": f"service-{index}-main"})
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "memory": {
            "total": mem_total,
            "used": mem_used_abs,
            "free": mem_free_abs,
            "cache": mem_cache_abs,
        },
        "cpu": {"total": cpu_total, "per_core": per_core},
        "disk": {
            "total": disk_total,
            "used": disk_used_abs,
            "free": disk_free_abs,
            "percent": disk_percent,
        },
        "docker": {"running_containers": docker_running, "containers": containers},
        "timestamp": ts,
    }


def validate_local(payload: dict):
    mem = payload["memory"]
    cpu = payload["cpu"]
    disk = payload["disk"]
    if not (0 <= cpu["total"] <= 100):
        raise ValueError("cpu.total fuera de rango")
    if any(c < 0 or c > 100 for c in cpu["per_core"]):
        raise ValueError("cpu.per_core fuera de rango")
    if mem["total"] <= 0:
        raise ValueError("memory.total inválida")
    if mem["used"] > mem["total"]:
        raise ValueError("memory.used > memory.total")
    if not (0 <= disk["percent"] <= 100):
        raise ValueError("disk.percent fuera de rango")


def send_metrics_loop(
    base_url: str,
    server_id: str,
    token: str,
    scenario: str,
    interval: int,
    iterations: int,
    verify_tls,
):
    url = base_url.rstrip("/") + "/api/metrics"
    session = requests.Session()
    for step in range(iterations):
        data = generate_metrics(scenario, index=hash(server_id) % 10, step=step)
        validate_local(data)
        payload = {"server_id": server_id}
        payload.update(data)
        try:
            r = session.post(
                url,
                json=payload,
                headers={"X-Auth-Token": token},
                timeout=10,
                verify=verify_tls,
            )
            ok = r.status_code == 200
            logging.info(
                "envio server_id=%s step=%s status=%s body=%s",
                server_id,
                step,
                r.status_code,
                r.text if not ok else "OK",
            )
        except Exception as e:
            logging.exception("error enviando métricas server_id=%s step=%s: %s", server_id, step, e)
        time.sleep(interval)


def validate_history(base_url: str, server_id: str, expected_min: int, verify_tls):
    url = (
        base_url.rstrip("/")
        + f"/api/metrics/history?server_id={server_id}&limit={expected_min * 2}"
    )
    r = requests.get(url, timeout=10, verify=verify_tls)
    if r.status_code != 200:
        raise RuntimeError(f"historial falló {server_id}: {r.status_code} {r.text}")
    data = r.json()
    count = len(data)
    logging.info("historial server_id=%s muestras=%s", server_id, count)
    if count < expected_min:
        raise RuntimeError(f"historial insuficiente para {server_id}: {count} < {expected_min}")


def parse_verify(value: str | None):
    if value is None or value == "":
        return True
    if value.lower() == "false":
        return False
    return value


def main():
    parser = argparse.ArgumentParser(description="Simulador local de métricas de prueba")
    parser.add_argument(
        "--server",
        default="http://localhost:8000",
        help="URL del backend de monitoreo",
    )
    parser.add_argument(
        "--services",
        type=int,
        default=3,
        help="Cantidad de servicios simulados",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Intervalo de envío en segundos",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=60,
        help="Cantidad de muestras por servicio",
    )
    parser.add_argument(
        "--scenario",
        choices=["normal", "stress-cpu", "memory-leak", "io-spikes"],
        default="normal",
        help="Escenario de carga simulado",
    )
    parser.add_argument(
        "--verify",
        default="",
        help="Ruta a CA/cert o 'false' para desactivar verificación TLS",
    )
    args = parser.parse_args()
    setup_logging()
    base_url = args.server
    services = args.services
    interval = args.interval
    iterations = args.iterations
    scenario = args.scenario
    verify_tls = parse_verify(args.verify)
    server_ids = []
    tokens = []
    for i in range(services):
        server_id = f"local-test-service-{i+1}"
        token = f"local-test-token-{i+1}"
        register_server(base_url, server_id, token)
        logging.info("servidor registrado server_id=%s", server_id)
        server_ids.append(server_id)
        tokens.append(token)
    threads = []
    for server_id, token in zip(server_ids, tokens):
        thread = threading.Thread(
            target=send_metrics_loop,
            name=f"svc-{server_id}",
            args=(base_url, server_id, token, scenario, interval, iterations, verify_tls),
            daemon=True,
        )
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    logging.info("simulación completada")


if __name__ == "__main__":
    main()
