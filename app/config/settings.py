import os
from dotenv import load_dotenv

load_dotenv()

WS_URL = os.getenv("WS_URL")
DATABASE_URL = os.getenv("DATABASE_URL")
ENDPOINT_URL = os.getenv("ENDPOINT_URL")

if not WS_URL:
    raise ValueError("WS_URL not configured")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not configured")

# ENDPOINT pode ser opcional