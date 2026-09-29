from __future__ import annotations

import hashlib
import unittest
from pathlib import Path


class VendoredMinerUTests(unittest.TestCase):
    def test_official_wheel_hash_version_and_source_are_present(self):
        root = Path(__file__).parents[1] / "vendor" / "mineru-4.0.7"
        wheel = root / "mineru-4.0.7-py3-none-any.whl"
        metadata_path = root / "mineru-4.0.7.dist-info" / "METADATA"

        self.assertTrue(wheel.is_file(), "vendored MinerU wheel is missing")
        self.assertTrue(metadata_path.is_file(), "official wheel metadata is missing")
        metadata = metadata_path.read_text(encoding="utf-8")
        self.assertEqual(
            hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "a08b24f733f0160eb9a836b0bb721640caef61d8d4f0ba2fd3aff28c6718111d",
        )
        self.assertIn("Version: 4.0.7", metadata)
        self.assertTrue((root / "mineru" / "parser").is_dir())
        self.assertTrue((root / "LICENSE.md").is_file())
        self.assertTrue((root / "UPSTREAM_README.md").is_file())
        self.assertFalse(any(root.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
