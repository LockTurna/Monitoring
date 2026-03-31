from flask import Flask, request, jsonify
import subprocess
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Mapping nama alert ke nama container yang perlu di-restart
ALERT_CONTAINER_MAP = {
    "VideotronDown":     "videotron",
    "PrometheusDown":   "prometheus",
    "GrafanaDown":      "grafana",
    "LokiDown":         "loki",
    "PromtailDown":     "promtail",
}

def restart_container(container_name: str):
    """Restart container via Docker socket."""
    try:
        result = subprocess.run(
            ["docker", "restart", container_name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logging.info(f"[REMEDIATION] Container '{container_name}' berhasil direstart.")
            return True, result.stdout.strip()
        else:
            logging.error(f"[REMEDIATION] Gagal restart '{container_name}': {result.stderr.strip()}")
            return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        logging.error(f"[REMEDIATION] Timeout saat restart '{container_name}'.")
        return False, "timeout"
    except Exception as e:
        logging.error(f"[REMEDIATION] Error: {e}")
        return False, str(e)


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return jsonify({"error": "No payload"}), 400

    alerts = data.get("alerts", [])
    results = []

    for alert in alerts:
        status      = alert.get("status", "")
        alert_name  = alert.get("labels", {}).get("alertname", "")
        instance    = alert.get("labels", {}).get("instance", "unknown")

        logging.info(f"[ALERT] {alert_name} | status={status} | instance={instance}")

        # Hanya proses alert yang sedang firing
        if status != "firing":
            results.append({"alert": alert_name, "action": "skipped (resolved)"})
            continue

        container = ALERT_CONTAINER_MAP.get(alert_name)
        if not container:
            logging.warning(f"[REMEDIATION] Tidak ada mapping untuk alert '{alert_name}'.")
            results.append({"alert": alert_name, "action": "no mapping found"})
            continue

        success, msg = restart_container(container)
        results.append({
            "alert":     alert_name,
            "container": container,
            "action":    "restart",
            "success":   success,
            "message":   msg,
        })

    return jsonify({"processed": len(alerts), "results": results}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
