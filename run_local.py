from __future__ import annotations

import os

import uvicorn


if __name__ == "__main__":
    host = os.getenv("FRAUDLAB_HOST", "0.0.0.0")
    port = int(os.getenv("FRAUDLAB_PORT", "8080"))
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=False,
        access_log=False,
    )
