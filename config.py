from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vyos.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# VyOS API config
def get_vyos_config():
    return {
        "VYOS_IP": os.getenv("VYOS_IP", "192.168.64.1"),
        "VYOS_API_PORT": int(os.getenv("VYOS_API_PORT", 443)),
        "VYOS_API_KEY_ID": os.getenv("VYOS_API_KEY_ID", "netauto"),
        "VYOS_API_KEY": os.getenv("VYOS_API_KEY", "changeme"),
    }
