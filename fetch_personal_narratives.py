"""
fetch_sources.py

Inputs:
  Excel: C:/Users/rrgas/Documents/research_project/references/personal_narratives.xlsx

Outputs:
  Extracted text (.txt) saved to:
    C:/Users/rrgas/Documents/research_project/unprocessed

  Original fetched artifacts (pdf/html/docx/txt/bin) saved to:
    C:/Users/rrgas/Documents/research_project/references

Features:
- Resume support via checkpoint file in unprocessed/
- Skips already-successful items unless --force
- Optional resume at last failure
- Playwright rendering fallback for JS-heavy pages (HTML only)
- Never overwrite existing outputs:
    - If a raw/text filename already exists, save as __v2, __v3, ...

Install:
  python3 -m pip install pandas openpyxl requests beautifulsoup4 lxml pypdf python-docx playwright
  python3 -m playwright install

Run:
  python3 scripts\\fetch_sources.py
"""

from __future__ import annotations

import os
import re
import csv
import time
import json
import hashlib
import argparse
from typing import Optional, Tuple, Dict, Any

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Optional dependencies
try:
    from pypdf import PdfReader  # type: ignore
except Exception:
    PdfReader = None  # type: ignore

try:
    import docx  # python-docx
except Exception:
    docx = None  # type: ignore

try:
    from playwright.sync_api import sync_playwright  # type: ignore
except Exception:
    sync_playwright = None  # type: ignore


# ---------------------------
# CONFIG
# ---------------------------
INPUT_XLSX = r"C:\Users\rrgas\Documents\research_project\references\personal_narratives.xlsx"

TEXT_OUT_DIR = r"C:\Users\rrgas\Documents\research_project\unprocessed"
RAW_OUT_DIR = r"C:\Users\rrgas\Documents\research_project\references"

COL_ID = "ID"
COL_TITLE = "Title"
COL_AUTHOR = "Author / Source"
COL_YEAR = "Year"
COL_TYPE = "Type"
COL_NOTES = "Main Focus / Notes"
COL_URL = "URL"

REQUEST_TIMEOUT = 30
SLEEP_BETWEEN_REQUESTS_SEC = 0.75
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Logs + checkpoint live with the extracted text outputs
CHECKPOINT_PATH = os.path.join(TEXT_OUT_DIR, "_fetch_checkpoint.json")
LOG_CSV = os.path.join(TEXT_OUT_DIR, "_fetch_log.csv")

# Extraction thresholds for HTML
MIN_TEXT_CHARS_NORMAL = 800
MIN_TEXT_CHARS_PLAYWRIGHT = 500


# ---------------------------
# HELPERS
# ---------------------------
def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def slugify(s: str, max_len: int = 80) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", "_", s)
    s = s.strip("_")
    if not s:
        s = "untitled"
    return s[:max_len]


def short_hash(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8", errors="ignore")).hexdigest()[:10]


def guess_ext_from_url(url: str) -> str:
    url_l = (url or "").lower()
    base = url_l.split("?")[0]
    for ext in (".pdf", ".docx", ".txt", ".html", ".htm"):
        if base.endswith(ext):
            return ext
    return ""


def id_prefix(row_id: Any, url: str) -> str:
    sid = str(row_id).strip() if row_id is not None else ""
    if sid and sid.lower() != "nan":
        try:
            return f"{int(float(sid)):03d}"
        except Exception:
            return slugify(sid, 20)
    return f"urlhash_{short_hash(url)}"


def make_item_key(row_id: Any, url: str) -> str:
    sid = str(row_id).strip() if row_id is not None else ""
    if sid and sid.lower() != "nan":
        return f"id:{sid}"
    return f"url:{short_hash(url)}"


def unique_path(path: str) -> str:
    """
    Never overwrite an existing file. If path exists, version it:
      file.ext -> file__v2.ext -> file__v3.ext ...
    """
    if not os.path.exists(path):
        return path

    base, ext = os.path.splitext(path)
    n = 2
    while True:
        candidate = f"{base}__v{n}{ext}"
        if not os.path.exists(candidate):
            return candidate
        n += 1


def detect_content_kind(resp: requests.Response, url: str) -> str:
    ctype = (resp.headers.get("Content-Type") or "").lower()
    url_ext = guess_ext_from_url(url)

    if "application/pdf" in ctype or url_ext == ".pdf":
        return "pdf"
    if ("application/vnd.openxmlformats-officedocument.wordprocessingml.document" in ctype) or url_ext == ".docx":
        return "docx"
    if "text/plain" in ctype or url_ext == ".txt":
        return "txt"
    if "text/html" in ctype or "application/xhtml+xml" in ctype or url_ext in (".html", ".htm") or url_ext == "":
        return "html"
    return "unknown"


def html_to_text(html: str) -> Tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")

    title = ""
    if soup.title and soup.title.get_text(strip=True):
        title = soup.title.get_text(strip=True)

    for tag in soup(["script", "style", "noscript", "svg", "canvas", "form", "aside"]):
        tag.decompose()

    for selector in ["header", "footer", "nav"]:
        for tag in soup.select(selector):
            tag.decompose()

    container = None
    for sel in ["article", "main", "div[role='main']"]:
        found = soup.select_one(sel)
        if found:
            container = found
            break
    if container is None:
        container = soup.body or soup

    lines = []
    for block in container.find_all(["h1", "h2", "h3", "p", "li", "blockquote"]):
        txt = block.get_text(" ", strip=True)
        if not txt:
            continue
        if len(txt) < 20 and block.name != "h1":
            continue
        lines.append(txt)

    text = "\n".join(lines).strip()
    if not text:
        text = container.get_text("\n", strip=True)

    h1 = soup.find("h1")
    if h1:
        h1t = h1.get_text(" ", strip=True)
        if h1t and (not title or len(h1t) > len(title) / 2):
            title = h1t

    return title.strip(), text.strip()


def pdf_bytes_to_text(pdf_bytes: bytes) -> str:
    if PdfReader is None:
        raise RuntimeError("pypdf not installed. Run: python3 -m pip install pypdf")
    import io
    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            parts.append("")
    return "\n\n".join(p.strip() for p in parts if p is not None).strip()


def docx_bytes_to_text(docx_bytes: bytes) -> str:
    if docx is None:
        raise RuntimeError("python-docx not installed. Run: python3 -m pip install python-docx")
    import io
    f = io.BytesIO(docx_bytes)
    document = docx.Document(f)
    paras = [p.text.strip() for p in document.paragraphs if p.text and p.text.strip()]
    return "\n".join(paras).strip()


def write_txt(out_path: str, metadata: dict, body_text: str) -> None:
    header = [
        f"Title: {metadata.get('title','')}",
        f"Author/Source: {metadata.get('author','')}",
        f"Year: {metadata.get('year','')}",
        f"Type: {metadata.get('type','')}",
        f"URL: {metadata.get('url','')}",
        f"Final_URL: {metadata.get('final_url','')}",
        f"Fetched_UTC: {metadata.get('fetched_utc','')}",
        f"Fetch_Method: {metadata.get('fetch_method','')}",
        f"Raw_File: {metadata.get('raw_file','')}",
        "",
        "----- BEGIN CONTENT -----",
        "",
    ]
    with open(out_path, "w", encoding="utf-8", errors="ignore") as f:
        f.write("\n".join(header))
        f.write(body_text.strip() + "\n")


def load_checkpoint(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"version": 1, "items": {}, "last_failure_key": None}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("items", {})
        data.setdefault("last_failure_key", None)
        return data
    except Exception:
        backup = path + ".corrupt_backup"
        try:
            os.replace(path, backup)
        except Exception:
            pass
        return {"version": 1, "items": {}, "last_failure_key": None}


def save_checkpoint(path: str, data: Dict[str, Any]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def playwright_render_html(url: str, timeout_ms: int = 30000) -> Tuple[str, str]:
    if sync_playwright is None:
        raise RuntimeError(
            "Playwright not installed. Run: python3 -m pip install playwright && python3 -m playwright install"
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 720},
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        final_url = page.url
        html = page.content()
        context.close()
        browser.close()
        return final_url, html


def build_paths(row_id: Any, title: str, url: str, kind: str) -> Tuple[str, str]:
    """
    Returns (text_out_path, raw_out_path) BEFORE uniqueness adjustments.
    """
    prefix = id_prefix(row_id, url)
    base = f"{prefix}__{slugify(title)}"

    text_out = os.path.join(TEXT_OUT_DIR, f"{base}.txt")

    if kind == "pdf":
        raw_ext = ".pdf"
    elif kind == "docx":
        raw_ext = ".docx"
    elif kind == "txt":
        raw_ext = ".txt"
    elif kind == "html":
        raw_ext = ".html"
    else:
        raw_ext = ".bin"

    raw_out = os.path.join(RAW_OUT_DIR, f"{base}{raw_ext}")
    return text_out, raw_out


def fetch_one_requests(session: requests.Session, url: str) -> Tuple[str, str, bytes]:
    resp = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    resp.raise_for_status()
    kind = detect_content_kind(resp, url)
    return kind, resp.url, resp.content


def save_raw(kind: str, raw_path: str, content: bytes, html_text: Optional[str] = None) -> None:
    if kind == "html":
        if html_text is None:
            html_text = content.decode("utf-8", errors="ignore")
        with open(raw_path, "w", encoding="utf-8", errors="ignore") as f:
            f.write(html_text)
    else:
        with open(raw_path, "wb") as f:
            f.write(content)


# ---------------------------
# MAIN
# ---------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch sources, save raw artifacts to references/, save text to unprocessed/."
    )
    parser.add_argument(
        "--resume-from-last-failure",
        action="store_true",
        help="Start processing at the first item that failed in the last run (based on checkpoint).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch even if checkpoint says the item already succeeded.",
    )
    parser.add_argument(
        "--no-playwright",
        action="store_true",
        help="Disable Playwright fallback rendering (even if installed).",
    )
    args = parser.parse_args()

    ensure_dir(TEXT_OUT_DIR)
    ensure_dir(RAW_OUT_DIR)

    df = pd.read_excel(INPUT_XLSX)

    for col in [COL_URL, COL_TITLE]:
        if col not in df.columns:
            raise ValueError(f"Missing required column '{col}' in spreadsheet. Found: {list(df.columns)}")

    checkpoint = load_checkpoint(CHECKPOINT_PATH)
    items_state: Dict[str, Any] = checkpoint.get("items", {})
    last_failure_key: Optional[str] = checkpoint.get("last_failure_key")

    start_idx = 0
    if args.resume_from_last_failure and last_failure_key:
        for idx, row in df.iterrows():
            url = str(row.get(COL_URL, "")).strip()
            key = make_item_key(row.get(COL_ID, None), url)
            if key == last_failure_key:
                start_idx = int(idx)
                break

    log_exists = os.path.exists(LOG_CSV)
    with open(LOG_CSV, "a", newline="", encoding="utf-8") as log_f:
        writer = csv.DictWriter(
            log_f,
            fieldnames=[
                "id",
                "title",
                "url",
                "final_url",
                "status",
                "kind",
                "raw_file",
                "text_file",
                "fetch_method",
                "error",
            ],
        )
        if not log_exists:
            writer.writeheader()

        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})

        for idx, row in df.iterrows():
            if int(idx) < start_idx:
                continue

            url = str(row.get(COL_URL, "")).strip()
            title = str(row.get(COL_TITLE, "")).strip()
            row_id = row.get(COL_ID, None)
            key = make_item_key(row_id, url)

            if not url or url.lower() == "nan":
                items_state[key] = {"status": "skipped", "error": "Missing URL", "ts": time.time()}
                checkpoint["items"] = items_state
                checkpoint["last_failure_key"] = key
                save_checkpoint(CHECKPOINT_PATH, checkpoint)

                writer.writerow(
                    {
                        "id": row_id,
                        "title": title,
                        "url": url,
                        "final_url": "",
                        "status": "skipped",
                        "kind": "",
                        "raw_file": "",
                        "text_file": "",
                        "fetch_method": "",
                        "error": "Missing URL",
                    }
                )
                continue

            if not args.force:
                prev = items_state.get(key)
                if prev and prev.get("status") == "ok":
                    continue

            try:
                kind, final_url, content = fetch_one_requests(session, url)
                fetch_method = "requests"

                # Build paths and apply "never overwrite" rule
                text_out_path, raw_out_path = build_paths(row_id, title, url, kind)
                raw_out_path = unique_path(raw_out_path)
                text_out_path = unique_path(text_out_path)

                extracted_title = ""
                body_text = ""

                if kind == "html":
                    html = content.decode("utf-8", errors="ignore")
                    extracted_title, body_text = html_to_text(html)

                    # Playwright fallback for thin extraction
                    if (
                        (not args.no_playwright)
                        and sync_playwright is not None
                        and len(body_text.strip()) < MIN_TEXT_CHARS_NORMAL
                    ):
                        pw_final_url, pw_html = playwright_render_html(url)
                        pw_title, pw_text = html_to_text(pw_html)
                        if len(pw_text.strip()) >= max(MIN_TEXT_CHARS_PLAYWRIGHT, len(body_text.strip())):
                            final_url = pw_final_url
                            extracted_title = pw_title or extracted_title
                            body_text = pw_text
                            fetch_method = "playwright"
                            # Save rendered HTML as raw
                            save_raw("html", raw_out_path, b"", html_text=pw_html)
                        else:
                            save_raw("html", raw_out_path, content, html_text=html)
                    else:
                        save_raw("html", raw_out_path, content, html_text=html)

                elif kind == "pdf":
                    save_raw("pdf", raw_out_path, content)
                    body_text = pdf_bytes_to_text(content)

                elif kind == "docx":
                    save_raw("docx", raw_out_path, content)
                    body_text = docx_bytes_to_text(content)

                elif kind == "txt":
                    save_raw("txt", raw_out_path, content)
                    body_text = content.decode("utf-8", errors="ignore").strip()

                else:
                    save_raw("unknown", raw_out_path, content)
                    html = content.decode("utf-8", errors="ignore")
                    extracted_title, body_text = html_to_text(html)

                # If extracted title is better, try to re-base filenames (still never overwrite)
                better_title = extracted_title if extracted_title and len(extracted_title) > len(title or "") else title
                if better_title and better_title != title:
                    new_text_out, new_raw_out = build_paths(row_id, better_title, url, kind)
                    new_raw_out = unique_path(new_raw_out)
                    new_text_out = unique_path(new_text_out)

                    # Rename raw to match improved title if possible
                    try:
                        os.replace(raw_out_path, new_raw_out)
                        raw_out_path = new_raw_out
                        title = better_title
                        text_out_path = new_text_out
                    except Exception:
                        # Keep existing names if rename fails
                        pass

                metadata = {
                    "id": None,
                    "title": title or extracted_title,
                    "author": str(row.get(COL_AUTHOR, "")).strip(),
                    "year": str(row.get(COL_YEAR, "")).strip(),
                    "type": str(row.get(COL_TYPE, "")).strip(),
                    "notes": str(row.get(COL_NOTES, "")).strip(),
                    "url": url,
                    "final_url": final_url,
                    "kind": kind,
                    "fetch_method": fetch_method,
                    "raw_file": os.path.basename(raw_out_path),
                    "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "row_index": int(idx),
                    "checkpoint_key": key,
                }

                sid = str(row_id).strip() if row_id is not None else ""
                if sid and sid.lower() != "nan":
                    try:
                        metadata["id"] = int(float(sid))
                    except Exception:
                        metadata["id"] = sid

                if not body_text or len(body_text.strip()) < 50:
                    body_text = (body_text or "").strip()
                    body_text += (
                        "\n\n[NOTE] Extraction produced little or no text. "
                        "This may be JS-rendered, image-based, or otherwise difficult to extract.\n"
                    )

                write_txt(text_out_path, metadata, body_text)

                items_state[key] = {
                    "status": "ok",
                    "kind": kind,
                    "fetch_method": fetch_method,
                    "final_url": final_url,
                    "raw_file": os.path.basename(raw_out_path),
                    "text_file": os.path.basename(text_out_path),
                    "ts": time.time(),
                }
                checkpoint["items"] = items_state
                checkpoint["last_failure_key"] = None
                save_checkpoint(CHECKPOINT_PATH, checkpoint)

                writer.writerow(
                    {
                        "id": row_id,
                        "title": title,
                        "url": url,
                        "final_url": final_url,
                        "status": "ok",
                        "kind": kind,
                        "raw_file": os.path.basename(raw_out_path),
                        "text_file": os.path.basename(text_out_path),
                        "fetch_method": fetch_method,
                        "error": "",
                    }
                )

            except Exception as e:
                items_state[key] = {"status": "error", "error": repr(e), "ts": time.time()}
                checkpoint["items"] = items_state
                checkpoint["last_failure_key"] = key
                save_checkpoint(CHECKPOINT_PATH, checkpoint)

                writer.writerow(
                    {
                        "id": row_id,
                        "title": title,
                        "url": url,
                        "final_url": "",
                        "status": "error",
                        "kind": "",
                        "raw_file": "",
                        "text_file": "",
                        "fetch_method": "",
                        "error": repr(e),
                    }
                )

            time.sleep(SLEEP_BETWEEN_REQUESTS_SEC)


if __name__ == "__main__":
    main()
