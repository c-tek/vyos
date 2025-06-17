from passlib.context import CryptContext
import logging
import json
from logging.handlers import RotatingFileHandler

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# --- Audit Logging ---
def audit_log_action(user, action, result, details=None, level="INFO"):
    """Log an audit action for API events in structured JSON format."""
    log_entry = {
        "timestamp": None,  # Will be set by formatter
        "level": level,
        "user": user,
        "action": action,
        "result": result,
        "details": details,
    }
    logger = logging.getLogger("vyos_audit")
    logger.info(json.dumps(log_entry))

# --- Logging Setup Helper ---
def setup_audit_logger(logfile="vyos_api_audit.log", max_bytes=5*1024*1024, backup_count=5):
    """Configure the vyos_audit logger for structured JSON output and rotation."""
    logger = logging.getLogger("vyos_audit")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(logfile, maxBytes=max_bytes, backupCount=backup_count)
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            try:
                log_obj = json.loads(record.getMessage())
            except Exception:
                log_obj = {"message": record.getMessage()}
            log_obj["timestamp"] = self.formatTime(record, self.datefmt)
            log_obj["level"] = record.levelname
            return json.dumps(log_obj)
    handler.setFormatter(JsonFormatter())
    if not logger.handlers:
        logger.addHandler(handler)
    logger.propagate = False

# Call setup_audit_logger() at import time for default config
setup_audit_logger()