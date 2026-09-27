# Changelog

## 0.2.0 — 2026-09-27

- Upgrade the local MinerU integration from 3.2.3 CLI calls to the 4.0.7 Python SDK.
- Replace the legacy remote `/tasks` protocol with MinerU V1 uploads, parse jobs, polling, and file downloads.
- Add MinerU 4 native input formats: DOC, PPT, XLS, RTF, ODT/ODS/ODP, EPUB, OFD, HTML, CSV/TSV, and MHTML/MHT.
- Keep the existing MCP tool names and add an automatic `tier` selector.
- Standardize parse artifacts on `structured_content.json`, `middle_json.json`, Markdown, and extracted images.
- Upgrade the Windows installer and Tailscale-bound Docker Compose templates to MinerU 4.0.7.
- Add optional bearer-key support to the self-hosted API template.
