# Automated Email Processing and AI-Powered Reply Bot Blueprint

## 🔁 Round 1: High-Level Modular Decomposition (5 Core Modules)

| Module | Responsibility |
|--------|----------------|
| `1. config_loader.py` | Load & validate `config.py`, inject env vars |
| `2. email_parser.py` | Parse `.eml` file → extract headers, body, attachments |
| `3. attachment_validator.py` | Validate attachment extensions + read allowed content |
| `4. ollama_client.py` | Send prompt → receive response with retries |
| `5. smtp_sender.py` | Compose & send reply (including error notices) |
| `6. archiver.py` | Move file from `source_folder` → `processed_folder` |
| `7. main.py` | Orchestrator: polling loop, error handling, control flow |

✅ *Note*: We’ll combine `config_loader` and `main`’s env loading; `main` may depend on all others. But we’ll build them one-by-one.

---

## 🔁 Round 2: Micro-Step Decomposition (17 micro-steps)

| # | Step | Scope | Test Strategy |
|---|------|-------|---------------|
| **1** | ✅ Create `config.py` skeleton (dict with placeholders) + load env vars into `config.py` via `os.environ` | Minimal config + validation stub | Unit test: ensure missing env var raises exception |
| **2** | ✅ Implement `email_parser.get_email_headers(path)` → `dict {from, subject, message-id, references, in-reply-to}` | Uses `email.message_from_file()` | Parse known `.eml` fixture; assert headers correct |
| **3** | ✅ Implement `email_parser.get_email_body(email_obj)` → `str` (prefer `text/plain`, fallback to `text/html`) | Uses `email.message_from_file()` and `get_payload()` | Test with both plain & HTML emails |
| **4** | ✅ Implement `attachment_validator.get_allowed_attachments(email_obj, allowed_exts)` → `list[(filename, content_str)]` | Filter by extension, read text content | Mock with `.txt` + `.exe`; assert only `.txt` returned |
| **5** | ✅ Implement `attachment_validator.raise_if_unsupported(email_obj, allowed_exts)` → `None or raise UnsupportedAttachmentError` | Check before processing | Assert raises on `.exe`, doesn’t on `.txt` |
| **6** | ✅ Implement `ollama_client.compose_prompt(config, attachments, body)` → `str` | Per spec: prefix + attachments XML + body XML | Unit test with known inputs/outputs |
| **7** | ✅ Implement `ollama_client.send_prompt(prompt, config)` → `str` (single call, no retry yet) | Uses `requests.post()` to Ollama API | Mock `requests.post()` in tests; assert correct body |
| **8** | ✅ Add retry logic: `ollama_client.send_with_retry(prompt, config, max_retries=3)` → `str` | Exponential backoff? (optional but safe) | Simulate failures → assert retry logic & final failure |
| **9** | ✅ Implement `smtp_sender.compose_reply(config, original_email, reply_text)` → `MIMEText` | Follow subject/body spec exactly | Test: `Re: ` prefixing, `On [date], ... wrote:` |
| **10** | ✅ Implement `smtp_sender.send_email(msg, config)` → `None` | Uses `smtplib.SMTP` / `SMTP_SSL` per config | Mock SMTP context; assert send called |
| **11** | ✅ Implement `archiver.move_to_processed(original_path, processed_folder)` → `Path` | `shutil.move()` + ensure dir exists | Unit: move temp file, assert removed + dest exists |
| **12** | ✅ Implement error reply logic: `smtp_sender.send_api_failure_notice(original_email, error_msg, config)` → `None` | Compose & send notice *before* archiving | Mock SMTP & date; assert body contains error |
| **13** | ✅ Implement error reply logic: `smtp_sender.send_unsupported_attachment_notice(original_email, disallowed_names, allowed_exts, config)` → `None` | List disallowed + allowed types | Test with `['.txt', '.md']` + `.exe` → list in body |
| **14** | ✅ Implement main loop: `main.poll_source_folder(config)` → `list[Path]` | `glob.glob('*.eml')` + filter | Unit: create test `.eml`, assert found |
| **15** | ✅ Implement main flow: `main.process_email(email_path, config)` → `None` | Wire steps 2–13, error handling | Integration test: `.eml` with body + `.txt` |
| **16** | ✅ Implement main loop error handling: SMTP → log + exit; API → retry + notice + archive | Per spec: **SMTP halt**, API → retry → notice + archive | Simulate SMTP/OLLA failures; assert log + exit |
| **17** | ✅ Wire `main.py` to orchestrate: loop, try/except, logging at INFO level | Single-threaded, resilient, no hanging | End-to-end test: run loop with 3 `.eml` files |

✅ *Step 14–17 form the full loop*.

But Step 15 is too big for safe, incremental implementation. Let’s **optimize down to 10–12 key steps**.

---

## 🔁 Round 3: Final Step Sizing (10 Optimized, Self-Contained Steps)

We now refine the 17 steps into **10 minimal, testable, non-breaking increments** — each is:

- ✅ **Ready to TDD**
- ✅ **Builds directly on previous**
- ✅ **No orphaned code**
- ✅ **Includes mocking-ready interfaces**

> **Key principle**: Each step produces a *working*, *tested* artifact. No dangling logic.

| # | Step Title | Scope | Deliverable | Test Strategy |
|---|-------------|-------|-------------|---------------|
| **1** | **Config Loader: Load & validate config** | `config.py` + env injection | `config.get_config()` → `dict` with env-validated keys | Unit test: missing `SMTP_USER` raises exception |
| **2** | **Email Parser: Extract headers + body** | `.eml` → `{from, subject, body, message-id, references, in-reply-to}` | `parse_email(path: Path) -> dict` | Test with `sample.eml` fixtures |
| **3** | **Attachment Validator: Validate extensions** | Check `.ext` against `allowed_exts` | `validate_attachments(email_obj, allowed_exts)` → no exception or `raise UnsupportedAttachmentError` | Test with `.txt` vs `.exe` |
| **4** | **Attachment Validator: Extract allowed content** | `[(filename, content)]` for allowed | `read_allowed_attachments(email_obj, allowed_exts) -> list[tuple[str, str]]` | Test: read `.txt`, skip `.pdf`/`.exe` |
| **5** | **Ollama Prompt Builder: Construct XML-wrapped prompt** | `{prefix, attachments, body}` → `prompt_str` | `compose_ollama_prompt(config, attachments, body)` → `str` | Unit: assert `<email_body>` only if body present |
| **6** | **Ollama Client: Single API call with retry** | Retry up to 3 × with jitter | `call_ollama(prompt, config) → str or raise` | Mock `requests.post()`; simulate 3 failures |
| **7** | **SMTP Reply Composer: Assemble reply message** | Original + AI text → `MIMEMultipart` | `compose_reply_msg(original_headers, reply_text, config) -> MIMEMultipart` | Test subject: `"Re: hi"` → `"Re: Re: hi"` (no double prefix) |
| **8** | **SMTP Sender: Send message + handle SMTP failure** | `send_email(msg, config)` → `None` | Use `smtplib` per config | Mock `smtplib.SMTP`; assert `sendmail()` called; raise on connect fail |
| **9** | **Error Notification Handlers: Unsupported attachment & API failure** | Notify sender *before* archiving | Two functions: `send_unsupported_notice(...)`, `send_api_failure_notice(...)` | Test: `disallowed = ['.exe']`, ensure list in body |
| **10** | **Main Orchestrator: Poll → process → archive loop** | `while True: ...` + error handling per spec | `main()` loop with logging, no infinite hang on error | Integration: 3 `.eml`s in `source/`, assert 1 moved + 1 error-archived |

✅ All steps can be **tested in isolation or integration**.

Now we move to the **final prompt set** — each tagged and ready for an LLM.

---

# 🧩 Final Prompt Set (Ready for Code Generation)

Each prompt below includes:

- ✅ **What to build**
- ✅ **Dependencies (previous steps)**
- ✅ **Test expectations**
- ✅ **Constraints (e.g., XML format, error handling)**
- ✅ **Code style** (PEP 8, `typing`, `logging`, `pathlib`)

> 📝 **All prompts assume prior steps have been implemented and tested.**  
> 🧪 Use `pytest` (or `unittest`) with fixtures/mocks.

---

prompts are located in `prompts.md`
