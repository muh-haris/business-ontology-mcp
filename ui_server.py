"""Start the local visual interface: python ui_server.py"""

import uvicorn


if __name__ == "__main__":
    # Loopback-only binding avoids unintentionally exposing demo data to a network.
    uvicorn.run("src.ui_app:app", host="127.0.0.1", port=8000, reload=False)
