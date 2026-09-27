from __future__ import annotations

import unittest
from pathlib import Path


class CloudTemplateTests(unittest.TestCase):
    def test_api_port_is_bound_to_configured_tailnet_ip(self):
        compose = (Path(__file__).parents[1] / "cloud" / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("${TAILSCALE_IP:?Set the server Tailscale IPv4 address}:8000:8000", compose)
        self.assertNotIn('"8000:8000"', compose)

    def test_cloud_image_pins_mineru_407_and_uses_v1_api_with_optional_gpu(self):
        dockerfile = (Path(__file__).parents[1] / "cloud" / "Dockerfile").read_text(encoding="utf-8")
        compose = (Path(__file__).parents[1] / "cloud" / "docker-compose.yml").read_text(encoding="utf-8")
        gpu_override = (Path(__file__).parents[1] / "cloud" / "docker-compose.gpu.yml").read_text(encoding="utf-8")

        self.assertIn('"mineru${MINERU_EXTRA}==4.0.7"', dockerfile)
        self.assertIn('ENTRYPOINT ["/usr/local/bin/document-parser-entrypoint"]', dockerfile)
        entrypoint = (Path(__file__).parents[1] / "cloud" / "entrypoint.sh").read_text(encoding="utf-8")
        self.assertIn('exec mineru-kit "$@"', entrypoint)
        self.assertIn("/v1/health", compose)
        self.assertIn("gpus: all", gpu_override)
        self.assertIn('MINERU_EXTRA: "[full]"', gpu_override)
        self.assertIn("MINERU_API_KEY", compose)

    def test_windows_installer_pins_407_and_supports_remote_api_auth(self):
        installer = (Path(__file__).parents[1] / "scripts" / "install.ps1").read_text(encoding="utf-8")

        self.assertIn('"mineru==4.0.7"', installer)
        self.assertIn('"mineru[full]==4.0.7"', installer)
        self.assertIn('"DOCUMENT_PARSER_REMOTE_TOKEN"', installer)
        self.assertNotIn("mineru[pipeline]==3.2.3", installer)


if __name__ == "__main__":
    unittest.main()
