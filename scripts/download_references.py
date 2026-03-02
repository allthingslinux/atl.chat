#!/usr/bin/env python3
"""Download all IRC/XMPP service documentation as markdown."""

import hashlib
import logging
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

OUTPUT_DIR = Path("references")

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def file_hash(content):
    """Calculate SHA256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def should_update(filepath, new_content):
    """Check if file needs updating by comparing hashes."""
    if not filepath.exists():
        return True
    old_content = filepath.read_text(encoding="utf-8")
    return file_hash(old_content) != file_hash(new_content)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((requests.exceptions.RequestException, requests.exceptions.HTTPError)),
    reraise=True,
)
def download_with_retry(url):
    """Download content with exponential backoff retry."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    resp = requests.get(url, timeout=30, headers=headers)
    resp.raise_for_status()
    return resp


# ============================================================================
# PROSODY
# ============================================================================


def _download_prosody_official(base_dir: Path) -> tuple[int, int, list]:
    """Download Prosody official docs from sitemap."""
    success = skipped = 0
    failed = []

    logger.info("\nFetching Prosody sitemap...")
    resp = download_with_retry("https://prosody.im/sitemap.xml")
    root = ET.fromstring(resp.content)
    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [loc.text for loc in root.findall(".//ns:loc", ns) if loc.text]
    logger.info(f"Found {len(urls)} official doc pages\n")

    for i, url in enumerate(urls, 1):
        parsed = urlparse(url)
        path = parsed.path.strip("/") or "index"
        parts = path.split("/")

        if len(parts) > 1:
            subdir = base_dir / "/".join(parts[:-1])
            filename = f"{parts[-1]}.md"
        else:
            subdir = base_dir
            filename = f"{parts[0]}.md"

        filepath = subdir / filename
        logger.info(f"[{i}/{len(urls)}] {path}")

        try:
            subdir.mkdir(parents=True, exist_ok=True)
            resp = download_with_retry(url)
            content = md(resp.text, heading_style="ATX")
            full_content = f"# {url}\n\n{content}"

            if should_update(filepath, full_content):
                filepath.write_text(full_content, encoding="utf-8")
                logger.info(f"  ✓ {filepath.relative_to(OUTPUT_DIR)}")
                success += 1
            else:
                logger.info(f"  ⊙ {filepath.relative_to(OUTPUT_DIR)} (unchanged)")
                skipped += 1
        except Exception as e:
            logger.error(f"  ✗ Failed: {e}")
            failed.append((url, str(e)))

    return success, skipped, failed


def _download_prosody_community(base_dir: Path) -> tuple[int, int, list]:
    """Download Prosody community modules."""
    success = skipped = 0
    failed = []

    logger.info("\nFetching Prosody community modules...")
    resp = download_with_retry("https://modules.prosody.im")
    soup = BeautifulSoup(resp.text, "html.parser")

    modules = []
    for link in soup.find_all("a", href=True):
        href = link.get("href")
        if href and isinstance(href, str) and href.startswith("mod_") and href.endswith(".html"):
            modules.append(href.replace(".html", ""))

    modules = sorted(set(modules))
    logger.info(f"Found {len(modules)} community modules\n")

    mod_dir = base_dir / "community_modules"
    mod_dir.mkdir(parents=True, exist_ok=True)

    for i, module in enumerate(modules, 1):
        url = f"https://modules.prosody.im/{module}.html"
        filepath = mod_dir / f"{module}.md"
        logger.info(f"[{i}/{len(modules)}] {module}")

        try:
            resp = download_with_retry(url)
            content = md(resp.text, heading_style="ATX")
            full_content = f"# {url}\n\n{content}"

            if should_update(filepath, full_content):
                filepath.write_text(full_content, encoding="utf-8")
                logger.info(f"  ✓ community_modules/{module}.md")
                success += 1
            else:
                logger.info(f"  ⊙ community_modules/{module}.md (unchanged)")
                skipped += 1
        except Exception as e:
            logger.error(f"  ✗ Failed: {e}")
            failed.append((module, str(e)))

    return success, skipped, failed


def download_prosody():
    """Download Prosody official docs and community modules."""
    logger.info("=" * 60)
    logger.info("PROSODY DOCUMENTATION")
    logger.info("=" * 60)

    base_dir = OUTPUT_DIR / "prosody"

    s1, sk1, f1 = _download_prosody_official(base_dir)
    s2, sk2, f2 = _download_prosody_community(base_dir)

    success = s1 + s2
    skipped = sk1 + sk2
    failed = f1 + f2
    total = success + skipped + len(failed)

    logger.info(f"\nProsody Summary: {success} downloaded, {skipped} skipped, {len(failed)} failed / {total} total")
    return success, skipped, failed


# ============================================================================
# UNREALIRCD
# ============================================================================


def download_unrealircd():
    """Download UnrealIRCd MediaWiki documentation."""
    logger.info("\n" + "=" * 60)
    logger.info("UNREALIRCD DOCUMENTATION")
    logger.info("=" * 60)

    base_dir = OUTPUT_DIR / "unrealircd"
    success = skipped = 0
    failed = []

    logger.info("\nFetching UnrealIRCd page list...")
    resp = download_with_retry("https://www.unrealircd.org/docs/Special:AllPages")
    soup = BeautifulSoup(resp.text, "html.parser")

    pages = []
    for link in soup.select(".mw-allpages-body a"):
        href = link.get("href")
        if href and isinstance(href, str) and href.startswith("/docs/"):
            page_name = href.replace("/docs/", "")
            # Skip special pages, sandboxes, translations
            if not any(
                x in page_name
                for x in ["Special:", "Sandbox", "Talk:", "Project:", "/en", "/es", "/fr", "/pt", "/tr", "/nl", "/zh-"]
            ):
                pages.append(page_name)

    pages = sorted(set(pages))
    logger.info(f"Found {len(pages)} documentation pages\n")

    for i, page_name in enumerate(pages, 1):
        url = f"https://www.unrealircd.org/docs/{page_name}"
        clean_name = page_name.replace("%27", "_").replace("%26", "_and_")
        parts = clean_name.split("/")

        if len(parts) > 1:
            subdir = base_dir / "/".join(parts[:-1])
            filename = f"{parts[-1]}.md"
        else:
            subdir = base_dir
            filename = f"{parts[0]}.md"

        filepath = subdir / filename
        logger.info(f"[{i}/{len(pages)}] {page_name}")

        try:
            subdir.mkdir(parents=True, exist_ok=True)
            resp = download_with_retry(url)
            content = md(resp.text, heading_style="ATX")
            full_content = f"# {url}\n\n{content}"

            if should_update(filepath, full_content):
                filepath.write_text(full_content, encoding="utf-8")
                logger.info(f"  ✓ {filepath.relative_to(OUTPUT_DIR)}")
                success += 1
            else:
                logger.info(f"  ⊙ {filepath.relative_to(OUTPUT_DIR)} (unchanged)")
                skipped += 1
        except Exception as e:
            logger.error(f"  ✗ Failed: {e}")
            failed.append((page_name, str(e)))

    logger.info(
        f"\nUnrealIRCd Summary: {success} downloaded, {skipped} skipped, {len(failed)} failed / {len(pages)} total"
    )
    return success, skipped, failed


# ============================================================================
# ATHEME
# ============================================================================


def fetch_github_files_recursive(path="doc"):
    """Recursively fetch all files from GitHub directory."""
    api_url = f"https://api.github.com/repos/atheme/atheme/contents/{path}"
    resp = download_with_retry(api_url)
    data = resp.json()

    files = []
    for item in data:
        if item["type"] == "file":
            files.append({"name": item["path"].replace("doc/", ""), "download_url": item["download_url"]})
        elif item["type"] == "dir":
            files.extend(fetch_github_files_recursive(item["path"]))

    return files


def _download_atheme_dev(base_dir: Path) -> tuple[int, int, list]:
    """Download Atheme documentation from atheme.dev sitemap."""
    success = skipped = 0
    failed = []

    logger.info("\nFetching atheme.dev sitemap...")
    resp = download_with_retry("https://atheme.dev/sitemap.xml")
    root = ET.fromstring(resp.content)
    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    urls = []
    for loc in root.findall(".//ns:loc", ns):
        url = loc.text
        if url and "/docs/" in url and "/blog/" not in url:
            urls.append(url)

    logger.info(f"Found {len(urls)} documentation pages\n")

    for i, url in enumerate(urls, 1):
        parsed = urlparse(url)
        path = parsed.path.strip("/").replace("docs/", "")

        if not path or path == "docs":
            subdir = base_dir
            filename = "index.md"
        else:
            parts = path.split("/")
            if len(parts) > 1:
                subdir = base_dir / "/".join(parts[:-1])
                filename = f"{parts[-1]}.md"
            else:
                subdir = base_dir
                filename = f"{parts[0]}.md"

        filepath = subdir / filename
        logger.info(f"[{i}/{len(urls)}] {url}")

        try:
            subdir.mkdir(parents=True, exist_ok=True)
            resp = download_with_retry(url)
            content = md(resp.text, heading_style="ATX")
            full_content = f"# {url}\n\n{content}"

            if should_update(filepath, full_content):
                filepath.write_text(full_content, encoding="utf-8")
                logger.info(f"  ✓ {filepath.relative_to(OUTPUT_DIR)}")
                success += 1
            else:
                logger.info(f"  ⊙ {filepath.relative_to(OUTPUT_DIR)} (unchanged)")
                skipped += 1
        except Exception as e:
            logger.error(f"  ✗ Failed: {e}")
            failed.append((url, str(e)))

    return success, skipped, failed


def _download_atheme_github(base_dir: Path) -> tuple[int, int, list]:
    """Download Atheme doc files from GitHub."""
    success = skipped = 0
    failed = []

    logger.info("\nFetching GitHub doc files...")
    github_files = fetch_github_files_recursive()
    logger.info(f"Found {len(github_files)} files in GitHub doc/\n")

    github_dir = base_dir / "github_doc"

    for i, file_info in enumerate(github_files, 1):
        filename = file_info["name"]
        download_url = file_info["download_url"]
        filepath = github_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"[{i}/{len(github_files)}] {filename}")

        try:
            resp = download_with_retry(download_url)
            content = resp.text

            if should_update(filepath, content):
                filepath.write_text(content, encoding="utf-8")
                logger.info(f"  ✓ github_doc/{filename}")
                success += 1
            else:
                logger.info(f"  ⊙ github_doc/{filename} (unchanged)")
                skipped += 1
        except Exception as e:
            logger.error(f"  ✗ Failed: {e}")
            failed.append((filename, str(e)))

    return success, skipped, failed


def download_atheme():
    """Download Atheme documentation from atheme.dev and GitHub."""
    logger.info("\n" + "=" * 60)
    logger.info("ATHEME DOCUMENTATION")
    logger.info("=" * 60)

    base_dir = OUTPUT_DIR / "atheme"

    s1, sk1, f1 = _download_atheme_dev(base_dir)
    s2, sk2, f2 = _download_atheme_github(base_dir)

    success = s1 + s2
    skipped = sk1 + sk2
    failed = f1 + f2
    total = success + skipped + len(failed)

    logger.info(f"\nAtheme Summary: {success} downloaded, {skipped} skipped, {len(failed)} failed / {total} total")
    return success, skipped, failed


# ============================================================================
# SLIXMPP / PYDLE (shared ReadTheDocs crawler)
# ============================================================================


def _crawl_rtd_links(base_url: str) -> list[str]:
    """Crawl a ReadTheDocs site and return a sorted list of HTML page paths."""
    visited: set[str] = set()
    to_visit = [""]
    pages: list[str] = []

    while to_visit:
        path = to_visit.pop(0)
        if path in visited:
            continue
        visited.add(path)

        url = f"{base_url}/{path}" if path else base_url
        try:
            resp = download_with_retry(url)
            soup = BeautifulSoup(resp.text, "html.parser")
            for link in soup.select("a[href]"):
                href = link.get("href", "")
                if isinstance(href, str) and href.endswith(".html") and not href.startswith("http") and "#" not in href:
                    clean_href = href.strip("/")
                    if clean_href not in visited and clean_href not in to_visit:
                        to_visit.append(clean_href)
                        pages.append(clean_href)
        except Exception as e:
            logger.warning(f"Failed to crawl {url}: {e}")

    return sorted(set(pages))


def _download_rtd_pages(base_url: str, base_dir: Path, pages: list[str]) -> tuple[int, int, list]:
    """Download a list of ReadTheDocs HTML pages as markdown files."""
    success = skipped = 0
    failed = []

    for i, page in enumerate(pages, 1):
        url = f"{base_url}/{page}"
        clean_path = page.replace(".html", "").strip("/")

        if "/" in clean_path:
            parts = clean_path.split("/")
            subdir = base_dir / "/".join(parts[:-1])
            filename = f"{parts[-1]}.md"
        else:
            subdir = base_dir
            filename = f"{clean_path}.md"

        filepath = subdir / filename
        logger.info(f"[{i}/{len(pages)}] {page}")

        try:
            subdir.mkdir(parents=True, exist_ok=True)
            resp = download_with_retry(url)
            content = md(resp.text, heading_style="ATX")
            full_content = f"# {url}\n\n{content}"

            if should_update(filepath, full_content):
                filepath.write_text(full_content, encoding="utf-8")
                logger.info(f"  ✓ {filepath.relative_to(OUTPUT_DIR)}")
                success += 1
            else:
                logger.info(f"  ⊙ {filepath.relative_to(OUTPUT_DIR)} (unchanged)")
                skipped += 1
        except Exception as e:
            logger.error(f"  ✗ Failed: {e}")
            failed.append((page, str(e)))

    return success, skipped, failed


def download_slixmpp():
    """Download Slixmpp ReadTheDocs documentation."""
    logger.info("\n" + "=" * 60)
    logger.info("SLIXMPP DOCUMENTATION")
    logger.info("=" * 60)

    base_dir = OUTPUT_DIR / "slixmpp"
    base_url = "https://slixmpp.readthedocs.io/en/latest"

    logger.info("\nCrawling Slixmpp documentation...")
    pages = _crawl_rtd_links(base_url)
    logger.info(f"Found {len(pages)} documentation pages\n")

    success, skipped, failed = _download_rtd_pages(base_url, base_dir, pages)

    logger.info(
        f"\nSlixmpp Summary: {success} downloaded, {skipped} skipped, {len(failed)} failed / {len(pages)} total"
    )
    return success, skipped, failed


# ============================================================================
# PYDLE
# ============================================================================


def download_pydle():
    """Download Pydle ReadTheDocs documentation."""
    logger.info("\n" + "=" * 60)
    logger.info("PYDLE DOCUMENTATION")
    logger.info("=" * 60)

    base_dir = OUTPUT_DIR / "pydle"
    base_url = "https://pydle.readthedocs.io/en/latest"

    logger.info("\nCrawling Pydle documentation...")
    pages = _crawl_rtd_links(base_url)
    logger.info(f"Found {len(pages)} documentation pages\n")

    success, skipped, failed = _download_rtd_pages(base_url, base_dir, pages)

    logger.info(f"\nPydle Summary: {success} downloaded, {skipped} skipped, {len(failed)} failed / {len(pages)} total")
    return success, skipped, failed


# ============================================================================
# MAIN
# ============================================================================


def main():
    # Parse arguments
    services = sys.argv[1:] if len(sys.argv) > 1 else ["prosody", "unrealircd", "atheme", "slixmpp", "pydle"]

    available = {
        "prosody": download_prosody,
        "unrealircd": download_unrealircd,
        "atheme": download_atheme,
        "slixmpp": download_slixmpp,
        "pydle": download_pydle,
    }

    # Validate services
    invalid = [s for s in services if s not in available]
    if invalid:
        logger.error(f"Invalid service(s): {', '.join(invalid)}")
        logger.info(f"Available: {', '.join(available.keys())}")
        sys.exit(1)

    logger.info(f"Downloading: {', '.join(services)}\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_success = all_skipped = 0
    all_failed = []

    # Download selected services
    for service in services:
        s, sk, f = available[service]()
        all_success += s
        all_skipped += sk
        all_failed.extend(f)

    # Final summary
    total = all_success + all_skipped + len(all_failed)
    logger.info("\n" + "=" * 60)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Downloaded: {all_success}/{total}")
    logger.info(f"  Skipped (unchanged): {all_skipped}/{total}")
    logger.info(f"  Failed: {len(all_failed)}/{total}")

    if all_failed:
        logger.info("\nFailed items:")
        for item, error in all_failed[:10]:  # Show first 10
            logger.info(f"  - {item}: {error}")
        if len(all_failed) > 10:
            logger.info(f"  ... and {len(all_failed) - 10} more")

    logger.info(f"\nAll documentation saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
