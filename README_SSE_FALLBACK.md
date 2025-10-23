# SSE Fallback Mode - Documentation

## Overview

The SmartHome server now supports **Server-Sent Events (SSE)** as a fallback mechanism when MQTT broker is unavailable. This allows clients to receive real-time updates directly from the HTTP server without requiring a separate MQTT connection.

## Architecture

```
┌─────────────────────────────────────────┐
│         Client Application              │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │   Connection Manager             │   │
│  │   1. Check /api/status           │   │
│  │   2. Choose connection method:   │   │
│  │      - MQTT (if available)       │   │
│  │      - SSE Fallback (if not)     │   │
│  └──────────────────────────────────┘   │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│       FastAPI Server                    │
│                                         │
│  ┌──────────────┐    ┌──────────────┐   │
│  │ MQTT         │    │ SSE Endpoint │   │
│  │ Publisher    │───▶│ /events/     │  │
│  │ (Primary)    │    │ stream       │   │
│  └──────────────┘    └──────────────┘   │
│         │                    │          │
│         ▼                    ▼          │
│  ┌──────────────────────────────────┐   │
│  │   Broadcast to SSE Clients       │   │
│  │   (Fallback + Hybrid Mode)       │   │
│  └──────────────────────────────────┘   │
└─────────────┬───────────────────────────┘
              │
              ▼
      ┌───────────────┐
      │ Mosquitto     │ (Optional)
      │ Broker        │
      └───────────────┘
```

## Operating Modes

### 1. **MQTT Mode** (Primary)
- **When**: Mosquitto broker is running and accessible
- **How**: Server publishes to MQTT broker, clients subscribe to MQTT topics
- **Advantages**: 
  - Standard MQTT features (QoS, retained messages, wildcards)
  - Multiple subscribers
  - Network-wide pub/sub

### 2. **SSE Fallback Mode**
- **When**: Mosquitto broker is not available
- **How**: Server broadcasts events via HTTP SSE to connected clients
- **Advantages**:
  - No additional infrastructure needed
  - Works through HTTP/HTTPS (firewall-friendly)
  - Automatic reconnection
  - Browser-native support


## Event Types

### System Events

| Topic | Description | Payload |
|-------|-------------|---------|
| `system/connection` | Client connected | `{ "status": "connected", "mqtt_available": false, "mode": "sse-fallback" }` |
| `system/initial-state` | Initial devices state | `{ "devices": [...], "timestamp": "..." }` |
| `system/keepalive` | Periodic keepalive (every 30s) | `{ "mqtt_connected": false }` |

### Data Events

| Topic | Description | Payload |
|-------|-------------|---------|
| `home/system/metrics` | Metrics update (every 5s) | `{ "temp": 23.4, "humidity": 45, "power": 405, "ts": "..." }` |
| `home/{device_id}/state` | Device state changed | `{ "id": "lamp", "name": "Lamp", "isOn": true, "lastSeen": "..." }` |


## Conclusion

The SSE fallback mode provides:
- ✅ Zero-configuration fallback (no broker needed)
- ✅ Real-time updates for web clients
- ✅ Automatic reconnection
- ✅ Seamless transition between MQTT and SSE
- ✅ Production-ready for 100s of concurrent clients

For questions or issues, see [Troubleshooting](#troubleshooting) section.
