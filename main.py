from fastapi import FastAPI
import os
from routers import vms, ports, status, mcp

app = FastAPI(title="VyOS VM Network Automation API")

# Include routers
app.include_router(vms.router, prefix="/vms", tags=["VMs"])
app.include_router(ports.router, prefix="/ports", tags=["Ports"])
app.include_router(status.router, prefix="/status", tags=["Status"])
app.include_router(mcp.router, prefix="/mcp", tags=["MCP"])

@app.get("/")
def root():
    return {"message": "VyOS VM Network Automation API is running."}

if __name__ == "__main__":
    import uvicorn
    api_port = int(os.getenv("VYOS_API_PORT", 8800))
    uvicorn.run("main:app", host="0.0.0.0", port=api_port, reload=True)
