"""
Run the snippets in tests/typing_snippets/ through ty and mypy.

A snippet line ending in `# error` must get a diagnostic, and no other line may.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SNIPPETS = sorted((ROOT / "tests" / "typing_snippets").glob("*.py"))


def expected_lines(path):
    lines = path.read_text().splitlines()
    return {n for n, line in enumerate(lines, start=1) if line.rstrip().endswith("# error")}


def flagged_lines(path, output):
    pattern = re.compile(re.escape(path.name) + r":(\d+):(?:\d+:)? error")
    return {int(m.group(1)) for m in pattern.finditer(output)}


def find_tool(name):
    local = Path(sys.executable).parent / name
    return str(local) if local.exists() else shutil.which(name)


CHECKERS = {
    "ty": lambda path: [find_tool("ty"), "check", "--python", sys.executable,
                        "--output-format", "concise", str(path)],
    "mypy": lambda path: [sys.executable, "-m", "mypy", "--follow-imports=silent",
                          "--no-error-summary", "--hide-error-context", str(path)],
}


@pytest.mark.parametrize("checker", sorted(CHECKERS))
@pytest.mark.parametrize("path", SNIPPETS, ids=lambda p: p.name)
def test_snippet(checker, path):
    if checker == "ty" and find_tool("ty") is None:
        pytest.skip("ty is not installed")
    if checker == "mypy" and shutil.which("mypy") is None and find_tool("mypy") is None:
        pytest.skip("mypy is not installed")

    result = subprocess.run(CHECKERS[checker](path), cwd=ROOT, capture_output=True, text=True)
    output = result.stdout + result.stderr

    flagged = flagged_lines(path, output)
    expected = expected_lines(path)
    assert flagged == expected, (
        f"missed: {sorted(expected - flagged)}, false alarms: {sorted(flagged - expected)}\n{output}"
    )
