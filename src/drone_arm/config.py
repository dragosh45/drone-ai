"""Load the study contract, check units/relationships, and hash its contents.

This validates configuration, not individual CAD geometries. Geometry generation
and its hole/ligament checks belong to Gate 1.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """The study file cannot be interpreted as a consistent configuration."""


def _at(data: dict[str, Any], path: str) -> Any:
    value: Any = data
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            raise ConfigError(f"Missing configuration field: {path}")
        value = value[key]
    return value


def _number(value: Any, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{label} must be a number")
    if not math.isfinite(value) or (positive and value <= 0):
        raise ConfigError(f"{label} must be finite" + (" and positive" if positive else ""))
    return float(value)


def _positive(data: dict[str, Any], path: str) -> float:
    return _number(_at(data, path), path, positive=True)


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ConfigError(f"{label} must be an integer >= {minimum}")
    return value


def _range(value: Any, label: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise ConfigError(f"{label} must contain two bounds")
    low, high = (_number(v, label) for v in value)
    if low >= high:
        raise ConfigError(f"{label} lower bound must be less than upper bound")
    return low, high


def _vector(value: Any, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ConfigError(f"{label} must have three components")
    return [_number(v, label) for v in value]


def _same(actual: float, expected: float, label: str) -> None:
    if not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=0.0):
        raise ConfigError(f"{label}: got {actual:g}, expected {expected:g}")


def validate_config(data: dict[str, Any]) -> None:
    """Reject a malformed or physically inconsistent study contract."""
    if not isinstance(data, dict):
        raise ConfigError("The JSON root must be an object")
    if _integer(_at(data, "schema_version"), "schema_version", minimum=1) != 1:
        raise ConfigError("Only schema_version 1 is supported")
    if not isinstance(_at(data, "study_id"), str) or not data["study_id"].strip():
        raise ConfigError("study_id must be a nonempty string")
    if not isinstance(_at(data, "frozen"), bool):
        raise ConfigError("frozen must be true or false")
    expected_units = {
        "length": "mm", "force": "N", "stress": "MPa", "time": "s",
        "solver_mass": "tonne", "density": "tonne/mm^3", "reported_mass": "g",
        "moment": "N*mm", "frequency": "Hz",
    }
    if _at(data, "units") != expected_units:
        raise ConfigError("units must use mm, N, MPa, s, tonnes and grams as documented")
    for path in ("sources", "supports", "outputs", "seeds", "solver"):
        if not isinstance(_at(data, path), dict):
            raise ConfigError(f"{path} must be an object")

    for path in (
        "interfaces.reach_mm", "interfaces.outer_width_mm", "interfaces.tip_mass_g",
        "interfaces.root_pad.length_mm", "interfaces.motor_pad.length_mm",
        "interfaces.motor_pad.width_mm", "material.youngs_modulus_MPa",
        "material.yield_reference_MPa", "material.interlayer_adhesion_MPa",
        "limits.tip_deflection_mm", "limits.stress_exclusion_beyond_root_face_mm",
        "solver.version_probe_timeout_s",
    ):
        _positive(data, path)
    for path in (
        "interfaces.root_pad.width_mm", "interfaces.root_pad.height_mm",
        "interfaces.motor_pad.thickness_mm", "mesh.hole_refinement_factor",
    ):
        if _at(data, path) is not None:
            _positive(data, path)
    nu = _number(_at(data, "material.poisson_ratio"), "material.poisson_ratio")
    if not -1 < nu < 0.5:
        raise ConfigError("material.poisson_ratio must be between -1 and 0.5")
    if _at(data, "material.model") != "isotropic_linear_elastic":
        raise ConfigError("Only the documented isotropic material model is supported")
    rho = _positive(data, "material.density_g_cm3")
    _same(_positive(data, "material.density_kg_m3"), rho * 1000, "density kg/m3")
    _same(_positive(data, "material.density_tonne_mm3"), rho * 1e-9, "density tonne/mm3")

    material_factor = _positive(data, "factors.material_process_factor")
    _same(_positive(data, "limits.body_stress_MPa"),
          data["material"]["yield_reference_MPa"] / material_factor, "stress allowable")
    hover = _positive(data, "reference.hover_thrust_N")
    motors = _integer(_at(data, "reference.motor_count"), "motor_count", minimum=1)
    expected_hover = round(_positive(data, "reference.takeoff_mass_kg") *
                           _positive(data, "reference.gravity_m_s2") / motors, 1)
    _same(hover, expected_hover, "rounded hover thrust")
    lc1 = _vector(_at(data, "loads.LC1.force_N"), "loads.LC1.force_N")
    _same(lc1[2], hover * _positive(data, "factors.thrust_load_factor"), "LC1 thrust")
    if lc1[:2] != [0.0, 0.0] or _at(data, "loads.LC1.load_factor_included") is not True:
        raise ConfigError("LC1 must be +z thrust with its load factor already included")
    _vector(_at(data, "loads.LC2.force_N"), "loads.LC2.force_N")
    _vector(_at(data, "loads.LC3.moment_Nmm"), "loads.LC3.moment_Nmm")

    if _at(data, "geometry.parameter_order") != ["t_mm", "h_mm", "r"]:
        raise ConfigError("geometry.parameter_order must be [t_mm, h_mm, r]")
    bounds = {name: _range(_at(data, f"geometry.ranges.{name}"), name)
              for name in ("t_mm", "h_mm", "r")}
    for name, (low, high) in bounds.items():
        baseline = _number(_at(data, f"geometry.baseline.{name}"), f"baseline.{name}")
        if not low <= baseline <= high:
            raise ConfigError(f"baseline.{name} is outside its bounds")
    rules = _at(data, "geometry.validity")
    for name in ("minimum_ligament_mm", "minimum_nonzero_hole_diameter_mm",
                 "minimum_internal_height_mm", "minimum_wall_mm"):
        _positive(data, f"geometry.validity.{name}")
    if bounds["t_mm"][0] < rules["minimum_wall_mm"]:
        raise ConfigError("Thickness bounds violate minimum_wall_mm")
    if 2 * bounds["t_mm"][1] >= data["interfaces"]["outer_width_mm"]:
        raise ConfigError("Thickness bounds leave no internal box width")
    if bounds["h_mm"][0] - 2 * bounds["t_mm"][1] < rules["minimum_internal_height_mm"]:
        raise ConfigError("Height/thickness bounds violate minimum_internal_height_mm")
    if not 0 <= bounds["r"][0] < bounds["r"][1] < 1:
        raise ConfigError("Hole-ratio bounds must satisfy 0 <= low < high < 1")
    _integer(_at(data, "geometry.holes_per_side"), "holes_per_side", minimum=1)
    start, end = _range(_at(data, "geometry.hole_centre_span_fraction"), "hole centres")
    if not 0 <= start < end <= 1:
        raise ConfigError("Hole-centre span must be inside [0, 1]")
    if _at(data, "geometry.no_holes_when_r_zero") is not True:
        raise ConfigError("r=0 must represent no holes")

    rpm = _range(_at(data, "reference.hover_rpm"), "reference.hover_rpm")
    if rpm[0] <= 0 or _positive(data, "reference.maximum_rpm") < rpm[1]:
        raise ConfigError("RPM range must be positive and below maximum_rpm")
    blades = _integer(_at(data, "reference.blade_count"), "blade_count", minimum=1)
    for key, multiplier in (("hover_1p_band_Hz", 1), ("hover_blade_pass_band_Hz", blades)):
        band = _range(_at(data, f"modal.{key}"), f"modal.{key}")
        for actual, speed in zip(band, rpm):
            _same(actual, speed / 60 * multiplier, key)
    modes = _integer(_at(data, "modal.mode_count"), "mode_count", minimum=1)
    if _at(data, "outputs.frequencies") != [f"f{i}_Hz" for i in range(1, modes + 1)]:
        raise ConfigError("Frequency output names must match mode_count")
    if not isinstance(_at(data, "limits.modal_constraint_enabled"), bool):
        raise ConfigError("modal_constraint_enabled must be boolean")
    if not 0 < _positive(data, "modal.separation_fraction") < 1:
        raise ConfigError("modal.separation_fraction must be between 0 and 1")
    if _at(data, "mesh.element") != "C3D10":
        raise ConfigError("The planned mesh element is C3D10")
    _positive(data, "mesh.wall_size_over_thickness")
    _integer(_at(data, "mesh.convergence_mesh_count"), "convergence_mesh_count", minimum=3)
    for name in ("u_tip_mm", "f1_Hz", "sigma_hole_MPa"):
        if not 0 < _positive(data, f"mesh.relative_change_limits.{name}") < 1:
            raise ConfigError("Mesh tolerances must be relative fractions between 0 and 1")
    for name in ("sampling", "split", "cv", "models", "design_search"):
        _integer(_at(data, f"seeds.{name}"), f"seeds.{name}")
    _integer(_at(data, "solver.omp_num_threads"), "omp_num_threads", minimum=1)
    executable = _at(data, "solver.executable")
    if executable is not None and (not isinstance(executable, str) or not executable.strip()):
        raise ConfigError("solver.executable must be null or a nonempty path")
    try:
        json.dumps(data, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise ConfigError("Configuration must contain only finite JSON values") from exc


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ConfigError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_config(path: str | Path) -> dict[str, Any]:
    """Read UTF-8 JSON and validate it before exposing values to other code."""
    file = Path(path)
    try:
        data = json.loads(file.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Cannot read configuration {file}: {exc}") from exc
    validate_config(data)
    return data


def config_hash(data: dict[str, Any]) -> str:
    """SHA256 of validated canonical JSON; ignores formatting and key order."""
    validate_config(data)
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
