from fastapi import APIRouter, Depends
from schemas import VMProvisionRequest, VMProvisionResponse
from crud import get_api_key

router = APIRouter()

# Removed: duplicate and dummy /provision endpoint. All logic is in routers.py.
