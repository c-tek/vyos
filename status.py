from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from config import SessionLocal
import crud
from schemas import VMStatusResponse, AllVMStatusResponse
from crud import get_api_key

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/vms/{machine_id}/ports/status", response_model=VMStatusResponse, dependencies=[Depends(get_api_key)])
def vm_ports_status(machine_id: str, db: Session = Depends(get_db)):
    vm = crud.get_vm_by_machine_id(db, machine_id)
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    ports = crud.get_vm_ports_status(db, vm)
    return ports

@router.get("/ports/status", response_model=list[AllVMStatusResponse], dependencies=[Depends(get_api_key)])
def all_ports_status(db: Session = Depends(get_db)):
    return crud.get_all_vms_status(db)
