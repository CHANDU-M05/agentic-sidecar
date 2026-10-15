"""Check tag, source versions, changelog, and built distribution metadata."""

from __future__ import annotations

import argparse
import ast
import email
import re
import subprocess
import tarfile
import zipfile
from pathlib import Path


def validate(root: Path, tag: str | None = None, distributions: Path | None = None) -> str:
    project = (root / "pyproject.toml").read_text()
    version = re.search(r'^version = "([^"]+)"$', project, re.MULTILINE)
    if version is None:
        raise ValueError("Package version is missing")
    expected = version.group(1)
    tree = ast.parse((root / "src/agentic_sidecar/__init__.py").read_text())
    runtime = next(
        (
            node.value.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets)
            and isinstance(node.value, ast.Constant)
        ),
        None,
    )
    if runtime != expected:
        raise ValueError("Runtime and package versions differ")
    changelog = (root / "CHANGELOG.md").read_text()
    if not re.search(
        rf"^## \[{re.escape(expected)}\] - \d{{4}}-\d{{2}}-\d{{2}}\s*$", changelog, re.MULTILINE
    ):
        raise ValueError(f"Missing dated changelog section for {expected}")
    if tag is not None:
        if tag != f"v{expected}":
            raise ValueError(f"Release tag must be v{expected}")
        tagged = subprocess.check_output(
            ["git", "rev-parse", f"refs/tags/{tag}^{{commit}}"], cwd=root, text=True
        ).strip()
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        if tagged != head:
            raise ValueError("Release tag must identify the checked-out commit")
    if distributions is not None:
        artifacts = list(distributions.glob("*.whl")) + list(distributions.glob("*.tar.gz"))
        if len(artifacts) != 2 or not any(p.suffix == ".whl" for p in artifacts):
            raise ValueError("Expected exactly one wheel and one source distribution")
        for path in artifacts:
            if path.suffix == ".whl":
                with zipfile.ZipFile(path) as archive:
                    name = next(
                        name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
                    )
                    metadata = archive.read(name).decode()
            else:
                with tarfile.open(path) as archive:
                    names = [
                        name
                        for name in archive.getnames()
                        if name.count("/") == 1 and name.endswith("/PKG-INFO")
                    ]
                    member = archive.extractfile(names[0])
                    if member is None:
                        raise ValueError("Missing source distribution metadata")
                    metadata = member.read().decode()
            parsed = email.message_from_string(metadata)
            if parsed["Version"] != expected or parsed["Name"] != "agentic-sidecar":
                raise ValueError(f"Distribution metadata mismatch: {path.name}")
    return expected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag")
    parser.add_argument("--dist", type=Path)
    args = parser.parse_args()
    version = validate(Path(__file__).resolve().parents[1], args.tag, args.dist)
    print(f"Release metadata validated: {version}")


if __name__ == "__main__":
    main()
