# run_server.py
import sys
import asyncio

# Принудительно выбрать селекторный event loop на Windows
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass

import uvicorn
import sys

if __name__ == "__main__":
    # Parse command line arguments
    host = "0.0.0.0"
    port = 8001
    
    # Simple argument parsing
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--host" and i + 1 < len(args):
            host = args[i + 1]
            i += 2
        elif args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        else:
            i += 1
    
    uvicorn.run("server:app", host=host, port=port, reload=False)