"""Emit an allowlisted upload manifest; never include local credentials/data."""
import base64
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
files = [root / name for name in ("README.md", "LICENSE", "requirements.txt", "manage.py", ".env.example", ".gitignore")]
for folder in ("config", "shop", "templates", "static", "scripts", "docs", ".github"):
    files.extend(p for p in (root / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
manifest = []
for file in sorted(files):
    binary = file.suffix == ".png"
    manifest.append({"path": file.relative_to(root).as_posix(), "binary": binary,
                     "content": "" if binary else file.read_text(encoding="utf-8-sig")})
print(json.dumps(manifest, ensure_ascii=True))
