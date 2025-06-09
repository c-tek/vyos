from fastapi import HTTPException, status

class VyOSAPIError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=detail)

class ResourceAllocationError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_507_INSUFFICIENT_STORAGE):
        super().__init__(status_code=status_code, detail=detail)

class VMNotFoundError(HTTPException):
    def __init__(self, detail: str = "VM not found", status_code: int = status.HTTP_404_NOT_FOUND):
        super().__init__(status_code=status_code, detail=detail)

class PortRuleNotFoundError(HTTPException):
    def __init__(self, detail: str = "Port rule not found", status_code: int = status.HTTP_404_NOT_FOUND):
        super().__init__(status_code=status_code, detail=detail)

class APIKeyError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(status_code=status_code, detail=detail)