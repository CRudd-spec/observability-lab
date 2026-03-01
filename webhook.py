from flask import Flask, request, json
from datetime import datetime, timezone
import requests
import os

app = Flask(__name__)

ITSM_CRITICAL_URL = "http://localhost:5002/tickets/critical"
ITSM_STANDARD_URL = "http://localhost:5002/tickets/standard"
ITSM_RESOLVE_URL = "http://localhost:5002/tickets/resolve"

FINGERPRINT_FILE = os.path.join(os.path.dirname(__file__), "seen_fingerprints.json")

def load_fingerprints():
    if os.path.exists(FINGERPRINT_FILE):
        with open(FINGERPRINT_FILE, "r") as f:
            data = json.load(f)
            print(f"[DEDUP] Loaded {len(data)} fingerprints from disk")
            return set(data)
    print("[DEDUP] No fingerprint file found - starting fresh")
    return set()

def save_fingerprints(fingerprints):
    with open(FINGERPRINT_FILE, "w") as f:
        json.dump(list(fingerprints), f)

seen_fingerprints = load_fingerprints()

def enrich_alert(alert):
    enriched = {
        "incident_title": alert["labels"].get("alertname"),
        "severity": alert["labels"].get("severity"),
        "affected_instance": alert["labels"].get("instance"),
        "status": alert["status"],
        "summary": alert["annotations"].get("summary"),
        "description": alert["annotations"].get("description"),
        "started_at": alert.get("startsAt"),
        "enriched_at": datetime.now(timezone.utc).isoformat(),
        "runbook": "https://wiki.company.com/runbooks/" + alert["labels"].get("alertname", "unknown"),
        "priority": "P2" if alert["labels"].get("severity") == "warning" else "P1"
    }
    return enriched

def get_itsm_url(priority):
    if priority == "P1":
        print(f"[ROUTING] P1 detected - routing to CRITICAL queue")
        return ITSM_CRITICAL_URL
    elif priority == "P2":
        print(f"[ROUTING] P2 detected - routing to STANDARD queue")
        return ITSM_STANDARD_URL
    else:
        print(f"[ROUTING] Unknown priority '{priority}' - defaulting to STANDARD queue")
        return ITSM_STANDARD_URL

@app.route('/alert', methods=['POST'])
def alert():
    data = request.json
    print("\n--- Raw Payload Received ---")
    print(json.dumps(data, indent=2))

    print("\n--- Processing Alerts ---")
    for alert_item in data.get("alerts", []):
        fingerprint = alert_item.get("fingerprint")
        status = alert_item.get("status")
        alertname = alert_item["labels"].get("alertname")

        if status == "resolved":
            print(f"[RESOLVED] {alertname} - fingerprint {fingerprint}")
            if fingerprint in seen_fingerprints:
                try:
                    response = requests.post(ITSM_RESOLVE_URL, json={"fingerprint": fingerprint}, timeout=5)
                    print(f"ITSM resolve response: {response.status_code} - {response.json()}")
                    seen_fingerprints.discard(fingerprint)
                    save_fingerprints(seen_fingerprints)
                    print(f"[DEDUP] Fingerprint {fingerprint} cleared and file updated")
                except requests.exceptions.RequestException as e:
                    print(f"Failed to reach ITSM for resolve: {e}")
            else:
                print(f"[RESOLVED] Fingerprint {fingerprint} not in seen set - no ticket to close")
            continue

        if fingerprint in seen_fingerprints:
            print(f"[DEDUP] Skipping {alertname} - fingerprint {fingerprint} already ticketed")
            continue

        enriched = enrich_alert(alert_item)
        enriched["fingerprint"] = fingerprint
        print("\n--- Enriched Incident ---")
        print(json.dumps(enriched, indent=2))

        itsm_url = get_itsm_url(enriched["priority"])

        try:
            response = requests.post(itsm_url, json=enriched, timeout=5)
            ticket = response.json()
            print(f"ITSM response: {response.status_code} - {ticket}")
            seen_fingerprints.add(fingerprint)
            save_fingerprints(seen_fingerprints)
            print(f"[DEDUP] Fingerprint {fingerprint} stored and file updated")
        except requests.exceptions.RequestException as e:
            print(f"Failed to reach ITSM: {e}")

    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)