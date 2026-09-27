from __future__ import annotations

import unittest
from pathlib import Path


class CloudTemplateTests(unittest.TestCase):
    def test_api_port_is_bound_to_configured_tailnet_ip(self):
        compose = (Path(__file__).parents[1] / "cloud" / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("${TAILSCALE_IP:?Set the server Tailscale IPv4 address}:8000:8000", compose)
        self.assertNotIn('"8000:8000"', compose)

    def test_cloud_image_pins_mineru_and_gpu_is_optional(self):
        dockerfile = (Path(__file__).parents[1] / "cloud" / "Dockerfile").read_text(encoding="utf-8")
        gpu_override = (Path(__file__).parents[1] / "cloud" / "docker-compose.gpu.yml").read_text(encoding="utf-8")

        self.assertIn("mineru[pipeline]==3.2.3", dockerfile)
        self.assertIn("gpus: all", gpu_override)


if __name__ == "__main__":
    unittest.main()
