# Smart Home Server Documentation

## Overview

This is a FastAPI-based smart home server that provides REST API endpoints for device management and metrics monitoring, with MQTT integration for real-time data publishing. The server supports TLS/mTLS authentication with Mosquitto MQTT broker and role-based access control.

### Features

- **REST API**: Device control and metrics retrieval
- **MQTT Integration**: Real-time publishing of metrics and device states
- **TLS/mTLS Security**: Certificate-based authentication
- **Role-based Access Control**: Admin and guest user roles
- **Device-dependent Metrics**: Temperature and power consumption vary based on device states
- **Async Architecture**: Non-blocking operations with asyncio

### Architecture

- **FastAPI**: Web framework for REST API
- **aiomqtt**: Async MQTT client for publishing
- **Mosquitto**: MQTT broker with TLS/mTLS support
- **mkcert**: Local CA for development certificates

## Installation and Setup

### Prerequisites

- Python 3.8+
- Mosquitto MQTT broker
- mkcert (for local certificates)
- PowerShell (for Windows setup scripts)

### Certificate Setup

1. Install mkcert:
   ```powershell
   choco install mkcert
   mkcert -install
   ```

2. Generate certificates:
   ```powershell
   # Broker certificate
   mkcert -cert-file broker-cert.pem -key-file broker-key.pem localhost 127.0.0.1

   # Client certificate
   mkcert -cert-file client-cert.pem -key-file client-key.pem fastapi-server

   # Move to Mosquitto directory
   mkdir C:\mosquitto\certs
   move broker-cert.pem, broker-key.pem, rootCA.pem C:\mosquitto\certs\
   ```

### Mosquitto Configuration

1. Install Mosquitto (Windows):
   ```powershell
   choco install mosquitto
   ```

2. Configure `C:\Program Files\mosquitto\mosquitto.conf`:
   ```conf
   per_listener_settings true

   listener 8883
   cafile C:\mosquitto\certs\rootCA.pem
   certfile C:\mosquitto\certs\broker-cert.pem
   keyfile C:\mosquitto\certs\broker-key.pem

   require_certificate true
   allow_anonymous false
   password_file C:\mosquitto\passwd
   acl_file C:\mosquitto\acl
   ```

3. Create password file:
   ```powershell
   mosquitto_passwd -c C:\mosquitto\passwd admin
   mosquitto_passwd C:\mosquitto\passwd guest
   ```

4. Create ACL file (`C:\mosquitto\acl`):
   ```
   user admin
   topic readwrite home/#
   topic readwrite home/+/state
   topic read $SYS/#

   user guest
   topic read home/system/metrics
   topic read home/+/state

   user fastapi-server
   topic readwrite home/#
   topic read $SYS/#
   ```

## Running the Server

### Environment Variables

Set the following environment variables (or use `start_server_with_mqtt_tls.ps1`):

```powershell
$env:MQTT_HOST = "127.0.0.1"
$env:MQTT_PORT = "8883"
$env:MQTT_USE_TLS = "true"
$env:MQTT_USER = "admin"  # or "fastapi-server"
$env:MQTT_PASS = "test"   # or "123"
$env:MQTT_CA_FILE = "C:\mosquitto\certs\rootCA.pem"
$env:MQTT_CERT_FILE = "E:\ProjectResume\server\client-cert.pem"
$env:MQTT_KEY_FILE = "E:\ProjectResume\server\client-key.pem"
```

### Start Commands

```powershell
# Using PowerShell script (recommended)
.\start_server_with_mqtt_tls.ps1

# Manual start
python run_server.py --host 127.0.0.1 --port 8001
```

### Verification

- Server starts on `http://127.0.0.1:8001`
- MQTT connection: `MQTT connected to 127.0.0.1:8883 (tls=True)`
- Swagger docs: `http://127.0.0.1:8001/docs`

## API Documentation

### Base URL
`http://localhost:8001/api`

### Endpoints

#### GET /api/metrics
Get current system metrics.

**Response:**
```json
{
  "temp": 25.3,
  "humidity": 45,
  "power": 390,
  "ts": "2025-10-22T12:34:56"
}
```

**Notes:**
- Temperature varies based on active devices
- Power consumption = base (250W) + device loads
- Published to MQTT topic `home/system/metrics` every 5 seconds

#### GET /api/devices
Get list of all devices.

**Response:**
```json
[
  {
    "id": "lamp",
    "name": "Lamp",
    "isOn": false,
    "lastSeen": "2025-10-22T12:34:56"
  },
  {
    "id": "hvac",
    "name": "HVAC",
    "isOn": true,
    "lastSeen": "2025-10-22T12:34:56"
  }
]
```

#### POST /api/devices/{id}/toggle
Toggle device state.

**Parameters:**
- `id`: Device ID (lamp, hvac, fan, heater)

**Response:**
```json
{
  "id": "lamp",
  "name": "Lamp",
  "isOn": true,
  "lastSeen": "2025-10-22T12:34:56"
}
```

**Notes:**
- Publishes state to MQTT topic `home/{id}/state` with retain=True
- Only admin users should have access to this endpoint

## MQTT Integration

### Topics

- `home/system/metrics`: Periodic metrics (every 5 seconds)
- `home/{device_id}/state`: Device state changes (retained)

### Connection Details

- **Broker**: 127.0.0.1:8883
- **TLS**: Required (mTLS)
- **Authentication**: Username/password + client certificate

### Client Examples

#### Admin Client (full access):
```powershell
mosquitto_sub -h 127.0.0.1 -p 8883 --cafile 'C:\mosquitto\certs\rootCA.pem' --cert 'E:\ProjectResume\server\client-cert.pem' --key 'E:\ProjectResume\server\client-key.pem' -u admin -P test -t 'home/#' -v
```

#### Guest Client (read-only):
```powershell
mosquitto_sub -h 127.0.0.1 -p 8883 --cafile 'C:\mosquitto\certs\rootCA.pem' --cert 'E:\ProjectResume\server\client-cert.pem' --key 'E:\ProjectResume\server\client-key.pem' -u guest -P 123 -t 'home/system/metrics' -v
```

## Authentication and Authorization

### MQTT Level

- **Certificates**: Required for all connections
- **Username/Password**: Required, checked against `password_file`
- **ACL**: Topic-based permissions per user

### API Level

Currently no authentication on HTTP endpoints. For production:

- Add JWT or API key authentication
- Implement role checking in endpoints
- Add CORS headers if needed

### User Roles

- **admin**: Full read/write access to all topics and devices
- **guest**: Read-only access to metrics and device states
- **fastapi-server**: Server's MQTT publishing account

## Testing

### HTTP API Tests

```powershell
# Get metrics
Invoke-WebRequest -Uri 'http://127.0.0.1:8001/api/metrics' -Method GET

# Get devices
Invoke-WebRequest -Uri 'http://127.0.0.1:8001/api/devices' -Method GET

# Toggle device
Invoke-WebRequest -Uri 'http://127.0.0.1:8001/api/devices/lamp/toggle' -Method POST
```

### MQTT Tests

```powershell
# Admin subscription
mosquitto_sub -h 127.0.0.1 -p 8883 --cafile 'C:\mosquitto\certs\rootCA.pem' --cert 'E:\ProjectResume\server\client-cert.pem' --key 'E:\ProjectResume\server\client-key.pem' -u admin -P test -t 'home/#' -v

# Guest subscription
mosquitto_sub -h 127.0.0.1 -p 8883 --cafile 'C:\mosquitto\certs\rootCA.pem' --cert 'E:\ProjectResume\server\client-cert.pem' --key 'E:\ProjectResume\server\client-key.pem' -u guest -P 123 -t 'home/system/metrics' -v

# Publish test
mosquitto_pub -h 127.0.0.1 -p 8883 --cafile 'C:\mosquitto\certs\rootCA.pem' --cert 'E:\ProjectResume\server\client-cert.pem' --key 'E:\ProjectResume\server\client-key.pem' -u admin -P test -t 'home/test' -m '{"test": "message"}'
```

## Troubleshooting

### Common Issues

1. **MQTT Connection Error: Not authorized**
   - Check username/password in environment variables
   - Verify certificates are valid
   - Check Mosquitto logs for ACL denials

2. **HTTP 404 Not Found**
   - Ensure `/api` prefix in URLs
   - Check server is running on correct port

3. **Certificate Errors**
   - Regenerate certificates with mkcert
   - Ensure rootCA.pem is trusted

4. **Guest doesn't see metrics**
   - Subscribe to specific topic `home/system/metrics`
   - Check ACL allows read access

### Logs

- **FastAPI**: Console output shows startup and MQTT connection status
- **Mosquitto**: Run with `-v` flag for detailed connection logs
- **Client**: Use `-v` flag with mosquitto_sub/pub for verbose output

## Development Notes

- Device states are stored in memory (reset on restart)
- Metrics are calculated dynamically based on device states
- Temperature impact: lamp (+0.8°C), hvac (-1.5°C), fan (+0.1°C), heater (+5.5°C)
- Power consumption: base 250W + device loads (lamp:10W, hvac:60W, fan:15W, heater:80W)

## Next Steps

- Add persistent storage for device states
- Implement JWT authentication for API
- Add health check endpoint
- Containerize with Docker
- Add unit tests
- Implement device discovery via MQTT
