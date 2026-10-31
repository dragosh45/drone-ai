"""Configuration checks run with unittest before the conda/pytest setup exists."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from drone_arm.config import ConfigError, config_hash, load_config, validate_config


STUDY = Path(__file__).resolve().parents[1] / "configs" / "study.json"


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(STUDY)

    def test_committed_units_and_factors(self):
        self.assertEqual(self.config["units"]["solver_mass"], "tonne")
        self.assertAlmostEqual(self.config["material"]["density_tonne_mm3"] * 1000 * 1e6, 1.27)
        self.assertEqual(self.config["loads"]["LC3"]["moment_Nmm"], [0, 0, 13])
        self.assertEqual(self.config["limits"]["body_stress_MPa"], 23.5)
        self.assertFalse(self.config["frozen"])

    def test_hash_ignores_formatting_and_key_order(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "study.json"
            file.write_text(json.dumps(self.config, sort_keys=True, indent=4), encoding="utf-8")
            self.assertEqual(config_hash(self.config), config_hash(load_config(file)))
        self.assertEqual(len(config_hash(self.config)), 64)

    def test_hash_changes_when_study_changes(self):
        changed = deepcopy(self.config)
        changed["material"]["youngs_modulus_MPa"] = 1600.0
        self.assertNotEqual(config_hash(self.config), config_hash(changed))

    def test_rejects_unit_and_density_mistakes(self):
        for section, key, value in [
            ("units", "solver_mass", "kg"),
            ("material", "density_tonne_mm3", 1.27e-6),
            ("material", "poisson_ratio", 0.5),
            ("material", "youngs_modulus_MPa", float("nan")),
            ("material", "youngs_modulus_MPa", True),
        ]:
            with self.subTest(key=key, value=value):
                changed = deepcopy(self.config)
                changed[section][key] = value
                with self.assertRaises(ConfigError):
                    validate_config(changed)

    def test_rejects_double_applied_factors(self):
        changed = deepcopy(self.config)
        changed["loads"]["LC1"]["force_N"][2] *= 2
        with self.assertRaisesRegex(ConfigError, "LC1 thrust"):
            validate_config(changed)
        changed = deepcopy(self.config)
        changed["limits"]["body_stress_MPa"] /= 2
        with self.assertRaisesRegex(ConfigError, "stress allowable"):
            validate_config(changed)

    def test_rejects_invalid_parameter_contract(self):
        for key, value in [("t_mm", [3.2, 1.6]), ("r", [0, 1.2]), ("t_mm", [1.6, 12])]:
            with self.subTest(key=key, value=value):
                changed = deepcopy(self.config)
                changed["geometry"]["ranges"][key] = value
                with self.assertRaises(ConfigError):
                    validate_config(changed)

    def test_rejects_inconsistent_frequency_band(self):
        self.config["modal"]["hover_blade_pass_band_Hz"] = [75, 100]
        with self.assertRaisesRegex(ConfigError, "blade_pass"):
            validate_config(self.config)

    def test_rejects_missing_fields_and_duplicate_json_keys(self):
        del self.config["solver"]
        with self.assertRaisesRegex(ConfigError, "solver"):
            validate_config(self.config)
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "duplicate.json"
            file.write_text('{"schema_version": 1, "schema_version": 2}', encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "Duplicate JSON key"):
                load_config(file)

    def test_unresolved_values_are_explicit(self):
        self.assertIsNone(self.config["interfaces"]["motor_pad"]["thickness_mm"])
        self.assertIsNone(self.config["mesh"]["hole_refinement_factor"])


if __name__ == "__main__":
    unittest.main()
