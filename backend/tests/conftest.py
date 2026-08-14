import os
import sys
from pathlib import Path

# Set env SEBELUM import app apa pun
os.environ.setdefault("ERP_MCP_TRANSPORT", "stdio")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).parent / 'test.db'}")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # root repo (agar mcp_server dapat diimpor)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # parent root repo (fallback path tambahan)