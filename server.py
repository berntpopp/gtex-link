"""HTTP server entry point for GTEx-Link."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "gtex_link.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_config=None,  # Use our custom logging
    )
