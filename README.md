Setup and run (Windows PowerShell)

1) Ensure Python 3.10+ is installed:

python --version

2) Create virtual environment and activate:

py -m venv .venv
.\.venv\Scripts\Activate.ps1

3) Install dependencies:

pip install -r requirements.txt

Note: asyncio-mqtt is optional for MQTT publishing. If not installed, MQTT messages will be logged to console instead.

4) Run the server:

uvicorn server:app --reload --host 0.0.0.0 --port 8000

5) Test endpoints in browser or HTTP client:

http://127.0.0.1:8000/api/metrics
http://127.0.0.1:8000/api/devices

Toggle device (example using PowerShell's Invoke-RestMethod):

Invoke-RestMethod -Method Post 
-Uri http://127.0.0.1:8000/api/devices/lamp/toggle

Swagger UI:

http://127.0.0.1:8000/docs

Integration with SmartHome2:

- Configure SmartHome2 to poll /api/metrics occasionally for telemetry.
- Use POST /api/devices/{id}/toggle to change device state.
- The API is intentionally minimal: add auth, CORS, and persistent storage as needed.
