"""Small-deflection cantilever formulas, using mm, N, MPa and grams.

Analytical screening only: uniform sections, no holes, pads or clamp compliance.
These functions do not create geometry or run a finite-element solver.
"""

from dataclasses import dataclass
import math


def _positive(**values: float) -> None:
    for name, value in values.items():
        if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")


@dataclass(frozen=True)
class Section:
    area_mm2: float
    inertia_mm4: float
    half_height_mm: float


def rectangle(width_mm: float, height_mm: float) -> Section:
    """Height is in the bending/load direction; I is about the lateral axis."""
    _positive(width_mm=width_mm, height_mm=height_mm)
    return Section(width_mm * height_mm, width_mm * height_mm**3 / 12,
                   height_mm / 2)


def box(width_mm: float, height_mm: float, wall_mm: float) -> Section:
    """Outer rectangle minus the concentric inner rectangle, uniform walls."""
    _positive(width_mm=width_mm, height_mm=height_mm, wall_mm=wall_mm)
    if 2 * wall_mm >= min(width_mm, height_mm):
        raise ValueError("Box walls must leave a positive interior")
    outer = rectangle(width_mm, height_mm)
    inner = rectangle(width_mm - 2 * wall_mm, height_mm - 2 * wall_mm)
    return Section(outer.area_mm2 - inner.area_mm2,
                   outer.inertia_mm4 - inner.inertia_mm4, height_mm / 2)


def cantilever(section: Section, *, length_mm: float, force_N: float,
               modulus_MPa: float, density_g_cm3: float) -> dict[str, float]:
    """Return magnitudes: delta=FL^3/(3EI), sigma=FLc/I, mass=rho*volume."""
    _positive(length_mm=length_mm, force_N=force_N, modulus_MPa=modulus_MPa,
              density_g_cm3=density_g_cm3, area_mm2=section.area_mm2,
              inertia_mm4=section.inertia_mm4, half_height_mm=section.half_height_mm)
    stiffness = 3 * modulus_MPa * section.inertia_mm4 / length_mm**3
    return {
        "area_mm2": section.area_mm2,
        "inertia_mm4": section.inertia_mm4,
        "stiffness_N_mm": stiffness,
        "deflection_mm": force_N / stiffness,
        "nominal_stress_MPa": force_N * length_mm * section.half_height_mm / section.inertia_mm4,
        "arm_mass_g": section.area_mm2 * length_mm * density_g_cm3 / 1000,
    }


def tip_mass_frequency(stiffness_N_mm: float, arm_mass_g: float,
                       tip_mass_g: float) -> float:
    """Rayleigh estimate: effective mass = tip mass + 0.236 * uniform arm mass.

N/mm requires mass in tonnes for seconds: 1 g = 1e-6 tonnes.
This is a bending estimate, not a six-mode or resonance assessment.
"""
    _positive(stiffness_N_mm=stiffness_N_mm, arm_mass_g=arm_mass_g,
              tip_mass_g=tip_mass_g)
    effective_mass_tonnes = (tip_mass_g + 0.236 * arm_mass_g) * 1e-6
    return math.sqrt(stiffness_N_mm / effective_mass_tonnes) / (2 * math.pi)
