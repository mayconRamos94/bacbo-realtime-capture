import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
ENDPOINT_URL = os.getenv("ENDPOINT_URL")


if not DATABASE_URL:
    raise ValueError("DATABASE_URL not configured")

# ENDPOINT pode ser opcional