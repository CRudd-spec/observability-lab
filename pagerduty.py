from flask import Flask, request, json
from datetime import datetime, timezone
import requests

app = Flask(__name__)

MOCK_ITSM_URL = "http://localhost:5002"

SEVERITY_MAP = {
    "critical": "critical",
    "warning": "warning",
    "info": "info",
    "error": "error"
}

def build_pg_payload(alert):
    raw_severity = alert["labels"].get("severity", "info").lower()
    
    enriched = {
        "routing_key": "<integration_key>",
        "event_action": "trigger",
        "dedup_key": alert.get("fingerprint"),
        "payload": {
            "summary": alert["annotations"].get("summary", alert["labels"].get("alertname", "Unknown Alert")),
            "source": alert["labels"].get("instance", "alertmanager"),
            "severity": SEVERITY_MAP.get(raw_severity, "info"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "custom_details": {
                "alertname": alert["labels"].get("alertname"),
                "job": alert["labels"].get("job"),
                "description": alert["annotations"].get("description"),
                "status": alert.get("status")
            }
        },
        "links": [],
        "images": []
    }
    return enriched

@app.route('/alert', methods=['POST'])
def alert():
    data = request.json
    print("\n--- Raw Payload Received ---")
    print(json.dumps(data, indent=2))

    for alert in data.get("alerts", []):
        enriched = build_pg_payload(alert)
        print("\n--- Enriched Payload ---")
        print(json.dumps(enriched, indent=2))

        itsm_payload = {
            "incident_title": enriched["payload"]["summary"],
            "fingerprint": enriched["dedup_key"]
        }

        if enriched["payload"]["severity"] == "critical":
            endpoint = f"{MOCK_ITSM_URL}/tickets/critical"
        else:
            endpoint = f"{MOCK_ITSM_URL}/tickets/standard"

        try:
            response = requests.post(endpoint, json=itsm_payload, timeout=5)
            ticket = response.json()
            print(f"Mock ITSM: {response.status_code} - {ticket}")
        except requests.exceptions.RequestException as e:
            print(f"Mock ITSM Failed: {e}")

    return "ok", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)