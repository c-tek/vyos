from fastapi import FastAPI
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
