"""Fetch stats data for verification."""
import httpx
import json
import random
import string

BASE = "http://localhost:8000"

suffix = "".join(random.choices(string.ascii_lowercase, k=6))
user = {"username": f"statsck_{suffix}", "password": "test123"}
httpx.post(f"{BASE}/api/auth/register", json=user, timeout=10)
r = httpx.post(f"{BASE}/api/auth/login", json=user, timeout=10)
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}
r = httpx.get(f"{BASE}/api/stats/samples", headers=h, timeout=10)
data = r.json()
print(json.dumps(data, ensure_ascii=False, indent=2))
