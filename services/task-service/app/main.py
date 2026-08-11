from fastapi import FastAPI

app = FastAPI(title="MachingLearing GUI Task Service", version="0.1.0")


@app.get("/api/health")
def get_health() -> dict[str, str]:
    return {
        "status": "ready",
        "service": "ml-gui-task-service",
        "version": "0.1.0",
    }

