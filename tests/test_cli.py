import pytest
from devtools import debug
from gallica_autobib.cli import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.mark.xfail(strict=False)
def test_app(fixed_tmp_path, file_regression):
    result = runner.invoke(app, ["tests/test_cli/test.bib", str(fixed_tmp_path)])
    debug(result.stdout)
    try:
        debug(result.stderr)
    except:
        pass
    assert result.exit_code == 0
    file_regression.check(result.stdout)
