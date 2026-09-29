from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import tomlkit

from document_parser_mcp.client_config import configure_clients, register_codex_server, register_workbuddy_server


class ClientConfigTests(unittest.TestCase):
    def test_shared_registration_updates_both_clients(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = configure_clients(
                root / "config.toml",
                root / "mcp.json",
                "yushu-document-parser",
                "python.exe",
                ["-m", "document_parser_mcp.server"],
                {"DOCUMENT_PARSER_BACKEND": "remote"},
            )

            self.assertEqual(set(result), {"codex", "workbuddy"})
            self.assertTrue((root / "config.toml").is_file())
            self.assertTrue((root / "mcp.json").is_file())

    def test_codex_merge_preserves_existing_servers_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "config.toml"
            config.write_text('[mcp_servers.existing]\ncommand = "keep"\n', encoding="utf-8")

            register_codex_server(config, "yushu-document-parser", "python.exe", ["-m", "document_parser_mcp.server"], {})
            content = config.read_text(encoding="utf-8")
            backups_before_second_run = list(config.parent.glob("config.toml.backup-*"))
            register_codex_server(config, "yushu-document-parser", "python.exe", ["-m", "document_parser_mcp.server"], {})

            parsed = tomlkit.parse(content)
            self.assertEqual(parsed["mcp_servers"]["existing"]["command"], "keep")
            self.assertEqual(parsed["mcp_servers"]["yushu-document-parser"]["command"], "python.exe")
            self.assertEqual(len(list(config.parent.glob("config.toml.backup-*"))), len(backups_before_second_run))
            self.assertTrue(backups_before_second_run)

    def test_workbuddy_merge_preserves_existing_entries_and_creates_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "mcp.json"
            config.write_text(json.dumps({"mcpServers": {"existing": {"command": "keep"}}}), encoding="utf-8")

            register_workbuddy_server(config, "yushu-document-parser", "python.exe", ["-m", "document_parser_mcp.server"], {})

            parsed = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(parsed["mcpServers"]["existing"]["command"], "keep")
            self.assertEqual(parsed["mcpServers"]["yushu-document-parser"]["command"], "python.exe")
            self.assertTrue(list(config.parent.glob("mcp.json.backup-*")))

    def test_migrates_owned_codex_entry_and_preserves_unrelated_legacy_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "config.toml"
            config.write_text(
                '[mcp_servers.document-parser]\ncommand = "python.exe"\nargs = ["-m", "document_parser_mcp.server"]\n'
                '[mcp_servers.keep-me]\ncommand = "keep"\n',
                encoding="utf-8",
            )

            register_codex_server(
                config,
                "yushu-document-parser",
                "new-python.exe",
                ["-m", "document_parser_mcp.server"],
                {},
            )

            parsed = tomlkit.parse(config.read_text(encoding="utf-8"))
            self.assertNotIn("document-parser", parsed["mcp_servers"])
            self.assertEqual(parsed["mcp_servers"]["yushu-document-parser"]["command"], "new-python.exe")
            self.assertEqual(parsed["mcp_servers"]["keep-me"]["command"], "keep")
            self.assertTrue(list(config.parent.glob("config.toml.backup-*")))

    def test_preserves_unrelated_codex_entry_named_document_parser(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "config.toml"
            config.write_text(
                '[mcp_servers.document-parser]\ncommand = "python.exe"\nargs = ["-m", "other.server"]\n',
                encoding="utf-8",
            )

            register_codex_server(
                config,
                "yushu-document-parser",
                "new-python.exe",
                ["-m", "document_parser_mcp.server"],
                {},
            )

            parsed = tomlkit.parse(config.read_text(encoding="utf-8"))
            self.assertEqual(parsed["mcp_servers"]["document-parser"]["args"], ["-m", "other.server"])
            self.assertEqual(parsed["mcp_servers"]["yushu-document-parser"]["command"], "new-python.exe")

    def test_migrates_owned_workbuddy_entry_and_preserves_unrelated_legacy_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "mcp.json"
            config.write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "document-parser": {
                                "command": "python.exe",
                                "args": ["-m", "document_parser_mcp.server"],
                            },
                            "keep-me": {"command": "keep"},
                        }
                    }
                ),
                encoding="utf-8",
            )

            register_workbuddy_server(
                config,
                "yushu-document-parser",
                "new-python.exe",
                ["-m", "document_parser_mcp.server"],
                {},
            )

            parsed = json.loads(config.read_text(encoding="utf-8"))
            self.assertNotIn("document-parser", parsed["mcpServers"])
            self.assertEqual(parsed["mcpServers"]["yushu-document-parser"]["command"], "new-python.exe")
            self.assertEqual(parsed["mcpServers"]["keep-me"]["command"], "keep")
            self.assertTrue(list(config.parent.glob("mcp.json.backup-*")))

    def test_preserves_unrelated_workbuddy_entry_named_document_parser(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "mcp.json"
            config.write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "document-parser": {
                                "command": "python.exe",
                                "args": ["-m", "other.server"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            register_workbuddy_server(
                config,
                "yushu-document-parser",
                "new-python.exe",
                ["-m", "document_parser_mcp.server"],
                {},
            )

            parsed = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(
                parsed["mcpServers"]["document-parser"]["args"],
                ["-m", "other.server"],
            )
            self.assertEqual(parsed["mcpServers"]["yushu-document-parser"]["command"], "new-python.exe")


if __name__ == "__main__":
    unittest.main()
