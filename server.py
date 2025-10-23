from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from datetime import datetime
from random import randint, uniform
import sys
import os
import asyncio
import json
from typing import Set, Optional
import secrets
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass
try:
    from aiomqtt import Client, MqttError
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    Client = None
    MqttError = None

app = FastAPI()

# Аутентификация для SSE endpoints (fallback mode)
security = HTTPBasic()

# Учетные данные для SSE fallback (можно вынести в env)
SSE_USERS = {
    "guest": {
        "password": os.getenv("GUEST_PASSWORD", "123"),
        "role": "guest",
        "can_control": False  # Только чтение
    },
    "admin": {
        "password": os.getenv("ADMIN_PASSWORD", "admin123"),
        "role": "admin",
        "can_control": True  # Полный доступ
    }
}

def authenticate_sse_user(credentials: HTTPBasicCredentials = Depends(security)) -> dict:
    """
    Аутентификация для SSE endpoints.
    По умолчанию требует guest credentials для read-only доступа.
    """
    username = credentials.username
    user_info = SSE_USERS.get(username)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    # Проверяем пароль
    is_password_correct = secrets.compare_digest(
        credentials.password.encode("utf8"),
        user_info["password"].encode("utf8")
    )
    
    if not is_password_correct:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return {
        "username": username,
        "role": user_info["role"],
        "can_control": user_info["can_control"]
    }

def optional_authenticate_sse_user(
    credentials: Optional[HTTPBasicCredentials] = Depends(HTTPBasic(auto_error=False))
) -> dict:
    """
    Опциональная аутентификация для HTTP endpoints.
    Требует credentials только в SSE fallback режиме (когда MQTT недоступен).
    Когда MQTT работает - доступ свободный (без аутентификации).
    """
    # Если MQTT работает - аутентификация не требуется
    if mqtt_connected:
        return {
            "username": "mqtt-mode",
            "role": "admin",
            "can_control": True
        }
    
    # Если MQTT недоступен - требуем SSE аутентификацию
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required in SSE fallback mode",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    username = credentials.username
    user_info = SSE_USERS.get(username)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    # Проверяем пароль
    is_password_correct = secrets.compare_digest(
        credentials.password.encode("utf8"),
        user_info["password"].encode("utf8")
    )
    
    if not is_password_correct:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return {
        "username": username,
        "role": user_info["role"],
        "can_control": user_info["can_control"]
    }

# SSE (Server-Sent Events) для fallback подключения без MQTT
sse_clients: Set[asyncio.Queue] = set()

# devices (как у вас)
devices = {
    "lamp":   {"id": "lamp", "name": "Lamp", "isOn": False, "lastSeen": None},
    "hvac":   {"id": "hvac", "name": "HVAC", "isOn": True,  "lastSeen": None},
    "fan":    {"id": "fan",  "name": "Fan",  "isOn": False, "lastSeen": None},
    "heater": {"id": "heater", "name": "Heater", "isOn": True, "lastSeen": None},
}

BASE_POWER = 250
DEVICE_LOAD = {"lamp":10, "hvac":60, "fan":15, "heater":80}
DEVICE_TEMP_IMPACT = {"lamp":0.8, "hvac":-1.5, "fan":0.1, "heater":5.5}

# MQTT settings
import os
import ssl

# MQTT configuration from env (useful for TLS / auth)
MQTT_BROKER = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USER") or None
MQTT_PASSWORD = os.getenv("MQTT_PASS") or None
MQTT_USE_TLS = os.getenv("MQTT_USE_TLS", "false").lower() in ("1", "true", "yes")
MQTT_CA_FILE = os.getenv("MQTT_CA_FILE")
MQTT_CERT_FILE = os.getenv("MQTT_CERT_FILE")
MQTT_KEY_FILE = os.getenv("MQTT_KEY_FILE")

# очередь публикаций: элементы = (topic, payload_str, retain_bool, qos_int)
publish_queue: asyncio.Queue = asyncio.Queue(maxsize=200)

# Флаг состояния MQTT подключения
mqtt_connected = False

# Функция для отправки событий SSE клиентам
async def broadcast_to_sse_clients(topic: str, payload: str):
    """Отправляет событие всем подключенным SSE клиентам"""
    if not sse_clients:
        return
    
    event_data = {
        "topic": topic,
        "payload": json.loads(payload) if payload else None,
        "timestamp": datetime.now().isoformat()
    }
    
    dead_clients = set()
    for client_queue in sse_clients:
        try:
            client_queue.put_nowait(event_data)
        except asyncio.QueueFull:
            # Клиент не успевает обрабатывать события - отключаем
            dead_clients.add(client_queue)
        except Exception:
            dead_clients.add(client_queue)
    
    # Удаляем отключенных клиентов
    for dead_client in dead_clients:
        sse_clients.discard(dead_client)

# Фоновая задача для mqtt-publish
async def mqtt_publisher():
    global mqtt_connected
    if not MQTT_AVAILABLE:
        # Fallback: consume queue and log to console
        print("MQTT library not available - using fallback mode (SSE)")
        mqtt_connected = False
        while True:
            topic, payload, retain, qos = await publish_queue.get()
            print(f"MQTT (fallback): {topic} -> {payload} (retain={retain}, qos={qos})")
            # Отправляем через SSE если есть подключенные клиенты
            await broadcast_to_sse_clients(topic, payload)
    else:
        # Prepare SSL context if requested
        ssl_context = None
        if MQTT_USE_TLS:
            try:
                ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=MQTT_CA_FILE)
                # if client certificate provided, load it
                if MQTT_CERT_FILE and MQTT_KEY_FILE:
                    ssl_context.load_cert_chain(certfile=MQTT_CERT_FILE, keyfile=MQTT_KEY_FILE)
            except Exception as e:
                print("Failed to create SSL context for MQTT:", e)
                ssl_context = None

        while True:
            try:
                # aiomqtt.Client accepts tls_context in newer versions; try to pass it when available
                client_kwargs = {"hostname": MQTT_BROKER, "port": MQTT_PORT}
                if MQTT_USERNAME:
                    client_kwargs["username"] = MQTT_USERNAME
                if MQTT_PASSWORD:
                    client_kwargs["password"] = MQTT_PASSWORD
                if ssl_context is not None:
                    # aiomqtt.Client accepts tls_context parameter
                    client_kwargs["tls_context"] = ssl_context

                async with Client(**client_kwargs) as client:
                    print(f"MQTT connected to {MQTT_BROKER}:{MQTT_PORT} (tls={MQTT_USE_TLS})")
                    mqtt_connected = True
                    try:
                        while True:
                            topic, payload, retain, qos = await publish_queue.get()
                            try:
                                await client.publish(topic, payload.encode('utf-8'), qos=qos, retain=retain)
                                # Дублируем в SSE если есть подключенные клиенты (для гибридного режима)
                                if sse_clients:
                                    await broadcast_to_sse_clients(topic, payload)
                            except Exception as e:
                                print("MQTT publish failed:", e)
                    finally:
                        print(f"MQTT disconnected from {MQTT_BROKER}:{MQTT_PORT}")
                        mqtt_connected = False
            except Exception as me:
                # catch broad exceptions because MqttError may be None when import failed
                print("MQTT connection error:", me, "- switching to fallback mode (SSE)")
                mqtt_connected = False
                # В режиме fallback продолжаем обрабатывать очередь через SSE
                while not mqtt_connected:
                    try:
                        # Пытаемся переподключиться через 5 секунд
                        await asyncio.sleep(5)
                        break  # Выходим из внутреннего цикла для повторной попытки подключения
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        # Пока нет MQTT - обрабатываем через SSE
                        try:
                            topic, payload, retain, qos = await asyncio.wait_for(
                                publish_queue.get(), timeout=1.0
                            )
                            print(f"MQTT (fallback): {topic} -> {payload}")
                            await broadcast_to_sse_clients(topic, payload)
                        except asyncio.TimeoutError:
                            pass

# задача публиковать метрики периодически (опционно)
async def periodic_metrics_publisher(interval_sec: int = 5):
    while True:
        # генерируем метрики (можно вынести общую логику)
        on_power = sum(DEVICE_LOAD[k] for k, v in devices.items() if v["isOn"])
        base_temp = 20 + uniform(0, 6)
        device_temp = sum(DEVICE_TEMP_IMPACT.get(k, 0) for k, v in devices.items() if v["isOn"])
        temp = round(base_temp + device_temp, 1)
        metrics = {
            "temp": temp,
            "humidity": randint(35, 55),
            "power": BASE_POWER + on_power,
            "ts": datetime.now().isoformat(timespec="seconds")
        }
        # публикуем в топик, например home/system/metrics (подписка home/+/metrics поймает его)
        await publish_queue.put((f"home/system/metrics", json.dumps(metrics), False, 0))
        await asyncio.sleep(interval_sec)

# Запуск фоновых задач при старте/shutdown
@app.on_event("startup")
async def startup_event():
    # старт mqtt publisher
    app.state._mqtt_task = asyncio.create_task(mqtt_publisher())
    # опционально: периодический паблишер метрик
    app.state._metrics_task = asyncio.create_task(periodic_metrics_publisher(5))

@app.on_event("shutdown")
async def shutdown_event():
    # отменяем задачи аккуратно
    app.state._mqtt_task.cancel()
    app.state._metrics_task.cancel()
    await asyncio.gather(app.state._mqtt_task, app.state._metrics_task, return_exceptions=True)

@app.get("/api/metrics")
async def metrics(user: dict = Depends(optional_authenticate_sse_user)):
    """
    Получить текущие метрики системы.
    Требует аутентификацию только в SSE fallback режиме.
    """
    on_power = sum(DEVICE_LOAD[k] for k, v in devices.items() if v["isOn"])
    base_temp = 20 + uniform(0, 6)
    device_temp = sum(DEVICE_TEMP_IMPACT.get(k, 0) for k, v in devices.items() if v["isOn"])
    temp = round(base_temp + device_temp, 1)
    m = {
        "temp": temp,
        "humidity": randint(35, 55),
        "power": BASE_POWER + on_power,
        "ts": datetime.now().isoformat(timespec="seconds")
    }
    # также кладём в очередь для немедленной публикации (не обязательно, если есть periodic)
    await publish_queue.put((f"home/system/metrics", json.dumps(m), False, 0))
    return m

@app.get("/api/devices")
async def get_devices(user: dict = Depends(optional_authenticate_sse_user)):
    """
    Получить список всех устройств.
    Требует аутентификацию только в SSE fallback режиме.
    """
    now = datetime.now().isoformat(timespec="seconds")
    for d in devices.values():
        d["lastSeen"] = now
    # можно публиковать все устройства по одному топику, либо не публиковать
    return list(devices.values())

@app.post("/api/devices/{id}/toggle")
async def toggle(id: str, user: dict = Depends(optional_authenticate_sse_user)):
    """
    Переключить состояние устройства.
    - Когда MQTT работает: доступ свободный (без аутентификации).
    - Когда MQTT недоступен (SSE fallback): требует роли admin.
    """
    # Проверяем права на управление только в SSE fallback режиме
    if not mqtt_connected and not user["can_control"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{user['username']}' with role '{user['role']}' cannot control devices in SSE fallback mode. Admin role required."
        )
    
    if id not in devices:
        raise HTTPException(status_code=404, detail="Device not found")
    d = devices[id]
    d["isOn"] = not d["isOn"]
    d["lastSeen"] = datetime.now().isoformat(timespec="seconds")
    # публикуем состояние устройства с retained=True, QoS=1
    await publish_queue.put((f"home/{id}/state", json.dumps(d), True, 1))
    return d

# ============================================
# SSE Endpoint для fallback подключения
# ============================================

@app.get("/api/events/stream")
async def event_stream(request: Request, user: dict = Depends(authenticate_sse_user)):
    """
    Server-Sent Events endpoint для получения обновлений в реальном времени.
    Используется как fallback когда MQTT недоступен.
    Требует аутентификации (guest для read-only, admin для полного доступа).
    
    Пример подключения из MAUI:
    var handler = new HttpClientHandler {
        Credentials = new NetworkCredential("guest", "123")
    };
    var client = new HttpClient(handler);
    var stream = await client.GetStreamAsync("http://localhost:8000/api/events/stream");
    """
    client_queue = asyncio.Queue(maxsize=100)
    sse_clients.add(client_queue)
    
    async def event_generator():
        try:
            # Отправляем информацию о подключении
            connection_info = {
                "topic": "system/connection",
                "payload": {
                    "status": "connected",
                    "mqtt_available": mqtt_connected,
                    "mode": "mqtt" if mqtt_connected else "sse-fallback",
                    "user": user["username"],
                    "role": user["role"],
                    "can_control": user["can_control"]
                },
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(connection_info)}\n\n"
            
            # Отправляем текущее состояние устройств
            devices_state = {
                "topic": "system/initial-state",
                "payload": {
                    "devices": list(devices.values()),
                    "timestamp": datetime.now().isoformat()
                },
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(devices_state)}\n\n"
            
            # Постоянно отправляем события из очереди
            while True:
                # Проверяем, не отключился ли клиент
                if await request.is_disconnected():
                    break
                
                try:
                    # Ждем событие с таймаутом для периодической проверки подключения
                    event = await asyncio.wait_for(client_queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Отправляем keepalive каждые 30 секунд
                    keepalive = {
                        "topic": "system/keepalive",
                        "payload": {
                            "mqtt_connected": mqtt_connected,
                            "user": user["username"],
                            "role": user["role"]
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(keepalive)}\n\n"
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"SSE client error: {e}")
        finally:
            sse_clients.discard(client_queue)
            print(f"SSE client disconnected (user: {user['username']}, role: {user['role']}). Active clients: {len(sse_clients)}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Для nginx
        }
    )

@app.get("/api/status")
async def get_status():
    """
    Возвращает статус сервера и доступность MQTT.
    Клиент может использовать этот endpoint чтобы решить, подключаться через MQTT или SSE.
    """
    return {
        "mqtt_available": mqtt_connected,
        "mqtt_broker": MQTT_BROKER,
        "mqtt_port": MQTT_PORT,
        "mqtt_tls": MQTT_USE_TLS,
        "sse_clients_count": len(sse_clients),
        "recommended_mode": "mqtt" if mqtt_connected else "sse",
        "timestamp": datetime.now().isoformat()
    }