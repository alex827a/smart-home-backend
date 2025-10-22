""" from fastapi import FastAPI, HTTPException
from datetime import datetime
from random import randint, uniform

app = FastAPI()

# устройства и их энергопотребление
devices = {
    "lamp":   {"id": "lamp", "name": "Lamp", "isOn": False, "lastSeen": None},
    "hvac":   {"id": "hvac", "name": "HVAC", "isOn": True,  "lastSeen": None},
    "fan":    {"id": "fan",  "name": "Fan",  "isOn": False, "lastSeen": None},
    "heater": {"id": "heater", "name": "Heater", "isOn": True, "lastSeen": None},
}

# базовое энергопотребление и вклад каждого устройства
BASE_POWER = 250
DEVICE_LOAD = {
    "lamp": 10,
    "hvac": 60,
    "fan": 15,
    "heater": 80
}

# влияние каждого устройства на температуру (положительное — повышает, отрицательное — понижает)
DEVICE_TEMP_IMPACT = {
    "lamp": 0.8,
    "hvac": -1.5,   # предположим, что HVAC охлаждает
    "fan": 0.1,
    "heater": 5.5
}

@app.get("/api/metrics")
def metrics():
    # мощность теперь зависит от включённых устройств
    on_power = sum(DEVICE_LOAD[k] for k, v in devices.items() if v["isOn"])
    # базовая температура плюс случайный фоновый шум
    base_temp = 20 + uniform(0, 6)
    # вклад устройств, которые включены
    device_temp = sum(DEVICE_TEMP_IMPACT.get(k, 0) for k, v in devices.items() if v["isOn"])
    temp = round(base_temp + device_temp, 1)
    return {
        "temp": temp,
        "humidity": randint(35, 55),
        "power": BASE_POWER + on_power,
        "ts": datetime.now().isoformat(timespec="seconds")
    }

@app.get("/api/devices")
def get_devices():
    now = datetime.now().isoformat(timespec="seconds")
    for d in devices.values():
        d["lastSeen"] = now
    return list(devices.values())

@app.post("/api/devices/{id}/toggle")
def toggle(id: str):
    if id not in devices:
        raise HTTPException(status_code=404, detail="Device not found")
    d = devices[id]
    d["isOn"] = not d["isOn"]
    d["lastSeen"] = datetime.now().isoformat(timespec="seconds")
    return d """

from fastapi import FastAPI, HTTPException
from datetime import datetime
from random import randint, uniform
import sys
import asyncio
import json
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

# Фоновая задача для mqtt-publish
async def mqtt_publisher():
    if not MQTT_AVAILABLE:
        # Fallback: consume queue and log to console
        while True:
            topic, payload, retain, qos = await publish_queue.get()
            print(f"MQTT (fallback): {topic} -> {payload} (retain={retain}, qos={qos})")
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
                    try:
                        while True:
                            topic, payload, retain, qos = await publish_queue.get()
                            try:
                                await client.publish(topic, payload.encode('utf-8'), qos=qos, retain=retain)
                            except Exception as e:
                                print("MQTT publish failed:", e)
                    finally:
                        print(f"MQTT disconnected from {MQTT_BROKER}:{MQTT_PORT}")
            except Exception as me:
                # catch broad exceptions because MqttError may be None when import failed
                print("MQTT connection error:", me)
                await asyncio.sleep(5)

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

# Используем async endpoints, чтобы можно было await publish_queue.put(...)
@app.get("/api/metrics")
async def metrics():
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
async def get_devices():
    now = datetime.now().isoformat(timespec="seconds")
    for d in devices.values():
        d["lastSeen"] = now
    # можно публиковать все устройства по одному топику, либо не публиковать
    return list(devices.values())

@app.post("/api/devices/{id}/toggle")
async def toggle(id: str):
    if id not in devices:
        raise HTTPException(status_code=404, detail="Device not found")
    d = devices[id]
    d["isOn"] = not d["isOn"]
    d["lastSeen"] = datetime.now().isoformat(timespec="seconds")
    # публикуем состояние устройства с retained=True, QoS=1
    await publish_queue.put((f"home/{id}/state", json.dumps(d), True, 1))
    return d