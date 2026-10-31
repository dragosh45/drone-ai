"""Reproduce review §3.1's rounded table from the committed study inputs."""

from pathlib import Path
import unittest

from drone_arm.config import load_config
from drone_arm.screening import screening_rows


class ScreeningTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(Path(__file__).resolve().parents[1] / "configs/study.json")
        self.rows = screening_rows(self.config)

    def test_full_review_table(self):
        # mass (whole g), deflection (review precision), stress (0.1 MPa), f1 (whole Hz)
        expected = [
            (25, 98.7, 1, 22.2, 5), (38, 29.2, 1, 9.9, 9),
            (64, 6.3, 1, 3.6, 19), (25, 2.5, 1, 3.6, 31),
            (37, 1.7, 1, 1.9, 38), (42, 0.96, 2, 1.4, 49),
            (51, 0.82, 2, 1.2, 53), (59, 0.73, 2, 1.0, 55),
        ]
        self.assertEqual(len(self.rows), len(expected))
        for row, (mass, displacement, digits, stress, frequency) in zip(self.rows, expected):
            with self.subTest(section=row["section"]):
                self.assertEqual(round(row["arm_mass_g"]), mass)
                self.assertEqual(round(row["deflection_mm"], digits), displacement)
                self.assertEqual(round(row["nominal_stress_MPa"], 1), stress)
                self.assertEqual(round(row["estimated_f1_Hz"]), frequency)

    def test_headline_and_orientation(self):
        flat4, flat6, _, edge, _, tube, *_ = self.rows
        self.assertAlmostEqual(flat6["deflection_mm"], 29.234567901234566)
        self.assertAlmostEqual(tube["arm_mass_g"], 41.656)
        self.assertGreater(flat6["deflection_mm"], self.config["limits"]["tip_deflection_mm"])
        self.assertLess(tube["deflection_mm"], self.config["limits"]["tip_deflection_mm"])
        self.assertEqual(flat4["arm_mass_g"], edge["arm_mass_g"])
        self.assertAlmostEqual(flat4["deflection_mm"] / edge["deflection_mm"], (25 / 4)**2)

    def test_modulus_scaling_reproduces_old_screen(self):
        self.config["material"]["youngs_modulus_MPa"] = 2000
        stiffer = screening_rows(self.config)
        self.assertAlmostEqual(stiffer[0]["deflection_mm"], 74)
        self.assertAlmostEqual(stiffer[1]["deflection_mm"], 21.925925925925927)
        for old, new in zip(self.rows, stiffer):
            self.assertEqual(old["nominal_stress_MPa"], new["nominal_stress_MPa"])
            self.assertAlmostEqual(new["estimated_f1_Hz"] / old["estimated_f1_Hz"], (2000/1500)**0.5)


if __name__ == "__main__":
    unittest.main()
