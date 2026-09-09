"""Doctor must inspect the consumer's projection, not only resolved canonical siblings."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'doctor.py'
spec = importlib.util.spec_from_file_location('doctor', SCRIPT)
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)


class DoctorProjectionTests(unittest.TestCase):
    def test_standalone_caller_does_not_scan_installation_ancestors(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            caller = root / 'scratch'
            caller.mkdir()
            (root / 'projects').mkdir()
            with patch.object(doctor.Path, 'cwd', return_value=caller):
                self.assertEqual(doctor.find_repo(), caller)

    def test_nested_caller_uses_its_own_project(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            caller = root / 'writing/article'
            caller.mkdir(parents=True)
            (root / 'project.md').write_text('# Consumer')
            with patch.object(doctor.Path, 'cwd', return_value=caller):
                self.assertEqual(doctor.find_repo(), root)

    def test_linked_vendor_version_is_detected_in_consumer(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            repo, vendor = root / 'consumer', root / 'vendor'
            vendor.mkdir()
            (vendor / 'SKILL.md').write_text('---\nname: remotion-best-practices\nversion: 4.0.520\n---\n')
            skills = repo / '.agents/skills'
            skills.mkdir(parents=True)
            (skills / 'remotion-best-practices').symlink_to(vendor, target_is_directory=True)
            (repo / 'remotion').mkdir()
            (repo / 'remotion/package.json').write_text('{"dependencies":{"remotion":"4.0.446"}}')
            self.assertEqual(doctor.find_skills_root(repo), skills)
            self.assertEqual(doctor.remotion_versions(repo, doctor.find_skills_root(repo)),
                             {'status': 'ready', 'engine': '4.0.446', 'optional_skill': '4.0.520'})

    def test_project_projection_precedes_canonical_shaped_folder(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / '.agents/skills').mkdir(parents=True)
            (root / 'skills').mkdir()
            self.assertEqual(doctor.find_skills_root(root), root / '.agents/skills')

    def test_central_repo_has_flat_skills(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'skills').mkdir()
            self.assertEqual(doctor.find_skills_root(root), root / 'skills')

    def test_no_projection_falls_back_to_installed_skill_source(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(doctor.find_skills_root(Path(d)), SCRIPT.parents[2])


if __name__ == '__main__':
    unittest.main()
