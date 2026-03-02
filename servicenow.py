import requests

SNOW_INSTANCE = "Your Instance"
SNOW_INCIDENT_URL = f"{SNOW_INSTANCE}/api/now/table/incident"
SNOW_USER = "your user ID"
SNOW_PASS = r"your password"
SNOW_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def build_snow_payload(enriched):
    urgency = "1" if enriched["priority"] == "P1" else "2"
    impact = "1" if enriched["priority"] == "P1" else "2"
    description = (
        f"{enriched.get('description', '')}\n\n"
        f"Affected instance: {enriched.get('affected_instance')}\n"
        f"Started at: {enriched.get('started_at')}\n"
        f"Runbook: {enriched.get('runbook')}"
    )
    return {
        "short_description": enriched.get("incident_title"),
        "description": description,
        "urgency": urgency,
        "impact": impact
    }

def create_incident(enriched):
    print(f"[SNOW] Attempting to create incident...")
    snow_payload = build_snow_payload(enriched)
    try:
        response = requests.post(
            SNOW_INCIDENT_URL,
            json=snow_payload,
            auth=(SNOW_USER, SNOW_PASS),
            headers=SNOW_HEADERS,
            timeout=10
        )
        result = response.json().get("result", {})
        incident_number = result.get("number")
        sys_id = result.get("sys_id")
        print(f"[SNOW] Incident created: {incident_number} (sys_id: {sys_id})")
        return sys_id
    except requests.exceptions.RequestException as e:
        print(f"[SNOW] Failed to reach ServiceNow: {e}")
        return None
