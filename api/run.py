import uvicorn

from settings.conf import settings

if __name__ == "__main__":
    uvicorn.run(
        "app:get_app",
        host="0.0.0.0",
        port=8000,
        log_level=settings.log_level,
        reload=settings.app_reload,
        factory=True,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
