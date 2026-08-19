from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

app = FastAPI(title="Local Bank Operations Demo")

MEMBERS = {
    "12345": {"name": "John Smith", "savings": "8120.00", "checking": "2450.00"},
    "12346": {"name": "Sarah Williams", "savings": "4320.00", "checking": "1850.00"},
    "12347": {"name": "Michael Brown", "savings": "12400.00", "checking": "3100.00"},
}

HUMAN_EVENTS: list[dict] = []


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!doctype html>
    <html>
    <head>
      <title>Bank Operations Portal</title>
      <style>
        body { font-family: Arial; background:#f3f4f6; margin:0; }
        .top { background:#17324d; color:white; padding:18px 30px; }
        .wrap { max-width:900px; margin:35px auto; }
        .card { background:white; padding:25px; border-radius:8px; box-shadow:0 2px 10px #ddd; margin-bottom:20px; }
        label { display:block; font-weight:bold; margin-bottom:8px; }
        input { padding:10px; width:300px; border:1px solid #aaa; border-radius:4px; }
        button { padding:10px 18px; margin-left:8px; cursor:pointer; }
        .balance { font-size:20px; margin:12px 0; }
        .error { background:#fee2e2; padding:12px; margin-top:20px; }
        .notice { background:#fef3c7; padding:18px; border:2px solid #f59e0b; }
      </style>
    </head>
    <body>
      <div class="top"><h1>Bank Operations Portal</h1></div>
      <div class="wrap">
        <div class="card">
          <h2>Member Search</h2>
          <label for="member-id">Member ID</label>
          <input id="member-id" name="member_id" aria-label="Member ID" placeholder="Enter member ID">
          <button id="search" data-testid="search-button" onclick="searchMember()">Search</button>
          <div id="result"></div>
        </div>
      </div>
      <script>
        async function searchMember() {
          const id = document.getElementById('member-id').value;
          const result = document.getElementById('result');
          const response = await fetch('/api/member/' + encodeURIComponent(id));
          const data = await response.json();

          if (!response.ok) {
            result.innerHTML = '<div class="error"><strong>Member not found</strong><p>No member exists with ID ' + id + '.</p></div>';
            return;
          }

          result.innerHTML = `
            <div class="card" id="member-details">
              <h2>Member Details</h2>
              <p><strong>Member Name</strong></p>
              <p id="member-name">${data.name}</p>
              <p><strong>Checking Balance</strong></p>
              <p id="checking-balance" class="balance">$${data.checking}</p>
              <p><strong>Savings Balance</strong></p>
              <p id="savings-balance" class="balance">$${data.savings}</p>
              <button id="open-account" onclick="openAccount()">Open Account</button>
            </div>`;
        }

        function openAccount() {
          document.getElementById('result').insertAdjacentHTML('beforeend',
            '<div class="notice" id="intervention-required"><strong>INTERVENTION_REQUIRED</strong><br>Manual review is required before account creation.</div>');
        }
      </script>
    </body>
    </html>
    """


@app.get("/api/member/{member_id}")
def member(member_id: str):
    if member_id not in MEMBERS:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return MEMBERS[member_id]


@app.post("/api/human-events")
async def human_event(request: Request):
    event = await request.json()
    HUMAN_EVENTS.append(event)
    return {"ok": True}


@app.get("/api/human-events")
def human_events():
    return HUMAN_EVENTS


def main():
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
