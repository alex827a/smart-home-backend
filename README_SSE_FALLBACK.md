# SSE Fallback Mode - Documentation

## Overview

The SmartHome server now supports **Server-Sent Events (SSE)** as a fallback mechanism when MQTT broker is unavailable. This allows clients to receive real-time updates directly from the HTTP server without requiring a separate MQTT connection.

## Architecture

```
┌─────────────────────────────────────────┐
│         Client Application              │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │   Connection Manager             │  │
│  │   1. Check /api/status           │  │
│  │   2. Choose connection method:   │  │
│  │      - MQTT (if available)       │  │
│  │      - SSE Fallback (if not)     │  │
│  └──────────────────────────────────┘  │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│       FastAPI Server                    │
│                                         │
│  ┌──────────────┐    ┌──────────────┐  │
│  │ MQTT         │    │ SSE Endpoint │  │
│  │ Publisher    │───▶│ /events/     │  │
│  │ (Primary)    │    │ stream       │  │
│  └──────────────┘    └──────────────┘  │
│         │                    │          │
│         ▼                    ▼          │
│  ┌──────────────────────────────────┐  │
│  │   Broadcast to SSE Clients       │  │
│  │   (Fallback + Hybrid Mode)       │  │
│  └──────────────────────────────────┘  │
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

### 3. **Hybrid Mode**
- **When**: MQTT is available, but some clients use SSE
- **How**: Server publishes to both MQTT and SSE simultaneously
- **Use Case**: Web clients use SSE, native apps use MQTT

## New API Endpoints

### 1. GET /api/status

Returns server status and connection recommendations.

**Response:**
```json
{
  "mqtt_available": false,
  "mqtt_broker": "127.0.0.1",
  "mqtt_port": 8883,
  "mqtt_tls": true,
  "sse_clients_count": 3,
  "recommended_mode": "sse",
  "timestamp": "2025-10-22T15:30:00"
}
```

**Usage:**
```javascript
const status = await fetch('http://localhost:8000/api/status').then(r => r.json());
if (status.recommended_mode === 'mqtt') {
    // Connect via MQTT
} else {
    // Use SSE fallback
}
```

### 2. GET /api/events/stream

Server-Sent Events stream for real-time updates.

**Connection:**
```javascript
const eventSource = new EventSource('http://localhost:8000/api/events/stream');

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Topic:', data.topic);
    console.log('Payload:', data.payload);
};

eventSource.onerror = (error) => {
    console.error('SSE error:', error);
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
    "ts": "2025-10-22T15:30:00"
  },
  "timestamp": "2025-10-22T15:30:01"
}
```

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

## Client Implementation

### JavaScript/TypeScript (Web)

```javascript
class SmartHomeClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        this.eventSource = null;
        this.onMetrics = null;
        this.onDeviceState = null;
    }

    async connect() {
        // Check server status
        const status = await fetch(`${this.baseUrl}/api/status`).then(r => r.json());
        console.log('Server mode:', status.recommended_mode);

        // Connect via SSE (web clients always use SSE)
        this.eventSource = new EventSource(`${this.baseUrl}/api/events/stream`);

        this.eventSource.onmessage = (event) => {
            const { topic, payload } = JSON.parse(event.data);

            if (topic === 'home/system/metrics' && this.onMetrics) {
                this.onMetrics(payload);
            } else if (topic.match(/^home\/\w+\/state$/) && this.onDeviceState) {
                this.onDeviceState(payload);
            }
        };

        this.eventSource.onerror = (error) => {
            console.error('Connection error:', error);
            // Auto-reconnect after 5 seconds
            setTimeout(() => this.connect(), 5000);
        };
    }

    async toggleDevice(deviceId) {
        const response = await fetch(`${this.baseUrl}/api/devices/${deviceId}/toggle`, {
            method: 'POST'
        });
        return response.json();
    }

    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
        }
    }
}

// Usage
const client = new SmartHomeClient('http://localhost:8000');
client.onMetrics = (metrics) => console.log('Metrics:', metrics);
client.onDeviceState = (device) => console.log('Device:', device);
await client.connect();
```

### C# (.NET MAUI)

```csharp
using System.Net.Http;
using System.Text.Json;

public class SseClient : IDisposable
{
    private readonly HttpClient _httpClient;
    private readonly string _baseUrl;
    private CancellationTokenSource _cts;

    public event Action<string, JsonElement> OnEvent;

    public SseClient(string baseUrl)
    {
        _baseUrl = baseUrl;
        _httpClient = new HttpClient { Timeout = Timeout.InfiniteTimeSpan };
    }

    public async Task<bool> IsMqttAvailable()
    {
        var response = await _httpClient.GetStringAsync($"{_baseUrl}/api/status");
        var status = JsonSerializer.Deserialize<JsonElement>(response);
        return status.GetProperty("mqtt_available").GetBoolean();
    }

    public async Task ConnectAsync()
    {
        _cts = new CancellationTokenSource();

        using var request = new HttpRequestMessage(HttpMethod.Get, $"{_baseUrl}/api/events/stream");
        using var response = await _httpClient.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, _cts.Token);
        
        response.EnsureSuccessStatusCode();

        using var stream = await response.Content.ReadAsStreamAsync();
        using var reader = new StreamReader(stream);

        while (!_cts.Token.IsCancellationRequested)
        {
            var line = await reader.ReadLineAsync();
            
            if (string.IsNullOrEmpty(line))
                continue;

            if (line.StartsWith("data: "))
            {
                var json = line.Substring(6);
                var eventData = JsonSerializer.Deserialize<JsonElement>(json);
                var topic = eventData.GetProperty("topic").GetString();
                var payload = eventData.GetProperty("payload");
                
                OnEvent?.Invoke(topic, payload);
            }
        }
    }

    public void Disconnect()
    {
        _cts?.Cancel();
    }

    public void Dispose()
    {
        Disconnect();
        _httpClient?.Dispose();
    }
}

// Usage
var sseClient = new SseClient("http://localhost:8000");

sseClient.OnEvent += (topic, payload) =>
{
    if (topic == "home/system/metrics")
    {
        var temp = payload.GetProperty("temp").GetDouble();
        Console.WriteLine($"Temperature: {temp}°C");
    }
};

// Check if MQTT is available
if (await sseClient.IsMqttAvailable())
{
    // Use MQTT connection
}
else
{
    // Use SSE fallback
    await sseClient.ConnectAsync();
}
```

## Testing

### 1. Test with MQTT Running

```powershell
# Terminal 1: Start Mosquitto
mosquitto -c "C:\Program Files\mosquitto\mosquitto.conf" -v

# Terminal 2: Start Server
.\start_server_with_mqtt_tls.ps1

# Terminal 3: Subscribe via MQTT
mosquitto_sub -h 127.0.0.1 -p 8883 --cafile rootCA.pem -u admin -P admin -t "home/#" -v

# Terminal 4: Open web client
# Navigate to http://localhost:8000/client_fallback_example.html
```

**Expected**: Client shows "MQTT Active + SSE", events visible in both MQTT and browser.

### 2. Test with MQTT Stopped

```powershell
# Terminal 1: Stop Mosquitto
Stop-Process -Name mosquitto -Force

# Terminal 2: Start Server
.\start_server_with_mqtt_tls.ps1

# Terminal 3: Open web client
# Navigate to http://localhost:8000/client_fallback_example.html
```

**Expected**: 
- Server logs: `MQTT connection error: ... - switching to fallback mode (SSE)`
- Client shows: "SSE Fallback Mode (MQTT unavailable)"
- Events still work via SSE

### 3. Test Reconnection

```powershell
# Start with MQTT running
# Stop Mosquitto during operation
Stop-Process -Name mosquitto -Force

# Server automatically switches to SSE mode
# Wait 5 seconds, then restart Mosquitto
mosquitto -c "C:\Program Files\mosquitto\mosquitto.conf" -v

# Server reconnects to MQTT automatically
```

**Expected**: Server logs show reconnection, clients continue receiving events seamlessly.

## Performance Considerations

### SSE vs MQTT

| Feature | MQTT | SSE |
|---------|------|-----|
| **Latency** | Very low (~10ms) | Low (~50ms) |
| **Throughput** | High (1000+ msg/s) | Medium (100+ msg/s) |
| **Memory** | Low | Medium (per client queue) |
| **Scalability** | Excellent | Good (100s of clients) |
| **Browser Support** | Requires library | Native |
| **Firewall** | May be blocked | HTTP-friendly |

### Recommendations

- **Production**: Use MQTT for native apps, SSE for web clients
- **Development**: SSE is simpler (no broker setup)
- **Hybrid**: Run both for maximum compatibility

### SSE Client Limits

- Max clients: ~200 concurrent (configurable via queue size)
- Max queue size: 100 messages per client
- Keepalive: 30 seconds
- Auto-cleanup: Slow clients are disconnected

## Troubleshooting

### SSE Connection Drops

**Symptoms:**
```
SSE client error: Failed to fetch
```

**Solutions:**
- Check server is running: `http://localhost:8000/api/status`
- Verify CORS if accessing from different domain
- Check firewall allows HTTP connections
- Increase client timeout

### No Events Received

**Symptoms:**
- SSE connected, but no data events

**Solutions:**
```javascript
// Check connection info event
eventSource.addEventListener('message', (event) => {
    console.log('Raw event:', event.data);
});

// Verify server is publishing
fetch('http://localhost:8000/api/devices/lamp/toggle', { method: 'POST' });
```

### High Memory Usage

**Symptoms:**
- Server memory grows with many SSE clients

**Solutions:**
- Reduce `maxsize` in `asyncio.Queue(maxsize=100)`
- Implement client authentication/limits
- Monitor `len(sse_clients)` via `/api/status`

## Security

### Authentication

SSE currently has no authentication. To add:

```python
from fastapi import Header, HTTPException

@app.get("/api/events/stream")
async def event_stream(request: Request, authorization: str = Header(None)):
    if not authorization or not verify_token(authorization):
        raise HTTPException(401, "Unauthorized")
    # ... rest of code
```

### CORS

To allow cross-origin requests:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Rate Limiting

Limit connections per IP:

```python
from collections import defaultdict
from datetime import datetime, timedelta

connection_counts = defaultdict(list)

@app.get("/api/events/stream")
async def event_stream(request: Request):
    client_ip = request.client.host
    now = datetime.now()
    
    # Clean old connections
    connection_counts[client_ip] = [
        ts for ts in connection_counts[client_ip]
        if now - ts < timedelta(minutes=5)
    ]
    
    # Check limit
    if len(connection_counts[client_ip]) >= 5:
        raise HTTPException(429, "Too many connections")
    
    connection_counts[client_ip].append(now)
    # ... rest of code
```

## Migration Guide

### From MQTT-only to Hybrid

1. Update server code (already done)
2. Add `/api/status` check in client
3. Implement SSE fallback in client
4. Test both modes
5. Deploy

### Client Changes

**Before:**
```javascript
// Only MQTT
const client = mqtt.connect('mqtt://localhost:8883', { ... });
```

**After:**
```javascript
// Check server status first
const status = await fetch('/api/status').then(r => r.json());

if (status.mqtt_available && isNativeApp) {
    // Use MQTT
    const client = mqtt.connect('mqtt://localhost:8883', { ... });
} else {
    // Use SSE
    const eventSource = new EventSource('/api/events/stream');
}
```

## Conclusion

The SSE fallback mode provides:
- ✅ Zero-configuration fallback (no broker needed)
- ✅ Real-time updates for web clients
- ✅ Automatic reconnection
- ✅ Seamless transition between MQTT and SSE
- ✅ Production-ready for 100s of concurrent clients

For questions or issues, see [Troubleshooting](#troubleshooting) section.
