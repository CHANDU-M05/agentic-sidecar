"""Release checks reject version/tag/changelog mismatches before publication."""

import importlib.util
from pathlib import Path

import pytest

path = Path(__file__).resolve().parents[1] / "scripts/validate_release.py"
spec = importlib.util.spec_from_file_location("validate_release", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture_project(tmp_path):
    (tmp_path / "src/agentic_sidecar").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text('version = "0.6.1"\n')
    (tmp_path / "src/agentic_sidecar/__init__.py").write_text('__version__ = "0.6.1"\n')
    (tmp_path / "CHANGELOG.md").write_text("## [0.6.1] - 2026-10-10\nFeatures.\n")
    return tmp_path


def test_matching_release_versions(tmp_path):
    assert module.validate(fixture_project(tmp_path)) == "0.6.1"


@pytest.mark.parametrize("case", ["runtime", "changelog", "tag"])
def test_release_mismatch_rejected(tmp_path, case):
    root = fixture_project(tmp_path)
    if case == "runtime":
        (root / "src/agentic_sidecar/__init__.py").write_text('__version__ = "0.6.0"')
    elif case == "changelog":
        (root / "CHANGELOG.md").write_text("## [Unreleased]")
    with pytest.raises(ValueError):
        module.validate(root, tag="v0.6.0" if case == "tag" else None)


@pytest.mark.parametrize("version", ["0.6.1", "0.6.0"])
def test_distribution_metadata_validation(tmp_path, version):
    import io
    import tarfile
    import zipfile

    root = fixture_project(tmp_path)
    distributions = root / "dist"
    distributions.mkdir()
    metadata = f"Name: agentic-sidecar\nVersion: {version}\n".encode()
    with zipfile.ZipFile(distributions / "package.whl", "w") as archive:
        archive.writestr("agentic_sidecar.dist-info/METADATA", metadata)
    with tarfile.open(distributions / "package.tar.gz", "w:gz") as archive:
        member = tarfile.TarInfo("agentic_sidecar/PKG-INFO")
        member.size = len(metadata)
        archive.addfile(member, io.BytesIO(metadata))
    if version == "0.6.1":
        assert module.validate(root, distributions=distributions) == version
    else:
        with pytest.raises(ValueError, match="metadata mismatch"):
            module.validate(root, distributions=distributions)
