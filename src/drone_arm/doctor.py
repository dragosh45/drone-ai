"""Check installed tools. The only ccx invocation allowed here is `-v`."""

from importlib import import_module, metadata
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

from .config import ConfigError, config_hash, load_config


def discover_ccx(configured: str | None) -> Path | None:
    """Explicit overrides must work: do not silently fall back to another binary."""
    override = configured or os.environ.get("DRONE_ARM_CCX")
    if override:
        found = shutil.which(str(Path(override).expanduser()))
        return Path(found).resolve() if found else None
    for name in ("ccx", "ccx_2.23", "ccx.exe"):
        found = shutil.which(name)
        if found:
            return Path(found).resolve()
    candidates = [
        Path("/Applications/FreeCAD.app/Contents/Resources/bin/ccx"),
        Path("/Applications/FreeCAD.app/Contents/MacOS/ccx"),
        Path.home() / "Applications/FreeCAD.app/Contents/Resources/bin/ccx",
    ]
    if sys.platform == "win32":
        for variable in ("ProgramFiles", "LOCALAPPDATA"):
            root = os.environ.get(variable)
            if root:
                candidates.extend(sorted(Path(root).glob("FreeCAD*/bin/ccx.exe")))
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    return None


def probe_ccx(executable: Path, *, threads: int, timeout: float) -> subprocess.CompletedProcess:
    """Probe the actual executable with explicit OpenMP setting and no shell."""
    return subprocess.run(
        [str(executable), "-v"], capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout, check=False,
        env={**os.environ, "OMP_NUM_THREADS": str(threads)},
    )


def ccx_version(result: subprocess.CompletedProcess) -> str | None:
    """Accept 201 only for an exact version response to our `-v` probe.

CalculiX's version branch calls Fortran stop(), which exits with 201. This
exception must never be reused as a success rule for a future FE job.
"""
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    match = re.fullmatch(r"This is Version ([0-9]+(?:\.[0-9]+)+)", output)
    if result.returncode in (0, 201) and match:
        return match.group(1)
    return None


def doctor(config_path: Path) -> int:
    """Print diagnostics and return 0 only if all Gate 0 runtime checks pass."""
    print("drone-arm doctor — Gate 0 (imports and version probe; no FE solve)")
    print(f"Platform: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python: {platform.python_version()} — {sys.executable}")
    passed = sys.version_info[:2] == (3, 12)
    if not passed:
        print("FAIL: Python 3.12 is required; activate the drone-ai conda environment.")
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"FAIL: {exc}\nDoctor: FAIL")
        return 1
    print(f"Config: {config_path.resolve()}")
    print(f"Config SHA256: {config_hash(config)}")
    print(f"Ranges frozen: {config['frozen']} (Gate 0 does not freeze ranges)")
    for distribution, module_name in (
        ("cadquery", "cadquery"), ("gmsh", "gmsh"), ("scikit-learn", "sklearn"),
        ("scipy", "scipy"), ("pandas", "pandas"), ("matplotlib", "matplotlib"),
        ("pytest", "pytest"), ("numpy", "numpy"),
    ):
        try:
            module = import_module(module_name)
            version = getattr(module, "__version__", None)
            if version is None:
                version = metadata.version(distribution)
            print(f"{distribution}: {version} — import OK")
        except Exception as exc:
            print(f"{distribution}: FAIL — {type(exc).__name__}: {exc}")
            passed = False
    solver = config["solver"]
    print(f"OMP_NUM_THREADS (ccx probe): {solver['omp_num_threads']}")
    executable = discover_ccx(solver["executable"])
    if executable is None:
        print("ccx: FAIL — executable not found; check config, DRONE_ARM_CCX or conda PATH.")
        passed = False
    else:
        print(f"ccx path: {executable}")
        try:
            result = probe_ccx(executable, threads=solver["omp_num_threads"],
                               timeout=solver["version_probe_timeout_s"])
            output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
            print(f"ccx -v (exit {result.returncode}):\n{output}")
            version = ccx_version(result)
            if version is None:
                print("FAIL: ccx version probe did not return a recognised version successfully.")
                passed = False
            else:
                print(f"CalculiX: {version} — version probe OK (201 is expected for upstream -v)")
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"ccx: FAIL — {exc}")
            passed = False
    print("Doctor: PASS" if passed else "Doctor: FAIL")
    return 0 if passed else 1
