# FastAPI + MQTT с TLS/mTLS — Инструкция по запуску

## Файловая структура

```
E:\ProjectResume\server\
├── server.py                          # FastAPI приложение с MQTT
├── run_server.py                      # Launcher для Windows
├── start_server_with_mqtt_tls.ps1    # Скрипт запуска с TLS переменными
├── broker-cert.pem                    # Сертификат брокера Mosquitto
├── broker-key.pem                     # Ключ брокера
├── client-cert.pem                    # Клиентский сертификат (для FastAPI)
└── client-key.pem                     # Клиентский ключ

C:\mosquitto\
├── certs\
│   ├── broker-cert.pem               # Копия сертификата брокера
│   ├── broker-key.pem                # Копия ключа брокера
│   └── rootCA.pem                    # Root CA (mkcert)
├── acl                               # Access Control List
└── passwd                            # Password file (пока пустой)

C:\Program Files\mosquitto\
└── mosquitto.conf                     # Конфигурация брокера (listener 8883, mTLS)
```

## 📋 Что уже сделано

✅ **Сертификаты созданы** (mkcert):
- Брокер: `broker-cert.pem` / `broker-key.pem`
- Клиент: `client-cert.pem` / `client-key.pem`
- Root CA: `rootCA.pem`

✅ **Mosquitto настроен**:
- Listener на порту **8883** (TLS)
- **mTLS** включён (`require_certificate true`)
- ACL и password файлы созданы

✅ **FastAPI поддерживает**:
- TLS подключение к MQTT
- Клиентский сертификат (mTLS)
- Переменные окружения для конфигурации

---

## 🚀 Запуск

### 1. Запустите Mosquitto broker

**Вариант A: Как Windows Service**
```powershell
Start-Service -Name mosquitto
```

**Вариант B: Вручную (для просмотра логов)**
```powershell
& 'C:\Program Files\mosquitto\mosquitto.exe' -c 'C:\Program Files\mosquitto\mosquitto.conf' -v
```

✅ Проверка — должны увидеть:
```
Opening ipv4 listen socket on port 8883.
mosquitto version 2.0.22 running
```

### 2. Запустите FastAPI сервер с TLS

```powershell
cd E:\ProjectResume\server
.\start_server_with_mqtt_tls.ps1
```

✅ Проверка — в логах FastAPI должно быть:
```
MQTT connected to 127.0.0.1:8883 (tls=True)
```

### 3. Протестируйте подключение MQTT клиентом

**Подписка на топики (mTLS):**
```powershell
mosquitto_sub -h 127.0.0.1 -p 8883 `
  --cafile C:\mosquitto\certs\rootCA.pem `
  --cert E:\ProjectResume\server\client-cert.pem `
  --key E:\ProjectResume\server\client-key.pem `
  -t 'home/#' -v
```

**Публикация (mTLS):**
```powershell
mosquitto_pub -h 127.0.0.1 -p 8883 `
  --cafile C:\mosquitto\certs\rootCA.pem `
  --cert E:\ProjectResume\server\client-cert.pem `
  --key E:\ProjectResume\server\client-key.pem `
  -t 'home/test' -m 'Hello from mTLS!'
```

---

## 🔧 Переменные окружения для FastAPI

Если не используете `start_server_with_mqtt_tls.ps1`, установите вручную:

```powershell
$env:MQTT_HOST = "127.0.0.1"
$env:MQTT_PORT = "8883"
$env:MQTT_USE_TLS = "true"
$env:MQTT_CA_FILE = "C:\mosquitto\certs\rootCA.pem"
$env:MQTT_CERT_FILE = "E:\ProjectResume\server\client-cert.pem"
$env:MQTT_KEY_FILE = "E:\ProjectResume\server\client-key.pem"

python run_server.py
```

---

## 📡 API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/metrics` | Возвращает текущие метрики (temp, humidity, power) и публикует в MQTT `home/system/metrics` |
| GET | `/api/devices` | Список всех устройств |
| POST | `/api/devices/{id}/toggle` | Переключить устройство (on/off) и опубликовать в MQTT `home/{id}/state` |

Примеры:
```powershell
# Получить метрики
Invoke-RestMethod http://localhost:8001/api/metrics

# Переключить лампу
Invoke-RestMethod -Method POST http://localhost:8001/api/devices/lamp/toggle
```

---

## 🔒 Безопасность (для production)

Текущая конфигурация — **dev-режим**. Для production:

1. **Используйте настоящий CA** вместо mkcert
2. **Создайте ACL с конкретными правами** (сейчас разрешено всё)
3. **Добавьте username/password** в `C:\mosquitto\passwd`:
   ```powershell
   & 'C:\Program Files\mosquitto\mosquitto_passwd.exe' -c C:\mosquitto\passwd myuser
   ```
4. **Включите JWT/OAuth2 для HTTP API** (добавьте в `server.py`)
5. **Храните секреты в переменных окружения** или secrets manager

---

## 🐛 Troubleshooting

### Mosquitto не стартует
```powershell
# Проверьте логи вручную
& 'C:\Program Files\mosquitto\mosquitto.exe' -c 'C:\Program Files\mosquitto\mosquitto.conf' -v
```

### FastAPI: "MQTT connection error: [WinError 10061]"
- Убедитесь, что Mosquitto запущен и слушает 8883
- Проверьте переменные окружения (`$env:MQTT_*`)

### "Error: Unable to load server certificate"
- Проверьте пути в `mosquitto.conf` (строка ~909-912)
- Убедитесь, что файлы существуют в `C:\mosquitto\certs`

### mosquitto_sub: "Connection Refused"
- Проверьте, что используете правильные пути к cert/key/CA
- Убедитесь, что порт 8883 открыт (`netstat -ano | Select-String 8883`)

---

## 📚 Дополнительные материалы

- [Mosquitto TLS documentation](https://mosquitto.org/man/mosquitto-tls-7.html)
- [mkcert](https://github.com/FiloSottile/mkcert)
- [FastAPI](https://fastapi.tiangolo.com/)
- [aiomqtt](https://github.com/sbtinstruments/aiomqtt)

---

## ✅ Чек-лист готовности

- [ ] Mosquitto запущен на порту 8883
- [ ] Сертификаты созданы и скопированы
- [ ] ACL и passwd файлы созданы
- [ ] FastAPI подключился к MQTT (логи показывают `MQTT connected`)
- [ ] `mosquitto_sub` видит сообщения из топика `home/#`
- [ ] HTTP API отвечает на `GET /api/metrics`
