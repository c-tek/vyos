from fastapi import FastAPI
import os
from routers import router

app = FastAPI(title="VyOS VM Network Automation API")

# Include all endpoints from the unified router
app.include_router(router)

@app.get("/")
def root():
    return {"message": "VyOS VM Network Automation API is running."}

if __name__ == "__main__":
    import uvicorn
    api_port = int(os.getenv("VYOS_API_PORT", 8800))
    uvicorn.run("main:app", host="0.0.0.0", port=api_port, reload=True)
