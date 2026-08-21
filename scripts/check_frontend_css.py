import re

import httpx

r = httpx.get("http://localhost:3000/simulation", timeout=60)
print("status", r.status_code)
css = re.findall(r"/_next/static/css/[^\"']+", r.text)
print("css files", css)
if css:
    c = httpx.get(f"http://localhost:3000{css[0]}", timeout=30)
    print("css status", c.status_code, "len", len(c.text))
    print("has dark bg", "#0a0a0f" in c.text or "bg-ow-bg" in c.text)
