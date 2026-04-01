import subprocess
from pathlib import Path


def test_run_java_tests():
    """Compile and run the Java test suite, assert zero failures."""
    root = Path(__file__).resolve().parent.parent
    subprocess.check_call(
        ["javac", "BMSSP.java", "BMSSPTest.java"],
        cwd=root,
    )
    result = subprocess.run(
        ["java", "BMSSPTest"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    assert result.returncode == 0, f"Java tests failed:\n{result.stdout}\n{result.stderr}"
    assert "FAIL" not in result.stdout, "Java test suite reported failures"
