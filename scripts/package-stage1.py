"""Freeze stage-one sources and evidence without secrets or runtime data."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parent.parent
output = root / "dist" / "qinghe-shop-stage-01.zip"
output.parent.mkdir(exist_ok=True)
files = [root / name for name in (
    "README.md", "LICENSE", "requirements.txt", "manage.py", ".env.example", ".gitignore",
)]
for folder in ("config", "shop", "templates", "static", "scripts", "docs", ".github"):
    files.extend(p for p in (root / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
    for file in sorted(files):
        archive.write(file, file.relative_to(root).as_posix())
with ZipFile(output) as archive:
    assert archive.testzip() is None
    assert ".env" not in archive.namelist()
    assert not any(name.endswith(".sqlite3") for name in archive.namelist())
print(f"Created {output.name}: {len(files)} files, {output.stat().st_size} bytes")
