#!/usr/bin/env python3
"""Dependency-free integrity checks for the PDA Question static website."""

from __future__ import annotations

import json
import posixpath
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_ORIGIN = "https://pdaquestion.com"
APP_STORE_ID = "6749604210"

HTML_FILES = (
    "index.html",
    "features.html",
    "for-parents.html",
    "for-professionals.html",
    "what-is-pda.html",
    "resources.html",
    "about.html",
    "download.html",
    "support.html",
    "privacy.html",
    "terms.html",
    "terms-california.html",
    "404.html",
)

CANONICALS = {
    "index.html": f"{PRODUCTION_ORIGIN}/",
    "features.html": f"{PRODUCTION_ORIGIN}/features.html",
    "for-parents.html": f"{PRODUCTION_ORIGIN}/for-parents.html",
    "for-professionals.html": f"{PRODUCTION_ORIGIN}/for-professionals.html",
    "what-is-pda.html": f"{PRODUCTION_ORIGIN}/what-is-pda.html",
    "resources.html": f"{PRODUCTION_ORIGIN}/resources.html",
    "about.html": f"{PRODUCTION_ORIGIN}/about.html",
    "download.html": f"{PRODUCTION_ORIGIN}/download.html",
    "support.html": f"{PRODUCTION_ORIGIN}/support.html",
    "privacy.html": f"{PRODUCTION_ORIGIN}/privacy.html",
    "terms.html": f"{PRODUCTION_ORIGIN}/terms.html",
    "terms-california.html": f"{PRODUCTION_ORIGIN}/terms.html",
}

SITEMAP_URLS = (
    f"{PRODUCTION_ORIGIN}/",
    f"{PRODUCTION_ORIGIN}/features.html",
    f"{PRODUCTION_ORIGIN}/for-parents.html",
    f"{PRODUCTION_ORIGIN}/for-professionals.html",
    f"{PRODUCTION_ORIGIN}/what-is-pda.html",
    f"{PRODUCTION_ORIGIN}/resources.html",
    f"{PRODUCTION_ORIGIN}/about.html",
    f"{PRODUCTION_ORIGIN}/download.html",
    f"{PRODUCTION_ORIGIN}/support.html",
    f"{PRODUCTION_ORIGIN}/privacy.html",
    f"{PRODUCTION_ORIGIN}/terms.html",
)

PACKAGE_FILES = {
    "package.json",
    "package-lock.json",
    "npm-shrinkwrap.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "bun.lock",
    "bun.lockb",
}

PRIVATE_KEY_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}
TEXT_SUFFIXES = {
    "",
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}


class SiteHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[int] = []
        self.ids: set[str] = set()
        self.duplicate_ids: set[str] = set()
        self.references: list[tuple[str, str]] = []
        self.aria_references: list[tuple[str, str]] = []
        self.canonicals: list[str] = []
        self.smart_app_banners: list[str] = []
        self.robots_directives: list[str] = []
        self.json_ld_blocks: list[str] = []
        self._json_ld_buffer: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name.lower(): value or "" for name, value in attrs}
        tag = tag.lower()

        element_id = attributes.get("id")
        if element_id:
            if element_id in self.ids:
                self.duplicate_ids.add(element_id)
            self.ids.add(element_id)

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.headings.append(int(tag[1]))

        if tag == "a" and attributes.get("name"):
            self.ids.add(attributes["name"])

        if tag in {"a", "link"} and attributes.get("href"):
            self.references.append((f"{tag}[href]", attributes["href"]))
        if tag in {"img", "script", "source"} and attributes.get("src"):
            self.references.append((f"{tag}[src]", attributes["src"]))
        if tag == "source" and attributes.get("srcset"):
            for candidate in attributes["srcset"].split(","):
                value = candidate.strip().split(" ", 1)[0]
                if value:
                    self.references.append(("source[srcset]", value))

        for attribute in ("aria-controls", "aria-describedby", "aria-labelledby"):
            if attributes.get(attribute):
                for target_id in attributes[attribute].split():
                    self.aria_references.append((attribute, target_id))

        if tag == "link" and "canonical" in attributes.get("rel", "").lower().split():
            self.canonicals.append(attributes.get("href", ""))

        if tag == "meta":
            name = attributes.get("name", "").lower()
            content = attributes.get("content", "")
            if name == "apple-itunes-app":
                self.smart_app_banners.append(content)
            elif name in {"robots", "googlebot"}:
                self.robots_directives.append(content.lower())

        if tag == "script" and attributes.get("type", "").lower() == "application/ld+json":
            self._json_ld_buffer = []

    def handle_data(self, data: str) -> None:
        if self._json_ld_buffer is not None:
            self._json_ld_buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._json_ld_buffer is not None:
            self.json_ld_blocks.append("".join(self._json_ld_buffer).strip())
            self._json_ld_buffer = None


class LegalMainTextParser(HTMLParser):
    """Extract visible main content while ignoring route-specific tables of contents."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_main = False
        self.ignored_depth = 0
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name.lower(): value or "" for name, value in attrs}
        tag = tag.lower()
        if tag == "main":
            self.in_main = True
            return
        if not self.in_main:
            return
        if self.ignored_depth:
            self.ignored_depth += 1
            return
        classes = attributes.get("class", "").split()
        if tag == "nav" and "toc" in classes:
            self.ignored_depth = 1

    def handle_endtag(self, tag: str) -> None:
        if not self.in_main:
            return
        if self.ignored_depth:
            self.ignored_depth -= 1
            return
        if tag.lower() == "main":
            self.in_main = False

    def handle_data(self, data: str) -> None:
        if self.in_main and not self.ignored_depth:
            normalized = " ".join(data.split())
            if normalized:
                self.text.append(normalized)


errors: list[str] = []
assertions = 0


def check(condition: bool, message: str) -> None:
    global assertions
    assertions += 1
    if not condition:
        errors.append(message)


def parse_html(path: Path) -> SiteHTMLParser:
    parser = SiteHTMLParser()
    try:
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
    except (OSError, UnicodeError) as exc:
        errors.append(f"{path.relative_to(ROOT)} could not be parsed: {type(exc).__name__}")
    return parser


def resolve_local_reference(source: Path, reference: str) -> tuple[Path | None, str]:
    parts = urlsplit(reference)
    if parts.scheme or parts.netloc:
        return None, ""

    fragment = unquote(parts.fragment)
    raw_path = unquote(parts.path)
    if not raw_path:
        return source, fragment

    if raw_path == "/":
        relative = "index.html"
    elif raw_path.startswith("/"):
        relative = posixpath.normpath(raw_path.lstrip("/"))
    else:
        source_parent = source.relative_to(ROOT).parent.as_posix()
        relative = posixpath.normpath(posixpath.join(source_parent, raw_path))

    if relative == ".":
        relative = "index.html"
    target = (ROOT / relative).resolve()
    try:
        target.relative_to(ROOT)
    except ValueError:
        return ROOT / "__outside_repository__", fragment

    if target.is_dir():
        target = target / "index.html"
    elif not target.exists() and not target.suffix:
        html_alias = target.with_suffix(".html")
        if html_alias.exists():
            target = html_alias
    return target, fragment


def validate_source_guardrails() -> None:
    forbidden_values = (
        ("protected app-backend hostname", "pda-app-" + "backend.vercel.app"),
        ("OpenAI API hostname", "api." + "openai.com"),
    )
    likely_endpoint_patterns = (
        re.compile(r"https?://[^\s\"']*openai\.com/v1(?:/|\b)", re.IGNORECASE),
        re.compile(r"https?://[^\s\"']*openai\.azure\.com/openai/deployments", re.IGNORECASE),
    )
    private_key_marker = re.compile(rb"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")

    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        relative = path.relative_to(ROOT)
        lowered_name = path.name.lower()
        check(lowered_name not in PACKAGE_FILES, f"Package manifest is not approved: {relative}")
        check(
            not (lowered_name == ".env" or lowered_name.startswith(".env.")),
            f"Environment file is not allowed: {relative}",
        )
        check(path.suffix.lower() not in PRIVATE_KEY_SUFFIXES, f"Private-key file type is not allowed: {relative}")

        try:
            data = path.read_bytes()
        except OSError as exc:
            errors.append(f"Could not inspect {relative}: {type(exc).__name__}")
            continue

        check(not private_key_marker.search(data), f"Private-key material detected in: {relative}")
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = data.decode("utf-8", errors="replace")
        for label, value in forbidden_values:
            check(value.lower() not in text.lower(), f"Unexpected {label} in: {relative}")
        for pattern in likely_endpoint_patterns:
            check(not pattern.search(text), f"Likely client-side OpenAI API endpoint in: {relative}")


def validate_html() -> dict[Path, SiteHTMLParser]:
    parsed: dict[Path, SiteHTMLParser] = {}
    for filename in HTML_FILES:
        path = ROOT / filename
        check(path.is_file(), f"Missing expected HTML file: {filename}")
        if not path.is_file():
            continue
        parser = parse_html(path)
        parsed[path] = parser

        check(parser.headings.count(1) == 1, f"{filename} must contain exactly one H1")
        check(bool(parser.headings) and parser.headings[0] == 1, f"{filename} must start its heading outline with H1")
        for previous, current in zip(parser.headings, parser.headings[1:]):
            check(current <= previous + 1, f"{filename} skips heading level H{previous} to H{current}")
        check(not parser.duplicate_ids, f"{filename} contains duplicate element IDs")
        for attribute, target_id in parser.aria_references:
            check(target_id in parser.ids, f"{filename} has unresolved {attribute} target: {target_id}")
        for index, block in enumerate(parser.json_ld_blocks, start=1):
            try:
                json.loads(block)
            except json.JSONDecodeError:
                errors.append(f"{filename} contains invalid JSON-LD block #{index}")
            else:
                check(True, "")

    for source, parser in parsed.items():
        for context, reference in parser.references:
            target, fragment = resolve_local_reference(source, reference)
            if target is None:
                continue
            relative_source = source.relative_to(ROOT)
            try:
                relative_target = target.relative_to(ROOT)
            except ValueError:
                relative_target = target
            check(target.is_file(), f"{relative_source} has unresolved {context}: {reference}")
            if fragment and target.is_file() and target.suffix.lower() == ".html":
                target_parser = parsed.get(target) or parse_html(target)
                check(
                    fragment in target_parser.ids,
                    f"{relative_source} has unresolved fragment #{fragment} in {relative_target}",
                )
    return parsed


def validate_canonicals(parsed: dict[Path, SiteHTMLParser]) -> None:
    for filename, expected in CANONICALS.items():
        parser = parsed.get(ROOT / filename)
        if not parser:
            continue
        check(parser.canonicals == [expected], f"{filename} canonical must remain {expected}")
        for canonical in parser.canonicals:
            parts = urlsplit(canonical)
            check(
                parts.scheme == "https" and parts.netloc == "pdaquestion.com",
                f"{filename} canonical must use the production HTTPS hostname",
            )
    not_found = parsed.get(ROOT / "404.html")
    if not_found:
        directives = ",".join(not_found.robots_directives)
        check("noindex" in directives, "404.html must contain a noindex directive")


def validate_terms_consistency() -> None:
    substantive_text: dict[str, tuple[str, ...]] = {}
    for filename in ("terms.html", "terms-california.html"):
        parser = LegalMainTextParser()
        try:
            parser.feed((ROOT / filename).read_text(encoding="utf-8"))
            parser.close()
        except (OSError, UnicodeError) as exc:
            errors.append(f"{filename} substantive text could not be parsed: {type(exc).__name__}")
            return
        substantive_text[filename] = tuple(parser.text)

    check(
        substantive_text["terms.html"] == substantive_text["terms-california.html"],
        "terms.html and terms-california.html must remain substantively synchronized outside their known TOC/ID differences",
    )


def validate_sitemap_and_robots() -> None:
    sitemap_path = ROOT / "sitemap.xml"
    check(sitemap_path.is_file(), "Missing sitemap.xml")
    if sitemap_path.is_file():
        try:
            tree = ET.parse(sitemap_path)
            root = tree.getroot()
            namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            urls = tuple((node.text or "").strip() for node in root.findall("s:url/s:loc", namespace))
        except (ET.ParseError, OSError):
            errors.append("sitemap.xml is not valid XML")
        else:
            check(urls == SITEMAP_URLS, "sitemap.xml must contain only the expected primary canonical URLs")
            check(len(urls) == len(set(urls)), "sitemap.xml must not contain duplicate URLs")
            check(f"{PRODUCTION_ORIGIN}/index.html" not in urls, "sitemap.xml must not include /index.html")
            check(
                f"{PRODUCTION_ORIGIN}/terms-california.html" not in urls,
                "sitemap.xml must not include terms-california.html",
            )
            check(f"{PRODUCTION_ORIGIN}/404.html" not in urls, "sitemap.xml must not include 404.html")
            for url in urls:
                parts = urlsplit(url)
                check(
                    parts.scheme == "https" and parts.netloc == "pdaquestion.com",
                    "All sitemap URLs must use the production HTTPS hostname",
                )

    robots_path = ROOT / "robots.txt"
    check(robots_path.is_file(), "Missing robots.txt")
    if robots_path.is_file():
        lines = {line.strip() for line in robots_path.read_text(encoding="utf-8").splitlines()}
        check(
            f"Sitemap: {PRODUCTION_ORIGIN}/sitemap.xml" in lines,
            "robots.txt must point to the production sitemap",
        )


def validate_manifest_and_css() -> None:
    manifest_path = ROOT / "site.webmanifest"
    check(manifest_path.is_file(), "Missing site.webmanifest")
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            errors.append("site.webmanifest is not valid JSON")
        else:
            check(isinstance(manifest, dict), "site.webmanifest must contain a JSON object")
            for icon in manifest.get("icons", []):
                source = icon.get("src", "") if isinstance(icon, dict) else ""
                target, _ = resolve_local_reference(manifest_path, source)
                check(target is not None and target.is_file(), "site.webmanifest references a missing local icon")

    css_path = ROOT / "assets/css/styles.css"
    check(css_path.is_file(), "Missing assets/css/styles.css")
    if css_path.is_file():
        css = css_path.read_text(encoding="utf-8")
        for match in re.finditer(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)", css, re.IGNORECASE):
            reference = match.group(2).strip()
            if reference.startswith(("data:", "http://", "https://", "#")):
                continue
            target, _ = resolve_local_reference(css_path, reference)
            check(target is not None and target.is_file(), f"styles.css references a missing local asset: {reference}")


def validate_app_store_ids(parsed: dict[Path, SiteHTMLParser]) -> None:
    app_store_urls: list[str] = []
    banner_ids: list[str] = []
    for path, parser in parsed.items():
        text = path.read_text(encoding="utf-8")
        app_store_urls.extend(re.findall(r"https://apps\.apple\.com/[^\"'\s<]+", text))
        for banner in parser.smart_app_banners:
            match = re.search(r"(?:^|,)\s*app-id=(\d+)", banner)
            check(match is not None, f"{path.name} has a malformed Smart App Banner app ID")
            if match:
                banner_ids.append(match.group(1))

    check(bool(app_store_urls), "At least one App Store URL must remain present")
    for url in app_store_urls:
        match = re.search(r"/id(\d+)(?:[/?#]|$)", url)
        check(match is not None, "Every App Store URL must contain an app ID")
        if match:
            check(match.group(1) == APP_STORE_ID, "App Store URLs must retain app ID 6749604210")
    check(bool(banner_ids), "Smart App Banner metadata must remain present")
    for banner_id in banner_ids:
        check(banner_id == APP_STORE_ID, "Smart App Banner metadata must retain app ID 6749604210")


def validate_domain_file() -> None:
    cname = ROOT / "CNAME"
    check(cname.is_file(), "Missing CNAME")
    if cname.is_file():
        check(cname.read_text(encoding="utf-8").strip().lower() == "pdaquestion.com", "CNAME must remain pdaquestion.com")


def main() -> int:
    validate_source_guardrails()
    parsed = validate_html()
    validate_canonicals(parsed)
    validate_terms_consistency()
    validate_sitemap_and_robots()
    validate_manifest_and_css()
    validate_app_store_ids(parsed)
    validate_domain_file()

    if errors:
        print(f"Website integrity validation failed with {len(errors)} issue(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Website integrity validation passed: {assertions} assertions across {len(HTML_FILES)} HTML files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
