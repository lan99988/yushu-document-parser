---
name: document-parser
description: Use when a user asks to extract, convert, or read text from PDF, image, Office, OpenDocument, EPUB, OFD, HTML/MHTML, CSV, or TSV files with the document-parser MCP tools.
---

# Document Parser

Use the document-parser MCP tools to turn supported files into local Markdown and structured artifacts. Parsing creates files; it does not automatically load an entire document into the conversation.

## Choose a tool

| User's request | Tool |
| --- | --- |
| Convert or inspect one file | `parse_document` |
| Convert several named files in a specified order | `parse_documents` |
| Read parsed Markdown or answer a question about its contents | `read_parsed_text` |

Supported inputs are PDF; PNG, JPG/JPEG, WEBP, BMP, TIF/TIFF images; DOC/DOCX, PPT/PPTX, XLS/XLSX; RTF; ODT/ODS/ODP; EPUB; OFD; HTML/HTM; MHTML/MHT; and CSV/TSV. MinerU 4.0.7 supports MHTML/MHT archives. Plain-text files such as TXT and MD are already readable and do not need parsing. Use explicit file paths. Do not recursively scan a directory unless the user asks for that and the exact scope is clear.

## Select the backend

- Omit `backend` when the user has not chosen a backend. The MCP service uses its configured default, which is local by default.
- Pass `backend="local"` or `backend="remote"` only when the user explicitly asks for that backend.
- Remote parsing uploads the selected file to the configured MinerU API. Use it only after the user chooses remote parsing. A configured remote URL alone does not mean the user chose remote for this request.
- If the requested backend is unavailable or fails, report that result. Never upload the file to another backend or switch backends automatically.

## Parse and check results

1. Pass the exact file path to the parse tool. Omit `tier` for automatic selection: PDF and images use `standard`; native Office, OpenDocument, EPUB, OFD, HTML/MHTML, and CSV/TSV use `flash`. Native document formats only support `flash`.
2. For one file, call `parse_document`. For multiple files, call `parse_documents` once with the paths in the user's order. The batch tool processes files sequentially and reports each outcome.
3. Check each returned `status`. For success, retain the `markdown_path`, `structured_content_path`, `middle_json_path`, `image_paths`, and `output_dir`; use the short `preview` only to confirm that output looks plausible.
4. If a file fails or an expected artifact path is empty, report the specific file and available error. Do not describe it as fully parsed.
5. Extracted image files are saved as artifacts. This tool does not generate image descriptions or claim to recognize image meaning.

## Read parsed text

- If the user only asked to convert files, report the artifacts and short preview. Do not read or paste the entire document by default.
- If the user asks a question about the document, or needs its body text, call `read_parsed_text` with the returned `markdown_path`.
- If no previous parse result provides a `markdown_path`, first call `parse_document` or `parse_documents` on the supplied file, then read the returned Markdown path. If the user has not supplied a file path, ask for it.
- Read in line chunks using `start_line` and `max_lines`. Continue from `next_line` while `has_more` is true when the answer depends on the full document. Set `full=true` only when the user asks for the full text or a complete text export.
- Distinguish the lines actually read from the total line count. Base answers only on text returned by the read tool; say when relevant sections were not read or parsing omitted content.

## Common issues

- A missing path or unsupported extension is an input error; report it before implying parsing started.
- Scanned PDFs and images rely on OCR; MinerU 4 automatically handles document language. Mention OCR uncertainty if the output is visibly incomplete or garbled.
- A repeated filename receives a separate output folder so earlier results are not overwritten. Always report the actual paths returned by the tool.
- Long documents may require several reads. A preview or first chunk is not evidence that the whole document was reviewed.
- A timeout, corrupt file, password-protected file, failed task, or incomplete artifact set must be reported with the tool's error and whatever outputs are available.
