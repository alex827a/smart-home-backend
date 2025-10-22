# PowerShell script to start FastAPI server with MQTT TLS/mTLS configuration
# Run this as: .\start_server_with_mqtt_tls.ps1

Write-Host "Starting FastAPI server with MQTT TLS/mTLS..." -ForegroundColor Cyan

# Set environment variables for MQTT TLS
$env:MQTT_HOST = "127.0.0.1"
$env:MQTT_PORT = "8883"
$env:MQTT_USE_TLS = "true"
$env:MQTT_USER='fastapi-server'
$env:MQTT_PASS='123'
$env:MQTT_CA_FILE = "C:\mosquitto\certs\rootCA.pem"
$env:MQTT_CERT_FILE = "E:\ProjectResume\server\client-cert.pem"
$env:MQTT_KEY_FILE = "E:\ProjectResume\server\client-key.pem"

Write-Host "`nMQTT Configuration:" -ForegroundColor Yellow
Write-Host "  Host: $env:MQTT_HOST"
Write-Host "  Port: $env:MQTT_PORT"
Write-Host "  TLS:  $env:MQTT_USE_TLS"
Write-Host "  CA:   $env:MQTT_CA_FILE"
Write-Host "  Cert: $env:MQTT_CERT_FILE"
Write-Host "  Key:  $env:MQTT_KEY_FILE"
Write-Host ""

# Start the server
python run_server.py
