"""Compile Python fences and verify local Markdown file links."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

root = Path(__file__).resolve().parents[1]
paths = [
    root / "README.md",
    root / "ROADMAP.md",
    *sorted((root / "website" / "docs").glob("*.md")),
    *sorted((root / "website" / "usecases").glob("*.md")),
    *sorted((root / "examples").glob("*.md")),
]
count = 0
for path in paths:
    content = path.read_text()
    for code in re.findall(r"```python\s*\n(.*?)```", content, re.DOTALL):
        compile(code, str(path), "exec")
        count += 1
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
        target = target.split("#", 1)[0].strip("<>")
        if not target or ":" in target or target.startswith("/"):
            continue
        if not (path.parent / unquote(target)).exists():
            raise SystemExit(f"Broken local link in {path.relative_to(root)}: {target}")
print(f"Validated {count} Python fences and local file links across {len(paths)} documents")
