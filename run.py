import os
import uvicorn


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"--- LAUNCHING V3 PROTOCOL ON PORT {port} ---")
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
