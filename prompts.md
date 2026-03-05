### 🔧 Prompt #1: Config Loader

```
<prompt>
# Task: Implement a robust configuration loader for the email bot. Read `spec.md` and `blueprint.md` for guidance

## Context
You are building an automated email processing system. Configuration is defined in `config.py`, but sensitive values (SMTP credentials) must be loaded from environment variables.

## Requirements
1. Read the `config.py` file (provided below) and inject environment variables as:
   - `SMTP_USER` → `config['smtp_username']`
   - `SMTP_PASS` → `config['smtp_password']`
2. Validate that all required keys are present and non-empty in `config`.
3. Raise clear exceptions (e.g., `ConfigError`) if:
   - Any required key is missing
   - Required environment variables are unset
4. Log at `INFO` level once config is loaded successfully.

## Required Keys (all must be present and non-empty after env injection)
```python
config_keys = [
    'source_folder',
    'processed_folder',
    'polling_interval_seconds',
    'bot_name',
    'bot_email',
    'ollama_api_url',
    'ollama_model',
    'ollama_temperature',
    'ollama_prefix_prompt',
    'allowed_attachment_extensions',
    'smtp_host',
    'smtp_port',
    'smtp_use_tls',
    'smtp_use_ssl',
    'smtp_username',  # injected from env
    'smtp_password',  # injected from env
]
```

## Starter: `config.py`
```python
# DO NOT MODIFY THIS FILE
# Only inject env vars at runtime

config = {
    'source_folder': './emails/source',
    'processed_folder': './emails/processed',
    'polling_interval_seconds': 10,
    'bot_name': 'Support Bot',
    'bot_email': 'bot@example.com',
    'ollama_api_url': 'http://localhost:11434/api/generate',
    'ollama_model': 'llama3',
    'ollama_temperature': 0.7,
    'ollama_prefix_prompt': 'You are a helpful email assistant.',
    'allowed_attachment_extensions': ['.txt', '.md', '.py'],
    'smtp_host': 'smtp.example.com',
    'smtp_port': 587,
    'smtp_use_tls': True,
    'smtp_use_ssl': False,
}
```

## Deliverable
Implement a `get_config()` function in a new module `config_loader.py`:
- Returns a *mutable copy* of config with env vars injected
- Raises `ConfigError` on validation failure
- Logs success at `INFO` level

## Constraints
- Use `os.environ.get()` (not `environ[]`) to avoid KeyError
- Use `typing` for return type: `def get_config() -> dict[str, Any]`
- Use `logging` module for logging
- No external dependencies beyond stdlib

## Tests to Write (in `test_config_loader.py`)
1. `test_get_config_success()` — all env vars set → config validated
2. `test_get_config_missing_env()` — `SMTP_USER` missing → raises `ConfigError`
3. `test_get_config_empty_value()` — `ollama_model=""` → raises `ConfigError`
4. `test_get_config_logs_success()` — asserts log call at INFO level

## Important Notes
- `config.py` must NOT import `os` or `logging` — it’s pure data.
- Do *not* modify `config.py` — inject values at runtime.
</prompt>
```

---

### 🔧 Prompt #2: Email Parser

```markdown
<prompt>
# Task: Parse `.eml` files to extract headers and body. Read `spec.md` and `blueprint.md` for guidance

## Context
You are building an email parser for the bot. Each `.eml` file is a raw MIME email.

## Requirements
1. Implement `parse_email(path: Path) -> dict` in `email_parser.py`
2. Extract:
   - `from`: first `From` header (use `email.utils.parseaddr` for clean extraction)
   - `subject`: raw `Subject` header
   - `message_id`: raw `Message-Id` header
   - `references`: raw `References` header
   - `in_reply_to`: raw `In-Reply-To` header
   - `body`: **text/plain** if present, otherwise **text/html** → convert to plain text
3. Use `email.message_from_file()` with `BytesParser(policy=default)`

## Constraints
- If both `text/plain` and `text/html` exist, prefer `text/plain`
- If only `text/html` exists, convert to plain text (strip tags, decode HTML entities)
- Use `html2text` is NOT allowed (stdlib only) — use `html.parser.HTMLParser` if needed
- No external dependencies beyond stdlib
- Handle malformed emails gracefully: log warning, return `body = ""`

## Deliverable
```python
from pathlib import Path

def parse_email(path: Path) -> dict[str, str]:
    """Parse .eml file and return {from, subject, body, message_id, references, in_reply_to}."""
    ...
```

## Tests to Write (`test_email_parser.py`)
1. `test_parse_email_with_plain_text()` — plain body present
2. `test_parse_email_html_fallback()` — only HTML, convert cleanly
3. `test_parse_email_empty_body()` — multipart but no text → `body = ""`
4. `test_parse_email_malformed()` — invalid MIME → log warning, return empty body
5. `test_parse_email_from_subject_cleaned()` — `From` header has display name (e.g., `John Doe <john@example.com>` → `john@example.com`)

## Utility Note
You may use this HTML-to-plain helper:
```python
from html.parser import HTMLParser

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.chunks = []
    def handle_data(self, data):
        self.chunks.append(data)
    def get_text(self):
        return '\n'.join(self.chunks).strip()

def html_to_plaintext(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    return parser.get_text()
```
</prompt>
```

---

### 🔧 Prompt #3: Attachment Validator (Validation Only)

```markdown
<prompt>
# Task: Validate email attachments against allowed extensions. Read `spec.md` and `blueprint.md` for guidance

## Context
The bot must reject unsupported attachments *before* processing — using extension check.

## Requirements
1. Implement `raise_if_unsupported(email_obj, allowed_exts: list[str]) -> None` in `attachment_validator.py`
2. Use `email_obj.get_payload()` and `get_filename()` to get attachment names
3. Compare extension (case-insensitive) against `allowed_exts`
4. If any disallowed: raise `UnsupportedAttachmentError` with list of disallowed filenames

## Helper
```python
class UnsupportedAttachmentError(Exception):
    def __init__(self, disallowed_names: list[str]):
        self.disallowed_names = disallowed_names
        super().__init__(f"Unsupported attachments: {', '.join(disallowed_names)}")
```

## Constraints
- Only check extension (e.g., `.txt`, `.LOG`)
- Normalize extensions (lowercase, include leading dot)
- Skip non-attachment parts (e.g., `Content-Type: multipart/*`)
- Use `os.path.splitext()` for extraction

## Deliverable
```python
from pathlib import Path

def raise_if_unsupported(email_obj, allowed_exts: list[str]) -> None:
    """Raise UnsupportedAttachmentError if disallowed extensions found."""
    ...
```

## Tests (`test_attachment_validator.py`)
1. `test_no_attachments()` — empty → no exception
2. `test_all_allowed()` — `.txt`, `.md` → no exception
3. `test_one_unsupported()` — `.txt` + `.exe` → `UnsupportedAttachmentError(['.exe'])`
4. `test_case_insensitive()` — `.TXT`, `.Pdf` → `.pdf` not allowed
5. `test_empty_allowed_list()` — `allowed_exts = []` → any extension raises

## Important
- Do NOT read file contents yet (that’s next step)
</prompt>
```

---

### 🔧 Prompt #4: Attachment Validator (Read Content)

```markdown
<prompt>
# Task: Read content of allowed attachments. Read `spec.md` and `blueprint.md` for guidance

## Context
Now that we’ve validated attachments, read text content of allowed ones.

## Requirements
1. Implement `read_allowed_attachments(email_obj, allowed_exts: list[str]) -> list[tuple[str, str]]` in `attachment_validator.py`
2. Return list of `(filename, content_str)` for allowed attachments only
3. Attempt to decode as UTF-8. If fails, fallback to `ISO-8859-1`.
4. For `.txt`, `.md`: decode bytes → text via `payload.get_content()` or raw `get_payload(decode=True)`

## Deliverable
```python
def read_allowed_attachments(email_obj, allowed_exts: list[str]) -> list[tuple[str, str]]:
    """Return [(filename, content)] for allowed attachments."""
    ...
```

## Constraints
- Use `os.path.splitext()` to extract `.ext`
- Normalize extension to lowercase, ensure it starts with `.`
- Return filenames as-is (preserve original case)
- Skip if `get_filename()` is `None` (i.e., not an attachment)

## Tests (`test_attachment_validator.py`)
1. `test_read_txt_md_attachments()` — `.txt`, `.md` → return both
2. `test_skip_disallowed()` — `.txt`, `.exe` → only `.txt`
3. `test_utf8_fallback()` — binary `.txt` (invalid UTF-8) → fallback to `ISO-8859-1`
4. `test_read_content_correct()` — compare content to file content

## Note
You may reuse code from Step 3 — just refactor to combine.
</prompt>
```

---

### 🔧 Prompt #5: Ollama Prompt Builder

```markdown
<prompt>
# Task: Construct prompt for Ollama API. Read `spec.md` and `blueprint.md` for guidance

## Context
Compose a structured prompt with XML tags for attachments and body.

## Requirements
1. Implement `compose_ollama_prompt(config: dict, attachments: list[tuple[str, str]], body: str) -> str` in `ollama_prompt.py`
2. Format:
   1. `ollama_prefix_prompt` (if non-empty, include as-is)
   2. Each allowed attachment: `<attachment filename="f.txt">content</attachment>`
   3. Email body (if non-empty): `<email_body>body_content</email_body>`
3. Preserve exact body text — do NOT escape XML — LLM handles it (and spec says no modification).
4. No trailing whitespace or newlines beyond intentional.

## Constraints
- Use Python `f-strings` or `.format()` for XML tags
- If `attachments = []` and `body = ""`, return only `ollama_prefix_prompt` (or empty if prefix blank)
- If `body = ""` but attachments exist, **omit** `<email_body>` tag entirely (per spec)

## Deliverable
```python
def compose_ollama_prompt(config: dict, attachments: list[tuple[str, str]], body: str) -> str:
    """Build XML-wrapped prompt for Ollama."""
    ...
```

## Tests (`test_ollama_prompt.py`)
1. `test_with_prefix_and_body()` — prefix + body → correct format
2. `test_with_attachments_only()` — no body → no `<email_body>` tag
3. `test_empty_inputs()` — blank prefix, no attachments, no body → empty string
4. `test_multiple_attachments()` — correct ordering and tag structure
5. `test_preserves_newlines_in_body()` — body with `\n` preserved (not escaped)

## Important
- Do NOT escape XML special chars (`<`, `>`, `&`) — LLM expects raw body.
</prompt>
```

---

### 🔧 Prompt #6: Ollama Client (Retry-enabled API Call)

```markdown
<prompt>
# Task: Call Ollama API with retry logic. Read `spec.md` and `blueprint.md` for guidance

## Context
LLMs may fail transiently — implement robust retry.

## Requirements
1. Implement `call_ollama(prompt: str, config: dict) -> str` in `ollama_client.py`
2. Retry up to 3 times on `requests.exceptions.RequestException`
3. Use exponential backoff with jitter: `sleep(2^retry * 0.5 + random(0, 0.5))`
4. On failure after 3 retries → raise `OllamaError`
5. API call must:
   - POST to `config['ollama_api_url']`
   - JSON body: `{"model": ..., "messages": "prompt": prompt, "temperature": ...}`
   - Parse response: `response.json()['response']`
6. Log each retry attempt at `DEBUG`, final success/failure at `INFO`

## Constraints
- Use only `requests` (third-party, but essential for Ollama)
- Return only the **assistant’s response text**, not full JSON
- Do not include `user` in final output (only the reply)

## Deliverable
```python
import requests
from typing import Optional

class OllamaError(Exception):
    pass

def call_ollama(prompt: str, config: dict) -> str:
    """Call Ollama API with retry and return response text."""
    ...
```

## Tests (`test_ollama_client.py`)
1. `test_success()` — mock `requests.post().json()` → return correct text
2. `test_retry_success()` — first 2 calls fail, 3rd succeeds
3. `test_max_retries_exceeded()` — all 3 fail → raises `OllamaError`
4. `test_backoff_times_correct()` — assert `sleep()` calls match expected values
5. `test_log_retries()` — verify log calls at correct levels

## Example Ollama Response Format
```json
{
  "model": "llama3",
  "created_at": "2024-05-15T10:30:00.000Z",
  "message": {
    "role": "assistant",
    "content": "Hello, I can help with that."
  },
  "done": true
}
```
</prompt>
```

---

### 🔧 Prompt #7: SMTP Reply Composer

```markdown
<prompt>
# Task: Compose reply email message object. Read `spec.md` and `blueprint.md` for guidance

## Context
Build the reply to the sender using original email + AI response.

## Requirements
1. Implement `compose_reply_msg(original_headers: dict, reply_text: str, config: dict) -> MIMEMultipart`
2. Implement `generate_message_id(original_headers: dict, error_msg: str, config: dict) -> str`
     - Generates `my-message-id` in the format: `<[32 random hex digits]@gcfl.net>` where `[32 random hex digits]` is a randomly generated 32-digit hex string

3. Build `MIMEMultipart()` with:
   - To: `original_headers['from']`
   - From: `config['bot_email']`
   - Subject: `Re: original_headers['subject']`, but if already starts with `"Re: "`, leave as-is
   - Message-ID: `<my-message-id>`
   - In-Reply-To: `original_headers['message-id']`
   - References: `original_headers['references'] original_headers['message-id']`
   - Body (plain text):
     ```
Assistant:
<AI_REPLY_TEXT>

User:
<ORIGINAL_BODY>
     ```
4. Format:
   - Date: use `email.utils.formatdate()` from original email’s `Date` header (fallback to now)
   - Original From: `original_headers['from']`
   - Original Cc: `original_headers['cc']`
   - Original Body: verbatim (no escaping)
5. Use `MIMEText(reply_text, 'plain', 'utf-8')` for AI part, then attach original body.

## Constraints
- Do not add HTML part — only `text/plain`
- Use `email.utils.parseaddr()` to extract `name <addr>` parts
- If no `Date` header, use current time
- Ensure `On [date], ... wrote:` uses correct date format

## Deliverable
```python
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email.utils

def compose_reply_msg(original_headers: dict, reply_text: str, config: dict) -> MIMEMultipart:
    """Compose reply message."""
    ...
```

## Tests (`test_smtp_sender.py`)
1. `test_subject_prefix_idempotent()` — `"Re: hi"` → `"Re: hi"` (no double prefix)
2. `test_body_format_correct()` — verify structure with `get_payload()` inspection
3. `test_date_fallback()` — missing `Date` → use current time
4. `test_original_body_preserved()` — body unchanged, including line endings

## Example Output Body
```
Hello! I'll help you with that.

On Wed, 15 May 2024 10:00:00 +0000, John Doe <john@example.com> wrote:
Hi there,
I need help with X.
```
</prompt>
```

---

### 🔧 Prompt #8: SMTP Sender (Send + Handle Failure)

```markdown
<prompt>
# Task: Send reply via SMTP and handle failures correctly. Read `spec.md` and `blueprint.md` for guidance

## Context
Sending may fail — we must exit on SMTP failure (per spec).

## Requirements
1. Implement `send_email(msg: MIMEMultipart, config: dict) -> None` in `smtp_sender.py`
2. Support:
   - `smtp_use_tls`: use `starttls()` after connect
   - `smtp_use_ssl`: use `SMTP_SSL` if `True` (skip `starttls`)
   - Auth with `config['smtp_username']`, `config['smtp_password']`
3. On *any* `smtplib.SMTPException`:
   - Log error at `ERROR` level
   - Exit the program with code `1` (`sys.exit(1)`)
4. Log success at `INFO` level.

## Deliverable
```python
import smtplib
import sys

def send_email(msg: MIMEMultipart, config: dict) -> None:
    """Send email via SMTP, exit on failure."""
    ...
```

## Tests (`test_smtp_sender.py`)
1. `test_send_tls_success()` — mock `smtplib.SMTP` → `starttls()` called
2. `test_send_ssl_success()` — `smtp_use_ssl=True` → `SMTP_SSL` used
3. `test_auth_called()` — verify `login()` with correct username/password
4. `test_failure_exits()` — `smtplib.SMTPServerDisconnected` → logs + `sys.exit(1)`
5. `test_no_hang_on_error()` — assert program terminates, doesn’t continue

## Important
- Use `with smtplib.SMTP(...) as server:` to ensure cleanup
- Use `msg.as_string()` for the payload
- `To`/`From` from message headers override `sendmail()` args — that’s fine
</prompt>
```

---

### 🔧 Prompt #9: Error Notification Handlers

```markdown
<prompt>
# Task: Send special error notices (unsupported attachment / API failure). Read `spec.md` and `blueprint.md` for guidance

## Context
For certain failures, notify sender *before* archiving.

## Requirements
1. Implement two functions in `smtp_sender.py`:
   - `send_unsupported_attachment_notice(original_headers: dict, disallowed_names: list[str], allowed_exts: list[str], config: dict) -> None`
   - `send_api_failure_notice(original_headers: dict, error_msg: str, config: dict) -> None`
   - `generate_message_id(original_headers: dict, error_msg: str, config: dict) -> str`
     - Generates `my-message-id` in the format: `<[32 random hex digits]@gcfl.net>` where `[32 random hex digits]` is a randomly generated 32-digit hex string
2. Both:
   - Compose reply message (not `compose_reply_msg`)
   - Subject: `"Error processing your email"`
   - Message-Id: `<my-message-id>`
   - In-Reply-To: `original_headers['message-id']`
   - References: `original_headers['references'] original_headers['message-id']`
   - Body: 
     - For unsupported: `"We rejected attachments: [list]. Allowed types: [list]"`
     - For API: `"AI service failed. Error details: [error_msg]"`
   - Send using `send_email()`
3. Do NOT archive — caller handles that.

## Constraints
- Reuse `compose_reply_msg()` where possible, but override body construction
- No external dependencies
- Preserve original `From`/`Subject`/`Date`/`Message-Id`/`In-Reply-To`/`References` if useful (but subject is overwritten)

## Deliverable
```python
def send_unsupported_attachment_notice(...) -> None: ...
def send_api_failure_notice(...) -> None: ...
```

## Tests (`test_smtp_sender.py`)
1. `test_unsupported_notice_body_correct()` — verify listing of `.exe` vs allowed `.txt`
2. `test_api_notice_includes_error()` — error message appears in body
3. `test_sends_to_original_sender()` — `To: original_headers['from']`
4. `test_calls_send_email()` — assert `send_email()` is invoked

## Note
These are *not* replies — they’re error notifications.
</prompt>
```

---

### 🔧 Prompt #10: Main Orchestrator (Poll → Process → Archive Loop)

```markdown
<prompt>
# Task: Wire everything together in main polling loop. Read `spec.md` and `blueprint.md` for guidance

## Context
Final step: implement resilient, testable main loop.

## Requirements
1. Implement `main()` in `main.py`:
   - Poll `source_folder` for `.eml` files every `polling_interval_seconds`
   - Process each file **one at a time** in FIFO order (sorted by mtime)
   - On success:
     - Send reply
     - Archive `.eml` to `processed_folder`
   - On `UnsupportedAttachmentError`:
     - Send notice
     - Archive
     - Continue (no exit)
   - On API failure:
     - Retry up to 3 times (via `ollama_client`)
     - On final failure: send notice + archive
   - On SMTP failure:
     - Log error
     - Exit with code `1`
   - Log all steps at `INFO` level

2. Use `pathlib.Path` for all file paths
3. Ensure `processed_folder` exists (create if missing)
4. Sleep after each run (non-blocking poll: `time.sleep()`)

## Constraints
- Single-threaded (no concurrency)
- No infinite loop bugs: handle `InterruptedError`, `KeyboardInterrupt`
- Use `sorted(source_folder.glob("*.eml"), key=lambda p: p.stat().st_mtime)` for FIFO

## Deliverable
```python
def main():
    config = get_config()
    Path(config['processed_folder']).mkdir(parents=True, exist_ok=True)
    while True:
        ...
```

## Tests (`test_main.py`)
1. `test_success_case()` — `.eml` processed & archived
2. `test_unsupported_attachment_case()` — notice sent, archived
3. `test_api_failure_case()` — 3 retries, notice sent, archived
4. `test_smtp_failure_exits()` — raises `SystemExit` on SMTP error
5. `test_logs_info_messages()` — assert at least one INFO log per step

## Example Flow for One File
```
[INFO] Found file: input.eml
[INFO] Parsing email...
[INFO] Reading attachments...
[INFO] Calling Ollama...
[INFO] Composing reply...
[INFO] Sending reply...
[INFO] Archiving input.eml → processed/
```

## Bonus (Optional)
Add graceful shutdown on `SIGINT`: `signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))`
</prompt>
```
