"""HTTP server entry point for GTEx-Link."""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "gtex_link.app:app",
        host=os.getenv("GTEX_LINK_HOST", "127.0.0.1"),
        port=int(os.getenv("GTEX_LINK_PORT", "8000")),
        reload=os.getenv("GTEX_LINK_RELOAD", "True").lower() == "true",
        log_config=None,  # Use our custom logging
    )
