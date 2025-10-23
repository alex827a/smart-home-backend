# 🏠 SmartHome Integration Guide

## Overview

This guide covers the integration between the **FastAPI SmartHome Backend Server** and **.NET MAUI SmartHome Client**. The system supports multiple connection modes for maximum reliability and flexibility.

### System Architecture

```
┌─────────────────────────────────────────┐
│         .NET MAUI Client                │
│         (Cross-platform App)            │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │   Connection Manager             │   │
│  │   1. Check /api/status           │   │
│  │   2. Choose connection method:   │   │
│  │      - MQTT (preferred)          │   │
│  │      - SSE Fallback (backup)     │   │
│  └──────────────────────────────────┘   │
└─────────────┬───────────────────────────┘
              │ HTTP + MQTT/SSE
              │
              ▼
┌─────────────────────────────────────────┐
│       FastAPI Backend Server            │
│       (Python + AsyncIO)                │
│                                         │
│  ┌──────────────┐    ┌──────────────┐   │
│  │ MQTT         │    │ SSE Endpoint │   │
│  │ Publisher    │──▶│ /events/	  │   │
│  │ (Primary)    │    │ stream       │   │
│  └──────────────┘    └──────────────┘   │
│         │                    │          │
│         ▼                    ▼          │
│  ┌──────────────────────────────────┐   │
│  │   Broadcast to SSE Clients       │   │
│  │   (Fallback + Hybrid Mode)       │   │
│  └──────────────────────────────────┘   │
└─────────────┬─────────────────────┬─────┘
              │                     │
              │ MQTT over TLS       │ SSE over HTTP
              │ Port 8883           │ Port 8000/8001
              ▼                     ▼
        ┌─────────────────┐   ┌─────────────────┐
        │ Mosquitto       │   │ Direct HTTP     │
        │ Broker          │   │ Connection      │
        │ (Optional)      │   │ (Always works)  │
        └─────────────────┘   └─────────────────┘
```

### Connection Modes

#### 1. **MQTT Mode** (Primary - Recommended)
- **When**: Mosquitto broker is running and accessible
- **Protocol**: MQTT over TLS/mTLS (port 8883)
- **Advantages**:
  - Lowest latency (~10ms)
  - QoS levels (0, 1, 2)
  - Retained messages
  - Wildcard subscriptions
  - Network-wide pub/sub

#### 2. **SSE Fallback Mode** (Backup)
- **When**: MQTT broker is unavailable or client prefers HTTP
- **Protocol**: Server-Sent Events over HTTP (port 8000/8001)
- **Advantages**:
  - No additional infrastructure needed
  - Works through HTTP proxies/firewalls
  - Browser-native support
  - Automatic reconnection

#### 3. **Hybrid Mode** (Advanced)
- **When**: Both MQTT and SSE are available
- **Protocol**: Server publishes to both simultaneously
- **Use Case**: Web clients use SSE, native apps use MQTT

## MAUI Client Integration

### Prerequisites

- **.NET 8.0+** with MAUI workload
- **MQTTnet** NuGet package for MQTT support
- **System.Net.Http.Json** for HTTP API calls
- **Microsoft.Extensions.Logging** for logging



## Server Configuration

### Environment Variables

```powershell
# MQTT Configuration (Primary)
$env:MQTT_HOST = "127.0.0.1"
$env:MQTT_PORT = "8883"
$env:MQTT_USE_TLS = "true"
$env:MQTT_USER = "fastapi-server"
$env:MQTT_PASS = "123"
$env:MQTT_CA_FILE = "C:\mosquitto\certs\rootCA.pem"
$env:MQTT_CERT_FILE = "client-cert.pem"
$env:MQTT_KEY_FILE = "client-key.pem"

# Server Configuration
$env:HOST = "0.0.0.0"
$env:PORT = "8000"
```

### PowerShell Launch Script

```powershell
# start_server_with_mqtt_tls.ps1
$env:MQTT_HOST = "127.0.0.1"
$env:MQTT_PORT = "8883"
$env:MQTT_USE_TLS = "true"
$env:MQTT_USER = "fastapi-server"
$env:MQTT_PASS = "123"
$env:MQTT_CA_FILE = "C:\mosquitto\certs\rootCA.pem"
$env:MQTT_CERT_FILE = "E:\ProjectResume\server\client-cert.pem"
$env:MQTT_KEY_FILE = "E:\ProjectResume\server\client-key.pem"

python run_server.py --host 0.0.0.0 --port 8000
```

## Testing Integration

### 1. Full MQTT Mode

```powershell
# Terminal 1: Start Mosquitto
mosquitto -c "C:\Program Files\mosquitto\mosquitto.conf" -v

# Terminal 2: Start Server
.\start_server_with_mqtt_tls.ps1

# Terminal 3: Run MAUI App
# Should connect via MQTT, show "🟢 MQTT Connected"
```

### 2. SSE Fallback Mode

```powershell
# Terminal 1: Stop Mosquitto
Stop-Process -Name mosquitto -Force

# Terminal 2: Start Server
python run_server.py

# Terminal 3: Run MAUI App
# Should fallback to SSE/polling, show "🟡 SSE Fallback"
```

### 3. Device Control Test

```powershell
# Test HTTP API directly
Invoke-WebRequest -Method Post -Uri "http://localhost:8000/api/devices/lamp/toggle"

# Check MAUI app updates device state
# Check server logs for MQTT/SSE broadcasts
```

## Troubleshooting

### Connection Issues

#### MAUI App Shows "Disconnected"

**Check:**
1. Server is running: `http://localhost:8000/api/status`
2. Firewall allows connections
3. Correct base URL in app configuration

#### MQTT Connection Fails

**Check:**
1. Mosquitto is running: `Get-Process mosquitto`
2. Certificates are valid and accessible
3. ACL allows client connection
4. Username/password correct

#### SSE Fallback Not Working

**Check:**
1. HTTP connection works: `curl http://localhost:8000/api/metrics`
2. Server logs show SSE client connections
3. No CORS issues (add CORS middleware if needed)

### Performance Issues

#### High Latency in SSE Mode

**Solution:**
- Reduce polling interval (minimum 1 second)
- Implement WebSocket instead of SSE for better performance
- Use MQTT when available

#### Memory Usage

**Solution:**
- Monitor connection count via `/api/status`
- Implement connection limits
- Clean up disconnected clients

## Security Considerations

### MQTT Security

- Always use TLS in production
- Rotate certificates regularly
- Use strong passwords
- Restrict ACL permissions

### HTTP Security

- Add authentication to API endpoints
- Use HTTPS in production
- Implement rate limiting
- Validate input data

### MAUI App Security

- Store credentials securely (not in code)
- Use certificate pinning
- Implement logout functionality
- Handle network errors gracefully

## Deployment

### Development

```powershell
# Local development
.\start_server_with_mqtt_tls.ps1  # With MQTT
python run_server.py              # SSE only
```

### Production

1. **Server Deployment:**
   - Use reverse proxy (nginx/caddy)
   - Enable HTTPS
   - Configure firewall
   - Set up monitoring

2. **MAUI App Deployment:**
   - Build for target platforms
   - Configure production URLs
   - Set up app store distribution

3. **Mosquitto Deployment:**
   - Use production certificates
   - Configure persistent storage
   - Set up monitoring and logging

## API Reference

### Server Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Server status and connection info |
| GET | `/api/metrics` | Current system metrics |
| GET | `/api/devices` | List of all devices |
| POST | `/api/devices/{id}/toggle` | Toggle device state |
| GET | `/api/events/stream` | SSE event stream |

### MQTT Topics

| Topic | Direction | QoS | Description |
|-------|-----------|-----|-------------|
| `home/system/metrics` | Server → Client | 0 | Periodic metrics |
| `home/{device_id}/state` | Server → Client | 1 | Device state changes |

### SSE Events

| Event Type | Payload | Description |
|------------|---------|-------------|
| `system/connection` | Connection info | Client connected |
| `system/initial-state` | Device list | Initial device states |
| `home/system/metrics` | Metrics data | Metrics update |
| `home/{device_id}/state` | Device data | Device state change |

## Support

For issues and questions:

1. Check server logs for error messages
2. Verify network connectivity
3. Test with provided examples
4. Check firewall and proxy settings

## Version Compatibility

- **Server**: Python 3.10+, FastAPI 0.100+
- **MAUI Client**: .NET 8.0+, MQTTnet 4.3+
- **Mosquitto**: 2.0.18+ (optional)

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

