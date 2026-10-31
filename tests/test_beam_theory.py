"""Tutorial tube arithmetic, not the Gate 1 finite-element benchmark.

Source: docs/reference/course_materials/
AIMLA_tutorial_part1_notes_and_report_template.md, section 3.
Running this file prints reproducible analytical evidence as JSON to stdout.
"""

import json
import unittest

from drone_arm.beam_theory import box, cantilever, rectangle, tip_mass_frequency


TUTORIAL_INPUTS = {
    "length_mm": 180, "force_N": 20, "modulus_MPa": 70000, "density_g_cm3": 2.7,
}


def tutorial_values() -> dict[str, float]:
    return cantilever(box(20, 25, 2), **TUTORIAL_INPUTS)


class BeamTheoryTests(unittest.TestCase):
    def test_tutorial_reference_to_four_significant_digits(self):
        values = tutorial_values()
        self.assertEqual(values["area_mm2"], 164)
        self.assertAlmostEqual(values["inertia_mm4"], 13693.6666666667, places=7)
        # Four-significant-digit references from the stated tutorial dimensions.
        self.assertEqual(format(values["inertia_mm4"], ".4g"), "1.369e+04")
        self.assertEqual(format(values["deflection_mm"], ".4g"), "0.04056")
        self.assertEqual(format(values["nominal_stress_MPa"], ".4g"), "3.286")
        self.assertAlmostEqual(values["arm_mass_g"], 79.704, places=8)
        # Also match the less precise numbers printed in the tutorial.
        self.assertEqual(round(values["inertia_mm4"], 2), 13693.67)
        self.assertEqual(round(values["deflection_mm"], 4), 0.0406)
        self.assertEqual(round(values["nominal_stress_MPa"], 2), 3.29)
        self.assertEqual(round(values["arm_mass_g"], 1), 79.7)

    def test_known_volume_density_conversion(self):
        # 10 mm cube = 1 cm^3; PETG therefore weighs 1.27 g.
        values = cantilever(rectangle(10, 10), length_mm=10, force_N=1,
                            modulus_MPa=1500, density_g_cm3=1.27)
        self.assertAlmostEqual(values["arm_mass_g"], 1.27)
        self.assertAlmostEqual(1.27e-9 * 1000 * 1e6, values["arm_mass_g"])

    def test_load_and_modulus_scaling(self):
        base = tutorial_values()
        doubled_load = cantilever(box(20, 25, 2), **{**TUTORIAL_INPUTS, "force_N": 40})
        doubled_modulus = cantilever(box(20, 25, 2), **{**TUTORIAL_INPUTS, "modulus_MPa": 140000})
        self.assertAlmostEqual(doubled_load["deflection_mm"], 2 * base["deflection_mm"])
        self.assertAlmostEqual(doubled_load["nominal_stress_MPa"], 2 * base["nominal_stress_MPa"])
        self.assertAlmostEqual(doubled_modulus["deflection_mm"], base["deflection_mm"] / 2)
        self.assertEqual(doubled_modulus["nominal_stress_MPa"], base["nominal_stress_MPa"])
        self.assertEqual(doubled_load["arm_mass_g"], base["arm_mass_g"])

    def test_tutorial_height_variant(self):
        taller = cantilever(box(20, 30, 2), **TUTORIAL_INPUTS)
        self.assertEqual(taller["area_mm2"], 184)
        # Imported notes have a small arithmetic typo here; see DECISIONS.md.
        self.assertAlmostEqual(taller["inertia_mm4"], 21565.3333333333, places=7)
        self.assertEqual(round(taller["deflection_mm"] / tutorial_values()["deflection_mm"], 3), 0.635)

    def test_frequency_mass_units(self):
        # k=1 N/mm=1000 N/m; effective mass=76.4+0.236*100=100 g=0.1 kg.
        self.assertAlmostEqual(tip_mass_frequency(1, 100, 76.4), 15.91549430919, places=9)

    def test_nonphysical_inputs_rejected(self):
        for dims in ((20, 25, 10), (20, 25, 0), (-20, 25, 2), (20, float("nan"), 2)):
            with self.subTest(dimensions=dims), self.assertRaises(ValueError):
                box(*dims)
        for name in TUTORIAL_INPUTS:
            with self.subTest(input=name), self.assertRaises(ValueError):
                cantilever(box(20, 25, 2), **{**TUTORIAL_INPUTS, name: 0})


if __name__ == "__main__":
    print(json.dumps({
        "method": "Euler-Bernoulli cantilever theory; no FE solve",
        "inputs": {"width_mm": 20, "height_mm": 25, "wall_mm": 2, **TUTORIAL_INPUTS},
        "results": tutorial_values(),
    }, indent=2))
    unittest.main()
