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

        self.assertIn("COPY vendor/mineru-4.0.7/mineru-4.0.7-py3-none-any.whl", dockerfile)
        self.assertIn('"mineru${MINERU_EXTRA} @ file:///opt/mineru-4.0.7-py3-none-any.whl"', dockerfile)
        self.assertIn('ENTRYPOINT ["/usr/local/bin/document-parser-entrypoint"]', dockerfile)
        self.assertIn("context: ..", compose)
        self.assertIn("dockerfile: cloud/Dockerfile", compose)
        self.assertIn("cloud/entrypoint.sh", dockerfile)
        entrypoint = (Path(__file__).parents[1] / "cloud" / "entrypoint.sh").read_text(encoding="utf-8")
        self.assertIn('exec mineru-kit "$@"', entrypoint)
        self.assertIn("/v1/health", compose)
        self.assertIn("gpus: all", gpu_override)
        self.assertIn('MINERU_EXTRA: "[full]"', gpu_override)
        self.assertIn("MINERU_API_KEY", compose)

    def test_windows_installer_pins_407_and_supports_remote_api_auth(self):
        installer = (Path(__file__).parents[1] / "scripts" / "install.ps1").read_text(encoding="utf-8")

        self.assertIn('"mineru @ $mineruWheelUri"', installer)
        self.assertIn('"mineru[full] @ $mineruWheelUri"', installer)
        self.assertIn('"vendor\\mineru-4.0.7\\$mineruWheelName"', installer)
        self.assertIn('"--server-name", "yushu-document-parser"', installer)
        self.assertIn('"DOCUMENT_PARSER_REMOTE_TOKEN"', installer)
        self.assertNotIn("mineru[pipeline]==3.2.3", installer)

    def test_windows_gpu_installer_restores_resolved_cuda_wheels_after_mineru(self):
        installer = (Path(__file__).parents[1] / "scripts" / "install.ps1").read_text(encoding="utf-8")

        mineru_install = installer.index("pip install --python $venvPython $mineruPackage")
        cuda_wheel_install = installer.index(
            "pip install --python $venvPython --index-url $torchIndex --no-deps --reinstall"
        )
        self.assertLess(mineru_install, cuda_wheel_install)
        self.assertIn('"https://download.pytorch.org/whl/cu126"', installer)
        self.assertIn("m.version('torch').split('+')[0]", installer)


if __name__ == "__main__":
    unittest.main()
