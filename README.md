# 🏠 SmartHome Backend Server

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MQTT](https://img.shields.io/badge/MQTT-TLS/mTLS-660066?logo=mqtt)](https://mqtt.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Production-ready FastAPI backend for smart home monitoring and control with real-time MQTT publishing, TLS/mTLS security, and role-based access control.

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Running the Server](#-running-the-server)
- [API Documentation](#-api-documentation)
- [MQTT Integration](#-mqtt-integration)
- [Security](#-security)
- [Project Structure](#-project-structure)
- [License](#-license)

---

## ✨ Features

### 🔥 Core Functionality
- **RESTful API**: FastAPI-powered HTTP endpoints for metrics and device control
- **Real-time MQTT**: Publish device states and metrics to MQTT broker with TLS/mTLS
- **SSE Fallback**: Server-Sent Events for real-time updates when MQTT is unavailable
- **Device Management**: Control smart home devices (lamp, HVAC, fan, heater)
- **Dynamic Metrics**: Temperature calculation based on active devices
- **Automatic Publishing**: Periodic metrics updates every 5 seconds

### 🔐 Security
- **MQTT TLS/SSL**: Encrypted communication with broker
- **mTLS Authentication**: Client certificate verification
- **Role-Based Access Control**: Admin, guest, and device-specific users
- **ACL Integration**: Mosquitto ACL enforcement for topic permissions
- **Password Authentication**: Secure credential management

### 🚀 Production Ready
- **Async/Await**: Non-blocking I/O with asyncio and aiomqtt
- **Windows Compatible**: WindowsSelectorEventLoopPolicy support
- **Auto-Reconnect**: MQTT connection resilience with backoff
- **Hybrid Mode**: Simultaneous MQTT + SSE broadcasting
- **Zero Configuration**: Works without MQTT broker (SSE fallback)
- **Queue Management**: Buffered MQTT publishing (200 message queue)
- **Environment Configuration**: 12-factor app compliance

---

## 🏗 Architecture

```
┌─────────────────────────────────────────┐
│         FastAPI Application             │
│                                         │
│  ┌──────────┐      ┌─────────────────┐  │
│  │ REST API │──────│ Device Manager  │  │
│  │  (HTTP)  │      │  (In-Memory)    │  │
│  └──────────┘      └─────────────────┘  │
│         │                    │          │
│         ▼                    ▼          │
│  ┌──────────────────────────────────┐   │
│  │   MQTT Publisher (aiomqtt)       │   │
│  │   - TLS/mTLS Support             │   │
│  │   - Auto-reconnect               │   │
│  │   - Async Queue (200 msgs)       │   │
│  └────────────┬─────────────────────┘   │
│               │                         │
│               ├─────────────────────┐   │
│               │                     │   │
│               ▼                     ▼   │
│  ┌────────────────────┐  ┌──────────┐   │
│  │ SSE Broadcaster    │  │ To MQTT  │   │ 
│  │ (Fallback Mode)    │  │ Broker   │   │
│  └────────────────────┘  └──────────┘   │
└──────────┬─────────────────────┬────────┘
           │                     │
           │ SSE (HTTP)          │ MQTT/TLS
           │                     │ Port 8883
           ▼                     ▼
  ┌─────────────────┐  ┌─────────────────────┐
  │ Web Clients     │  │ Mosquitto Broker    │
  │ (Browser SSE)   │  │ - TLS/mTLS          │
  └─────────────────┘  │ - ACL Authorization │
                       │ - Password Auth     │
                       └──────────┬──────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │ Native Clients      │
                       │ - MAUI App (MQTT)   │
                       │ - Admin Tools       │
                       └─────────────────────┘
```

**Operating Modes:**
- 🟢 **MQTT Mode**: Primary mode when broker is available
- 🟡 **SSE Fallback**: Automatic fallback when broker is down
- 🔵 **Hybrid Mode**: Both MQTT + SSE simultaneously (web + native clients)

> 💡 **New!** Server now works without MQTT broker using Server-Sent Events (SSE). Perfect for development or web-only deployments. See [README_SSE_FALLBACK.md](README_SSE_FALLBACK.md) for details.

### Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Framework** | FastAPI | 0.100+ |
| **Language** | Python | 3.10+ |
| **ASGI Server** | Uvicorn | Latest |
| **MQTT Client** | aiomqtt | Latest |
| **TLS/SSL** | OpenSSL | 1.1+ |

---

## 📦 Prerequisites

### Required Software

1. **Python 3.10+**
   ```powershell
   python --version
   # Should return 3.10.x or higher
   ```
   Download: https://www.python.org/downloads/

2. **Mosquitto MQTT Broker 2.0+**
   - Windows: https://mosquitto.org/download/
   - Default port: 8883 (TLS) or 1883 (plain)

3. **mkcert** (for certificate generation)
   ```powershell
   # Windows (with Scoop)
   scoop install mkcert
   
   # Or download from https://github.com/FiloSottile/mkcert/releases
   ```

### Optional Tools

- **Git**: Version control
- **Postman/Insomnia**: API testing
- **MQTT Explorer**: MQTT debugging

---

## 🔧 Installation

### 1. Clone the Repository

```powershell
git clone https://github.com/alex827a/smart-home-backend.git
cd smart-home-backend
```

### 2. Create Virtual Environment

```powershell
# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (Windows CMD)
.venv\Scripts\activate.bat
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

**Dependencies:**
- `fastapi` - Web framework
- `uvicorn[standard]` - ASGI server
- `aiomqtt` - Async MQTT client

### 4. Generate TLS Certificates

See [README_MQTT_TLS.md](README_MQTT_TLS.md) for detailed certificate setup.

**Quick Setup:**

```powershell
# Install local CA
mkcert -install

# Generate broker certificates
mkcert -cert-file C:\mosquitto\certs\broker-cert.pem `
       -key-file C:\mosquitto\certs\broker-key.pem `
       localhost 127.0.0.1 ::1

# Generate client certificates
mkcert -client `
       -cert-file client-cert.pem `
       -key-file client-key.pem `
       localhost 127.0.0.1

# Copy rootCA
Copy-Item "$(mkcert -CAROOT)\rootCA.pem" C:\mosquitto\certs\
```

### 5. Configure Mosquitto Broker

Edit `C:\Program Files\mosquitto\mosquitto.conf`:

```conf
# Enable per-listener settings
per_listener_settings true

# TLS Listener
listener 8883
certfile C:/mosquitto/certs/broker-cert.pem
keyfile C:/mosquitto/certs/broker-key.pem
cafile C:/mosquitto/certs/rootCA.pem

# Require client certificates
require_certificate true
use_identity_as_username false

# Password authentication
allow_anonymous false
password_file C:/mosquitto/passwd

# Access control
acl_file C:/mosquitto/acl
```

### 6. Create User Accounts

```powershell
# Create password file
mosquitto_passwd -c C:\mosquitto\passwd fastapi-server
# Enter password: 123

mosquitto_passwd C:\mosquitto\passwd admin
# Enter password: admin

mosquitto_passwd C:\mosquitto\passwd guest
# Enter password: 123
```

### 7. Configure ACL

Create `C:\mosquitto\acl` (UTF-8 without BOM):

```conf
# FastAPI server - full access
user fastapi-server
topic readwrite home/#
topic read $SYS/#

# Admin - full control
user admin
topic readwrite home/#
topic readwrite home/+/state
topic read $SYS/#

# Guest - read only
user guest
topic read home/system/metrics
topic read home/+/state
```

---

## ⚙ Configuration

### Environment Variables

Configure via environment or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_HOST` | `127.0.0.1` | Mosquitto broker hostname |
| `MQTT_PORT` | `1883` | Broker port (8883 for TLS) |
| `MQTT_USER` | `None` | MQTT username |
| `MQTT_PASS` | `None` | MQTT password |
| `MQTT_USE_TLS` | `false` | Enable TLS/SSL encryption |
| `MQTT_CA_FILE` | `None` | Path to CA certificate |
| `MQTT_CERT_FILE` | `None` | Path to client certificate |
| `MQTT_KEY_FILE` | `None` | Path to client private key |

### PowerShell Launch Script

Use `start_server_with_mqtt_tls.ps1` for easy TLS setup:

```powershell
# Edit paths in the script first
.\start_server_with_mqtt_tls.ps1
```

Script content:
```powershell
$env:MQTT_HOST = "127.0.0.1"
$env:MQTT_PORT = "8883"
$env:MQTT_USE_TLS = "true"
$env:MQTT_USER = "fastapi-server"
$env:MQTT_PASS = "123"
$env:MQTT_CA_FILE = "C:\mosquitto\certs\rootCA.pem"
$env:MQTT_CERT_FILE = "E:\ProjectResume\server\client-cert.pem"
$env:MQTT_KEY_FILE = "E:\ProjectResume\server\client-key.pem"

python run_server.py
```

---

## 🚀 Running the Server

### Method 1: PowerShell Script (Recommended)

```powershell
.\start_server_with_mqtt_tls.ps1
```

### Method 2: Manual Start

```powershell
# Set environment variables
$env:MQTT_HOST = "127.0.0.1"
$env:MQTT_PORT = "8883"
$env:MQTT_USE_TLS = "true"
$env:MQTT_USER = "fastapi-server"
$env:MQTT_PASS = "123"

# Run server
python run_server.py
```

### Method 3: Uvicorn Direct

```powershell
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

**Server will start on:**
- HTTP API: `http://localhost:8001`
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

---

## 📚 API Documentation

### Base URL

```
http://127.0.0.1:8001
```

### Endpoints

#### 1. Get Metrics

**GET** `/api/metrics`

Returns current system metrics (temperature, humidity, power).

**Response:**
```json
{
  "temp": 23.4,
  "humidity": 45,
  "power": 405,
  "ts": "2025-10-22T14:30:00"
}
```

**MQTT Publishing:**
- Topic: `home/system/metrics`
- QoS: 0
- Retain: false

**Temperature Calculation:**
- Base: 20-26°C (random)
- Device impacts:
  - Lamp: +0.8°C
  - HVAC: -1.5°C
  - Fan: +0.1°C
  - Heater: +5.5°C

**Power Consumption:**
- Base: 250W
- Device loads:
  - Lamp: 10W
  - HVAC: 60W
  - Fan: 15W
  - Heater: 80W

#### 2. Get Devices

**GET** `/api/devices`

Returns list of all devices with current states.

**Response:**
```json
[
  {
    "id": "lamp",
    "name": "Lamp",
    "isOn": false,
    "lastSeen": "2025-10-22T14:30:00"
  },
  {
    "id": "hvac",
    "name": "HVAC",
    "isOn": true,
    "lastSeen": "2025-10-22T14:30:00"
  }
]
```

#### 3. Toggle Device

**POST** `/api/devices/{id}/toggle`

Toggles device on/off state.

**Parameters:**
- `id` (path): Device ID (`lamp`, `hvac`, `fan`, `heater`)

**Example:**
```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/api/devices/lamp/toggle
```

**Response:**
```json
{
  "id": "lamp",
  "name": "Lamp",
  "isOn": true,
  "lastSeen": "2025-10-22T14:30:05"
}
```

**MQTT Publishing:**
- Topic: `home/{device_id}/state`
- QoS: 1
- Retain: true

**Error Responses:**
- `404 Not Found`: Device ID does not exist

#### 4. Get Server Status

**GET** `/api/status`

Returns server status and MQTT availability. Use this to determine connection method.

**Response:**
```json
{
  "mqtt_available": false,
  "mqtt_broker": "127.0.0.1",
  "mqtt_port": 8883,
  "mqtt_tls": true,
  "sse_clients_count": 3,
  "recommended_mode": "sse",
  "timestamp": "2025-10-22T14:30:00"
}
```

**Use Case:**
```javascript
const status = await fetch('/api/status').then(r => r.json());
if (status.recommended_mode === 'mqtt') {
    // Connect via MQTT
} else {
    // Use SSE fallback
}
```

#### 5. Real-time Event Stream (SSE)

**GET** `/api/events/stream`

Server-Sent Events endpoint for real-time updates without MQTT broker.

**Connection:**
```javascript
const eventSource = new EventSource('http://localhost:8001/api/events/stream');

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Topic:', data.topic);
    console.log('Payload:', data.payload);
};
```

**Event Format:**
```json
{
  "topic": "home/system/metrics",
  "payload": {
    "temp": 23.4,
    "humidity": 45,
    "power": 405,
    "ts": "2025-10-22T14:30:00"
  },
  "timestamp": "2025-10-22T14:30:01"
}
```

**Features:**
- 🔄 Auto-reconnection
- ⚡ Real-time updates (same as MQTT)
- 📱 Browser-native support
- 🔁 30-second keepalive
- 🌐 Works through firewalls

**See also:** [README_SSE_FALLBACK.md](README_SSE_FALLBACK.md) for detailed SSE documentation.


## 📡 MQTT Integration

### Topics

| Topic | Publisher | QoS | Retain | Description |
|-------|-----------|-----|--------|-------------|
| `home/system/metrics` | Server | 0 | false | Periodic metrics (every 5s) |
| `home/{device_id}/state` | Server | 1 | true | Device state changes |

### Subscription Examples

```bash
# Subscribe to all home topics (admin only)
mosquitto_sub -h 127.0.0.1 -p 8883 \
  --cafile C:\mosquitto\certs\rootCA.pem \
  --cert C:\mosquitto\certs\client-cert.pem \
  --key C:\mosquitto\certs\client-key.pem \
  -u admin -P admin \
  -t "home/#" -v

# Subscribe to metrics only (guest allowed)
mosquitto_sub -h 127.0.0.1 -p 8883 \
  --cafile C:\mosquitto\certs\rootCA.pem \
  --cert C:\mosquitto\certs\client-cert.pem \
  --key C:\mosquitto\certs\client-key.pem \
  -u guest -P 123 \
  -t "home/system/metrics" -v
```

### Message Formats

**Metrics:**
```json
{
  "temp": 23.4,
  "humidity": 45,
  "power": 405,
  "ts": "2025-10-22T14:30:00"
}
```

**Device State:**
```json
{
  "id": "lamp",
  "name": "Lamp",
  "isOn": true,
  "lastSeen": "2025-10-22T14:30:05"
}
```

### Connection Parameters

**TLS/mTLS:**
- Host: `127.0.0.1`
- Port: `8883`
- CA Certificate: `rootCA.pem`
- Client Certificate: `client-cert.pem`
- Client Key: `client-key.pem`
- Username/Password: Required (per ACL)

**Plain (Development Only):**
- Host: `127.0.0.1`
- Port: `1883`
- No TLS

---

## 🔐 Security

### User Roles

| User | Password | Permissions |
|------|----------|-------------|
| `fastapi-server` | `123` | Full read/write access to `home/#` |
| `admin` | `admin` | Full control, can read `$SYS/#` |
| `guest` | `123` | Read-only access to metrics and device states |

### ACL Rules

```conf
# Admin - full access
user admin
topic readwrite home/#
topic read $SYS/#

# Guest - read only
user guest
topic read home/system/metrics
topic read home/+/state

# FastAPI server - publisher
user fastapi-server
topic readwrite home/#
```

### Certificate Management

**Development:**
- Use mkcert for local CA and self-signed certificates
- Install CA: `mkcert -install`

**Production:**
- Use Let's Encrypt or commercial CA
- Regenerate certificates before expiry
- Store private keys securely

### Best Practices

1. ✅ Always use TLS in production
2. ✅ Enable `require_certificate true` for mTLS
3. ✅ Use strong passwords (not default ones!)
4. ✅ Restrict ACL permissions by topic
5. ✅ Rotate certificates periodically
6. ❌ Never commit `.pem` files to Git (already in `.gitignore`)

---

## 📂 Project Structure

```
smart-home-backend/
├── 📄 server.py                       # Main FastAPI application with MQTT + SSE
├── 📄 run_server.py                   # Windows-compatible launcher
├── 📄 start_server_with_mqtt_tls.ps1  # PowerShell launch script
├── 📄 requirements.txt                # Python dependencies
├── 📄 .gitignore                      # Git ignore rules
├── 📄 README.md                       # This file
├── 📄 README_MQTT_TLS.md              # TLS/mTLS setup guide
├── 📄 README_SSE_FALLBACK.md          # SSE fallback documentation
├── 📄 SMART_HOME_INTEGRATION.md       # Client integration guide
├── 🔐 broker-cert.pem                 # MQTT broker certificate (not in Git)
├── 🔐 broker-key.pem                  # MQTT broker private key (not in Git)
```

### Key Files

- **server.py**: FastAPI app with async MQTT publisher, SSE broadcaster, device management, and metrics calculation
- **run_server.py**: Sets `WindowsSelectorEventLoopPolicy` for Windows compatibility
- **start_server_with_mqtt_tls.ps1**: Sets environment variables and launches server with TLS
- **requirements.txt**: Python package dependencies
- **client_fallback_example.html**: Full-featured web client demonstrating SSE fallback


## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🔗 Related Projects

- **SmartHome MAUI Client**: https://github.com/alex827a/smart-home-client-maui.git
- **Mosquitto MQTT Broker**: https://mosquitto.org/
- **FastAPI Framework**: https://fastapi.tiangolo.com/

---

## 📞 Support

For detailed setup instructions, see:
- [SMART_HOME_INTEGRATION.md](SMART_HOME_INTEGRATION.md) - Client integration guide

---

**Made using FastAPI and Python**
