# Smart Home Backend

## Overview
A minimalist backend for smart home device management and telemetry. Designed for integration with external smart home systems and as a backend for the [Smart Home Client (MAUI)](https://github.com/alex827a/smart-home-client-maui).

## Features
- REST API for device control and telemetry
- Simple endpoints for metrics and device toggling
- MQTT integration (optional)
- Swagger UI for API documentation
- Easy integration with SmartHome2 and other clients

## Requirements
- Python 3.10+
- Windows (instructions use PowerShell; adapt for Linux/Mac as needed)
- Dependencies listed in `requirements.txt`

## Installation

1. **Verify Python**
   ```powershell
   python --version
   ```

2. **Create and activate virtual environment**
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

   *Optional: For MQTT publishing support*
   ```powershell
   pip install asyncio-mqtt
   ```

4. **Run the server**
   ```powershell
   uvicorn server:app --reload --host 0.0.0.0 --port 8000
   ```

## Configuration
- Environment variables can be used to configure server behavior (e.g., port, MQTT broker settings).
- By default, MQTT messages are printed to the console if `asyncio-mqtt` is not installed.

## API Usage

- **Metrics:** [GET /api/metrics](http://127.0.0.1:8000/api/metrics)
- **Devices:** [GET /api/devices](http://127.0.0.1:8000/api/devices)
- **Toggle device (example, PowerShell):**
  ```powershell
  Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/devices/lamp/toggle
  ```
- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Integration with SmartHome2
- Configure SmartHome2 to poll `/api/metrics` for telemetry data.
- Use `POST /api/devices/{id}/toggle` to change device state.
- Minimal API: add authentication, CORS, and persistent storage as needed for your use case.

## Client Application
See the official client repository: [alex827a/smart-home-client-maui](https://github.com/alex827a/smart-home-client-maui)

## Development & Contribution

1. Fork the repository
2. Create a feature branch
3. Commit your changes and open a pull request

Feel free to open issues for bugs, feature requests, or questions.

## License
MIT License

## Contact
For support or feedback, open an [issue](https://github.com/alex827a/smart-home-backend/issues) or email: alexot422@gmail.com
