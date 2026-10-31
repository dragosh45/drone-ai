from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

from drone_arm.doctor import ccx_version, discover_ccx, doctor, probe_ccx


class DoctorTests(unittest.TestCase):
    def test_config_override_precedes_environment_and_path(self):
        with patch.dict("os.environ", {"DRONE_ARM_CCX": "/other/ccx"}), \
                patch("drone_arm.doctor.shutil.which", return_value="/configured/ccx") as which:
            self.assertEqual(discover_ccx("/configured/ccx"), Path("/configured/ccx").resolve())
            which.assert_called_once_with(str(Path("/configured/ccx")))

    def test_bad_explicit_override_does_not_use_path_fallback(self):
        with patch("drone_arm.doctor.shutil.which", return_value=None) as which:
            self.assertIsNone(discover_ccx("/missing/ccx"))
            which.assert_called_once_with(str(Path("/missing/ccx")))

    def test_environment_override(self):
        with patch.dict("os.environ", {"DRONE_ARM_CCX": "/custom/ccx"}), \
                patch("drone_arm.doctor.shutil.which", return_value="/custom/ccx") as which:
            self.assertEqual(discover_ccx(None), Path("/custom/ccx").resolve())
            which.assert_called_once_with(str(Path("/custom/ccx")))

    def test_version_probe_handles_spaces_and_sets_threads(self):
        with patch("drone_arm.doctor.subprocess.run") as run:
            probe_ccx(Path("/path with spaces/ccx"), threads=1, timeout=15)
            args, kwargs = run.call_args
            self.assertEqual(args[0], [str(Path("/path with spaces/ccx")), "-v"])
            self.assertEqual(kwargs["env"]["OMP_NUM_THREADS"], "1")
            self.assertEqual(kwargs["timeout"], 15)
            self.assertFalse(kwargs.get("shell", False))

    def test_expected_version_exit_codes(self):
        for code in (0, 201):
            result = subprocess.CompletedProcess(["ccx", "-v"], code, "\nThis is Version 2.23\n", "")
            self.assertEqual(ccx_version(result), "2.23")

    def test_failure_is_not_mistaken_for_a_version(self):
        for code, stdout, stderr in (
            (201, "", "*ERROR in CalculiX"),
            (201, "This is Version 2.23", "dyld: library not loaded"),
            (1, "This is Version 2.23", ""),
            (0, "version unknown", ""),
        ):
            self.assertIsNone(ccx_version(subprocess.CompletedProcess(["ccx", "-v"], code, stdout, stderr)))

    @unittest.skipUnless(shutil.which("ccx"), "ccx is not on PATH")
    def test_installed_ccx_version_only(self):
        executable = Path(shutil.which("ccx"))
        self.assertIsNotNone(ccx_version(probe_ccx(executable, threads=1, timeout=15)))

    def test_bad_config_fails_without_a_solver_probe(self):
        with redirect_stdout(StringIO()) as output, patch("drone_arm.doctor.probe_ccx") as probe:
            self.assertEqual(doctor(Path("does-not-exist.json")), 1)
            self.assertIn("Doctor: FAIL", output.getvalue())
            probe.assert_not_called()

    def test_timeout_is_not_a_success(self):
        config = Path(__file__).resolve().parents[1] / "configs/study.json"
        with patch("drone_arm.doctor.import_module") as module, \
                patch("drone_arm.doctor.discover_ccx", return_value=Path("/fake/ccx")), \
                patch("drone_arm.doctor.probe_ccx", side_effect=subprocess.TimeoutExpired("ccx", 15)), \
                redirect_stdout(StringIO()) as output:
            module.return_value.__version__ = "test"
            self.assertEqual(doctor(config), 1)
            self.assertIn("Doctor: FAIL", output.getvalue())
            self.assertIn("timed out", output.getvalue())

    def test_complete_check_passes_with_version_201(self):
        config = Path(__file__).resolve().parents[1] / "configs/study.json"
        result = subprocess.CompletedProcess(["ccx", "-v"], 201, "This is Version 2.23", "")
        with patch("drone_arm.doctor.sys.version_info", (3, 12)), \
                patch("drone_arm.doctor.import_module") as module, \
                patch("drone_arm.doctor.discover_ccx", return_value=Path("/fake/ccx")), \
                patch("drone_arm.doctor.probe_ccx", return_value=result), \
                redirect_stdout(StringIO()) as output:
            module.return_value.__version__ = "test"
            self.assertEqual(doctor(config), 0)
            self.assertIn("Doctor: PASS", output.getvalue())


if __name__ == "__main__":
    unittest.main()
