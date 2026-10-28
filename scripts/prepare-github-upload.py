"""Emit an allowlisted upload manifest; never include local credentials/data."""
import base64
import json
import hashlib
from pathlib import Path

root = Path(__file__).resolve().parent.parent
files = [root / name for name in ("README.md", "LICENSE", "requirements.txt", "manage.py", ".env.example", ".gitignore")]
for folder in ("config", "shop", "templates", "static", "scripts", "docs", ".github"):
    files.extend(p for p in (root / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
manifest = []
for file in sorted(files):
    binary = file.suffix == ".png"
    content = "" if binary else file.read_text(encoding="utf-8-sig")
    data = file.read_bytes() if binary else content.encode("utf-8")
    sha = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    manifest.append({"path": file.relative_to(root).as_posix(), "binary": binary,
                     "content": content, "sha": sha})
print(json.dumps(manifest, ensure_ascii=True))
