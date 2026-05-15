"""Entry point — starts the uvicorn server."""
import uvicorn

if __name__ == "__main__":
    from app.config import settings

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
