"""Interactive prompt contracts with deterministic terminal input."""

from typer.testing import CliRunner

from agentic_sidecar.cli.main import app


def test_approval_demo_defaults_to_rejection():
    result = CliRunner().invoke(app, ["approval-demo"], input="\n\n")
    assert result.exit_code == 0
    assert "Selected reject; no tool executed" in result.stdout


def test_approval_demo_approve_once():
    result = CliRunner().invoke(app, ["approval-demo"], input="approve_once\nreviewed\n")
    assert result.exit_code == 0
    assert "Selected approve_once" in result.stdout
