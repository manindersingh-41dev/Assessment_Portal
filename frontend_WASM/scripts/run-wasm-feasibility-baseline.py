#!/usr/bin/env python3
"""Run the feasibility corpus against the installed GCC as a reference baseline."""

import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "src/runner/wasm/feasibility-corpus.json"
TIMEOUT_SECONDS = 0.5


def compile_case(case, directory):
    source_path = directory / "main.c"
    executable_path = directory / "main"
    source_path.write_text(case["source"], encoding="utf-8")
    command = [
        "gcc", "-std=c11", "-O0", "-Wall", "-Wextra",
        str(source_path), "-lm", "-o", str(executable_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    return executable_path, result


def main():
    cases = json.loads(CORPUS.read_text(encoding="utf-8"))
    passed = 0
    failures = []

    for case in cases:
        with tempfile.TemporaryDirectory(prefix=f"wasm-baseline-{case['id']}-") as temp_dir:
            directory = Path(temp_dir)
            executable, compilation = compile_case(case, directory)

            if case.get("expect_compile_error"):
                ok = compilation.returncode != 0 and "error:" in compilation.stderr
                if not ok:
                    failures.append(f"{case['id']}: expected a compiler error")
                else:
                    passed += 1
                continue

            if compilation.returncode != 0:
                failures.append(f"{case['id']}: GCC compile failed: {compilation.stderr.strip()}")
                continue

            if case.get("expect_timeout"):
                try:
                    subprocess.run(
                        [str(executable)], input=case.get("input", ""), text=True,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        timeout=TIMEOUT_SECONDS, check=False,
                    )
                    failures.append(f"{case['id']}: expected execution to time out")
                except subprocess.TimeoutExpired:
                    passed += 1
                continue

            if case.get("expect_output_limit"):
                try:
                    subprocess.run(
                        [str(executable)], input=case.get("input", ""), text=True,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        timeout=TIMEOUT_SECONDS, check=False,
                    )
                    failures.append(f"{case['id']}: expected the infinite output program to keep running")
                except subprocess.TimeoutExpired:
                    passed += 1
                continue

            try:
                result = subprocess.run(
                    [str(executable)], input=case.get("input", ""), text=True,
                    capture_output=True, timeout=5, check=False,
                )
            except subprocess.TimeoutExpired:
                failures.append(f"{case['id']}: GCC execution timed out")
                continue

            expected = case.get("expected_stdout", "")
            if result.returncode != 0 or result.stdout != expected:
                failures.append(
                    f"{case['id']}: exit={result.returncode}, expected stdout={expected!r}, got {result.stdout!r}"
                )
                continue
            passed += 1

    print(f"GCC baseline: {passed}/{len(cases)} corpus cases passed")
    for failure in failures:
        print(f"FAIL: {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
