import argparse
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location("profiles", Path(__file__).parents[1] / "scripts/eden-cache-profiles.py")
profiles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profiles)


def raw(version=17):
    return b"yuzucach" + struct.pack("<I", version) + b"opaque shader records"


def pipeline(version=17, payload=b"opaque pipeline cache"):
    return (b"yuzuvkch" + struct.pack("<I", version) +
            struct.pack("<IIII", 32, 1, 0x5143, 0x44030000) + bytes(range(16)) + payload)


def make_driver(path, marker=b"a", name="fixture"):
    elf = bytearray(32)
    elf[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", elf, 18, 183)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("meta.json", json.dumps({"name": name, "libraryName": "driver.so"}))
        archive.writestr("driver.so", elf + marker)


class CacheProfilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = self.root / "010096f00ff22000"
        self.cache.mkdir()
        (self.cache / profiles.RAW).write_bytes(raw())
        (self.cache / profiles.PIPELINES).write_bytes(pipeline())
        self.driver = self.root / "driver.zip"
        make_driver(self.driver)
        self.args = argparse.Namespace(cache_dir=self.cache, title=self.cache.name,
                                       driver=self.driver, emulator="4dc69c06f7",
                                       profiles=self.root / "profiles")

    def test_restore_preserves_new_shader_records_and_backs_up_current_driver_cache(self):
        saved = profiles.save(self.args)
        current_raw = raw() + b"newly discovered shaders"
        current_pipeline = pipeline(payload=b"other driver cache")
        (self.cache / profiles.RAW).write_bytes(current_raw)
        (self.cache / profiles.PIPELINES).write_bytes(current_pipeline)
        restored = profiles.restore(self.args)
        self.assertEqual((self.cache / profiles.PIPELINES).read_bytes(), pipeline())
        self.assertEqual((self.cache / profiles.RAW).read_bytes(), current_raw)
        self.assertEqual(Path(restored["backup"]).read_bytes(), current_pipeline)
        self.assertEqual(restored["profile"], saved["profile"])
        self.assertFalse(restored["compilation_performed"])

    def test_different_driver_cannot_restore_another_profile(self):
        profiles.save(self.args)
        make_driver(self.driver, marker=b"different binary")
        before = (self.cache / profiles.PIPELINES).read_bytes()
        with self.assertRaisesRegex(ValueError, "Nenhum perfil"):
            profiles.restore(self.args)
        self.assertEqual((self.cache / profiles.PIPELINES).read_bytes(), before)

    def test_same_library_with_different_zip_metadata_reuses_profile(self):
        profiles.save(self.args)
        make_driver(self.driver, name="same driver renamed")
        self.assertEqual(profiles.restore(self.args)["status"], "restored")

    def test_different_emulator_revision_has_no_profile(self):
        profiles.save(self.args)
        self.args.emulator = "another-revision"
        with self.assertRaisesRegex(ValueError, "Nenhum perfil"):
            profiles.restore(self.args)

    def test_cache_version_change_does_not_overwrite(self):
        profiles.save(self.args)
        (self.cache / profiles.RAW).write_bytes(raw(version=18))
        before = (self.cache / profiles.PIPELINES).read_bytes()
        with self.assertRaisesRegex(ValueError, "versão de cache diferente"):
            profiles.restore(self.args)
        self.assertEqual((self.cache / profiles.PIPELINES).read_bytes(), before)

    def test_corrupt_snapshot_is_rejected(self):
        saved = profiles.save(self.args)
        p = Path(saved["profile"]) / profiles.PIPELINES
        p.write_bytes(p.read_bytes() + b"unexpected corruption")
        before = (self.cache / profiles.PIPELINES).read_bytes()
        with self.assertRaisesRegex(ValueError, "alterado ou corrompido"):
            profiles.restore(self.args)
        self.assertEqual((self.cache / profiles.PIPELINES).read_bytes(), before)

    def test_empty_or_unknown_cache_does_not_create_a_profile(self):
        for data in [pipeline(payload=b""), b"bad signature", pipeline()[:20]]:
            (self.cache / profiles.PIPELINES).write_bytes(data)
            with self.assertRaises(ValueError):
                profiles.save(self.args)
        self.assertFalse(self.args.profiles.exists())

    def test_symlink_destination_is_rejected_before_writing(self):
        profiles.save(self.args)
        destination = self.cache / profiles.PIPELINES
        destination.unlink()
        unrelated = self.root / "unrelated.bin"
        unrelated.write_bytes(b"keep this file")
        destination.symlink_to(unrelated)
        with self.assertRaisesRegex(ValueError, "Arquivo normal"):
            profiles.restore(self.args)
        self.assertEqual(unrelated.read_bytes(), b"keep this file")

    def test_saved_profiles_are_append_only(self):
        first = profiles.save(self.args)
        (self.cache / profiles.PIPELINES).write_bytes(pipeline(payload=b"newer cache"))
        second = profiles.save(self.args)
        self.assertNotEqual(first["profile"], second["profile"])
        self.assertEqual((Path(first["profile"]) / profiles.PIPELINES).read_bytes(), pipeline())
        self.assertEqual((Path(second["profile"]) / profiles.PIPELINES).read_bytes(), pipeline(payload=b"newer cache"))

    def test_actual_repository_driver_archives_have_distinct_identities(self):
        directory = Path(__file__).parents[1] / "drivers/poco-f7/experimental-1"
        normal = profiles.driver_identity(directory / "Turnip_POCO_F7_Experimental_1.zip")
        diag = profiles.driver_identity(directory / "Turnip_POCO_F7_Experimental_1_Diag.zip")
        self.assertNotEqual(normal["library_sha256"], diag["library_sha256"])

    def test_cli_save_and_restore_round_trip(self):
        script = Path(__file__).parents[1] / "scripts/eden-cache-profiles.py"
        common = ["--cache-dir", str(self.cache), "--driver", str(self.driver),
                  "--emulator", self.args.emulator, "--profiles", str(self.args.profiles),
                  "--eden-stopped"]
        saved = subprocess.run([sys.executable, str(script), "save", *common], capture_output=True, text=True)
        self.assertEqual(saved.returncode, 0, saved.stderr)
        self.assertEqual(json.loads(saved.stdout)["status"], "saved")
        (self.cache / profiles.PIPELINES).write_bytes(pipeline(payload=b"different current cache"))
        restored = subprocess.run([sys.executable, str(script), "restore", *common], capture_output=True, text=True)
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertEqual(json.loads(restored.stdout)["status"], "restored")
        self.assertEqual((self.cache / profiles.PIPELINES).read_bytes(), pipeline())


if __name__ == "__main__":
    unittest.main()
