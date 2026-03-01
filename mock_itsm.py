from flask import Flask, request, jsonify
import json
from datetime import datetime, timezone

app = Flask(__name__)

critical_counter = 1
standard_counter = 1
open_tickets = []
resolved_tickets = []

@app.route('/', methods=['GET'])
def view_tickets():
    open_rows = ""
    for t in open_tickets:
        open_rows += f"<tr><td>{t['ticket_id']}</td><td>{t['queue']}</td><td>{t['title']}</td><td>{t['created_at']}</td></tr>"

    resolved_rows = ""
    for t in resolved_tickets:
        resolved_rows += f"<tr><td>{t['ticket_id']}</td><td>{t['queue']}</td><td>{t['title']}</td><td>{t['created_at']}</td><td>{t['resolved_at']}</td></tr>"

    html = f"""
    <html>
    <head><title>Mock ITSM</title></head>
    <body>
    <h2>Open Tickets ({len(open_tickets)})</h2>
    <table border="1" cellpadding="8">
        <tr><th>Ticket ID</th><th>Queue</th><th>Title</th><th>Created At</th></tr>
        {open_rows}
    </table>

    <br><br>

    <h2>Resolved Tickets ({len(resolved_tickets)})</h2>
    <table border="1" cellpadding="8">
        <tr><th>Ticket ID</th><th>Queue</th><th>Title</th><th>Created At</th><th>Resolved At</th></tr>
        {resolved_rows}
    </table>

    </body>
    </html>
    """
    return html

@app.route('/tickets/critical', methods=['POST'])
def create_critical_ticket():
    global critical_counter
    data = request.get_json()
    ticket_id = f"INC-CRIT-{critical_counter:05d}"
    critical_counter += 1
    print(f"\n[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] *** CRITICAL TICKET CREATED: {ticket_id} ***")
    print(json.dumps(data, indent=2))
    open_tickets.append({
        "ticket_id": ticket_id,
        "queue": "critical",
        "title": data.get("incident_title", "unknown"),
        "fingerprint": data.get("fingerprint"),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    })
    return jsonify({"ticket_id": ticket_id, "status": "created", "queue": "critical"}), 201

@app.route('/tickets/standard', methods=['POST'])
def create_standard_ticket():
    global standard_counter
    data = request.get_json()
    ticket_id = f"INC-STD-{standard_counter:05d}"
    standard_counter += 1
    print(f"\n[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] Standard ticket created: {ticket_id}")
    print(json.dumps(data, indent=2))
    open_tickets.append({
        "ticket_id": ticket_id,
        "queue": "standard",
        "title": data.get("incident_title", "unknown"),
        "fingerprint": data.get("fingerprint"),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    })
    return jsonify({"ticket_id": ticket_id, "status": "created", "queue": "standard"}), 201

@app.route('/tickets/resolve', methods=['POST'])
def resolve_ticket():
    data = request.get_json()
    fingerprint = data.get("fingerprint")

    ticket = next((t for t in open_tickets if t.get("fingerprint") == fingerprint), None)

    if not ticket:
        print(f"\n[RESOLVE] No open ticket found for fingerprint {fingerprint}")
        return jsonify({"status": "not_found"}), 404

    open_tickets.remove(ticket)
    ticket["resolved_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    resolved_tickets.append(ticket)

    print(f"\n[RESOLVE] Ticket {ticket['ticket_id']} resolved and moved to resolved queue")
    return jsonify({"ticket_id": ticket["ticket_id"], "status": "resolved"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)