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
LEGACY_TERMS_FRAGMENTS = ("top", "site-nav", "main", "law", "contact")

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
        self.refresh_redirects: list[str] = []
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
            if attributes.get("http-equiv", "").lower() == "refresh":
                self.refresh_redirects.append(content)

        if tag == "script" and attributes.get("type", "").lower() == "application/ld+json":
            self._json_ld_buffer = []

    def handle_data(self, data: str) -> None:
        if self._json_ld_buffer is not None:
            self._json_ld_buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._json_ld_buffer is not None:
            self.json_ld_blocks.append("".join(self._json_ld_buffer).strip())
            self._json_ld_buffer = None


class VisibleTextParser(HTMLParser):
    """Extract normalized visible text while excluding script and style contents."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.ignored_depth: int | None = None
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.depth += 1
        if self.ignored_depth is None and tag.lower() in {"script", "style"}:
            self.ignored_depth = self.depth

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        return

    def handle_endtag(self, tag: str) -> None:
        if self.ignored_depth == self.depth:
            self.ignored_depth = None
        self.depth = max(0, self.depth - 1)

    def handle_data(self, data: str) -> None:
        if self.ignored_depth is None:
            value = " ".join(data.split())
            if value:
                self.text.append(value)


class ElementTextParser(HTMLParser):
    """Extract text from one element selected by its stable HTML ID."""

    def __init__(self, target_id: str) -> None:
        super().__init__(convert_charrefs=True)
        self.target_id = target_id
        self.depth = 0
        self.target_depth: int | None = None
        self.found = False
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.depth += 1
        attributes = {name.lower(): value or "" for name, value in attrs}
        if self.target_depth is None and attributes.get("id") == self.target_id:
            self.target_depth = self.depth
            self.found = True

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.target_depth == self.depth:
            self.target_depth = None
        self.depth = max(0, self.depth - 1)

    def handle_data(self, data: str) -> None:
        if self.target_depth is not None:
            value = " ".join(data.split())
            if value:
                self.text.append(value)


errors: list[str] = []
assertions = 0


def check(condition: bool, message: str) -> None:
    global assertions
    assertions += 1
    if not condition:
        errors.append(message)


def normalize_policy_text(value: str) -> str:
    translations = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-"})
    return re.sub(r"\s+", " ", value.translate(translations).casefold()).strip()


def visible_text(source: str) -> str:
    parser = VisibleTextParser()
    parser.feed(source)
    parser.close()
    return normalize_policy_text(" ".join(parser.text))


def element_text(source: str, target_id: str) -> str:
    parser = ElementTextParser(target_id)
    parser.feed(source)
    parser.close()
    check(parser.found, f"Expected policy element is missing: #{target_id}")
    return normalize_policy_text(" ".join(parser.text))


def matches(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE | re.DOTALL) is not None


def without_explicit_negations(text: str) -> str:
    """Remove only the approved clauses that expressly reject dispute machinery."""

    safe_clauses = (
        r"\b(?:these terms )?do not require (?:pre-dispute )?arbitration\b",
        r"\b(?:these terms )?do not waive participation in (?:a )?class action\b",
        r"\b(?:these terms )?do not require every user to bring a claim exclusively in san diego county\b",
        r"\b(?:these terms )?do not waive any non-waivable jurisdictional or consumer right\b",
    )
    for clause in safe_clauses:
        text = re.sub(clause, " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def parse_hex_color(value: str) -> tuple[int, int, int] | None:
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(character * 2 for character in value)
    if len(value) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", value):
        return None
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def contrast_ratio(foreground: tuple[int, int, int], background: tuple[int, int, int]) -> float:
    def luminance(color: tuple[int, int, int]) -> float:
        channels = []
        for channel in color:
            normalized = channel / 255
            channels.append(normalized / 12.92 if normalized <= 0.04045 else ((normalized + 0.055) / 1.055) ** 2.4)
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    lighter, darker = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


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


def validate_terms_architecture(parsed: dict[Path, SiteHTMLParser]) -> None:
    terms = parsed.get(ROOT / "terms.html")
    legacy = parsed.get(ROOT / "terms-california.html")
    if not terms or not legacy:
        return

    try:
        terms_source = (ROOT / "terms.html").read_text(encoding="utf-8")
        legacy_source = (ROOT / "terms-california.html").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"Terms architecture could not be inspected: {type(exc).__name__}")
        return

    check(not terms.refresh_redirects, "terms.html must remain the authoritative non-redirecting Terms document")
    check(
        len(legacy.refresh_redirects) == 1
        and matches(legacy.refresh_redirects[0], r"^\s*0\s*;\s*url\s*=\s*terms\.html\s*$"),
        "terms-california.html must retain a no-JavaScript fallback redirect to terms.html",
    )
    legacy_robots = ",".join(legacy.robots_directives)
    check("noindex" in legacy_robots, "terms-california.html must remain noindex as a legacy route")
    legacy_links = [reference for context, reference in legacy.references if context == "a[href]"]
    check(
        any(urlsplit(reference).path in {"terms.html", "/terms.html"} for reference in legacy_links),
        "terms-california.html must provide a visible fallback link to terms.html",
    )

    authoritative_text = visible_text(terms_source)
    legacy_text = visible_text(legacy_source)
    check("terms of service" in authoritative_text, "terms.html must remain visibly identified as the Terms of Service")
    check(len(authoritative_text.split()) >= 900, "terms.html must retain a substantive authoritative Terms agreement")
    check(len(legacy_text.split()) <= 120, "terms-california.html must remain a short legacy notice, not duplicate Terms")
    duplicate_section_concepts = (
        "eligibility and permitted use",
        "limitation of liability",
        "indemnification",
        "intellectual property and content rights",
        "payment terms",
        "governing law and jurisdiction",
    )
    for concept in duplicate_section_concepts:
        check(concept not in legacy_text, f"terms-california.html must not duplicate substantive section: {concept}")

    check(
        matches(legacy_source, r"location\.replace\s*\(\s*[\"']terms\.html[\"']\s*\+"),
        "terms-california.html must replace the legacy URL with the authoritative terms.html route",
    )
    check("location.hash" in legacy_source, "terms-california.html redirect must inspect the incoming fragment")
    check(
        matches(
            legacy_source,
            r"(?:indexOf\s*\(\s*window\.location\.hash\s*\)|includes\s*\(\s*window\.location\.hash\s*\)).{0,80}\?.{0,45}window\.location\.hash.{0,45}:\s*[\"'][\"']",
        ),
        "Unknown or empty legacy fragments must fall back to terms.html without a fragment",
    )
    check(
        not matches(legacy_source, r"location\.replace\s*\([^)]*terms-california"),
        "terms-california.html redirect must not loop back to the legacy route",
    )
    check(
        not matches(legacy_source, r"<script\b[^>]*\bsrc\s*="),
        "Legacy fragment preservation must remain dependency-free and first-party",
    )
    check(
        not matches(legacy_text, r"\bcalifornia (?:agreement|terms|addendum)\b"),
        "Legacy route must not present a separate California agreement or addendum",
    )
    for fragment in LEGACY_TERMS_FRAGMENTS:
        check(fragment in terms.ids, f"Authoritative Terms target is missing for legacy fragment: #{fragment}")
        check(f'"#{fragment}"' in legacy_source, f"Legacy Terms redirect must preserve/map fragment: #{fragment}")


def validate_policy_decisions() -> None:
    try:
        privacy = (ROOT / "privacy.html").read_text(encoding="utf-8")
        terms = (ROOT / "terms.html").read_text(encoding="utf-8")
        home = (ROOT / "index.html").read_text(encoding="utf-8")
        download = (ROOT / "download.html").read_text(encoding="utf-8")
        professionals = (ROOT / "for-professionals.html").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"Policy decision guardrails could not read website content: {type(exc).__name__}")
        return

    raw_sources = {
        "terms.html": terms,
        "privacy.html": privacy,
        "index.html": home,
        "download.html": download,
        "for-professionals.html": professionals,
    }
    policy_text = {filename: visible_text(source) for filename, source in raw_sources.items()}
    terms_text = policy_text["terms.html"]
    privacy_text = policy_text["privacy.html"]

    # Effective dates must be labeled, prospective, and distinct from the document update date.
    for filename in ("privacy.html", "terms.html"):
        text = policy_text[filename]
        check(
            matches(text, r"\blast updated\s*:\s*august 22, 2026\b"),
            f"{filename} must label August 22, 2026 as the Last Updated date",
        )
        check(
            matches(text, r"\brevised effective date\s*:\s*september 21, 2026\b"),
            f"{filename} must label September 21, 2026 as the Revised Effective Date",
        )
        check("january 6, 2025" not in text, f"{filename} must not restore the January 6, 2025 governing date")
        check("retroactiv" not in text, f"{filename} must use direct prospective wording rather than retroactivity language")
    check(
        matches(terms_text, r"revised terms.{0,45}take effect september 21, 2026.{0,90}on or after"),
        "terms.html must state prospectively when the revised Terms apply",
    )
    check(
        matches(privacy_text, r"revised policy text.{0,45}takes effect september 21, 2026.{0,80}from that date forward"),
        "privacy.html must distinguish its update date from prospective effectiveness",
    )

    # Removed arbitration, class-waiver, jury-waiver, and exclusive-venue machinery.
    dispute_scan = without_explicit_negations(terms_text)
    removed_dispute_patterns = (
        ("mandatory or binding arbitration", r"\b(?:mandatory|binding|required|compulsory)\s+(?:pre-dispute\s+)?arbitration\b|\barbitration (?:is|will be) (?:mandatory|required|binding|compulsory)\b|\b(?:must|required to|shall|agree to)\b.{0,65}\barbitrat\w*\b|\bshall be resolved by.{0,35}arbitration\b"),
        ("American Arbitration Association / AAA dispute process", r"\bamerican arbitration association\b|\b(?:aaa.{0,80}(?:arbitrat|dispute)|(?:arbitrat|dispute).{0,80}aaa)\b"),
        ("arbitration opt-out", r"\b(?:arbitrat\w*.{0,100}opt[- ]?out|opt[- ]?out.{0,100}arbitrat\w*)\b"),
        ("class-action waiver", r"\bclass[- ]action waiver\b"),
        ("class or representative proceeding prohibition", r"\b(?:may|shall|can|must) not\b.{0,110}\b(?:class|representative) proceeding\b|\bnot as\b.{0,80}\bclass member\b|\bno (?:class|representative) (?:actions?|proceedings?) (?:are )?(?:allowed|permitted)\b|\bprohibit\w*.{0,65}\b(?:class|representative) (?:action|proceeding)\b"),
        ("mandatory individual-only proceeding", r"\b(?:claim|dispute)s?\b.{0,110}\bonly\b.{0,45}\bindividual (?:capacity|arbitration)\b|\bindividual[- ]only arbitration\b"),
        ("jury waiver", r"\b(?:waiv\w*.{0,75}jury|jury.{0,75}waiv\w*)\b"),
        ("exclusive San Diego venue", r"\b(?:exclusive(?:ly)?|sole)\b.{0,110}\bsan diego\b|\bsan diego\b.{0,110}\b(?:exclusive(?:ly)?|sole)\b"),
    )
    for label, pattern in removed_dispute_patterns:
        check(not matches(dispute_scan, pattern), f"terms.html must not restore {label}")
    check(
        not matches(terms_text, r"\bclick(?:ing)?\s+[\"']?accept[\"']?\b"),
        "terms.html must not restore a click-ACCEPT assent fiction",
    )
    check(not matches(terms_text, r"\bexport control\b"), "terms.html must not restore removed export-control boilerplate")
    check(
        matches(terms_text, r"on or after (?:the )?revised effective date.{0,80}(?:agree|agreement)"),
        "terms.html must retain use-based assent tied to the Revised Effective Date",
    )
    check(
        matches(privacy_text, r"privacy policy is a notice.{0,100}not.{0,35}(?:accept|contract)"),
        "privacy.html must remain a notice rather than a separate acceptance contract",
    )

    # Submitted content remains user-owned and is licensed only for requested operations.
    submitted_license = element_text(terms, "submitted-content-license")
    feedback_license = element_text(terms, "feedback-license")
    check(matches(submitted_license, r"retain.{0,45}rights.{0,45}(?:submit|content)"), "Submitted-content rights must remain with the user")
    check(
        matches(submitted_license, r"limited, non-exclusive, royalty-free license"),
        "The submitted-content processing license must remain expressly limited and non-exclusive",
    )
    submitted_license_requirements = (
        ("provide the requested Services", r"provide the services (?:you|the user) request"),
        ("required operational-provider transmission", r"process and transmit.{0,90}operational providers?.{0,70}(?:required|needed)"),
        ("security, maintenance, and troubleshooting", r"secure, maintain, and troubleshoot"),
        ("applicable legal obligations", r"comply with applicable legal obligations.{0,35}(?:where appropriate|when appropriate)"),
    )
    for label, pattern in submitted_license_requirements:
        check(matches(submitted_license, pattern), f"Submitted-content license must remain limited to {label}")
    prohibited_license_purposes = (
        ("improvement", r"\bimprov\w*\b"),
        ("development", r"\bdevelop\w*\b"),
        ("training", r"\btrain\w*\b"),
        ("research", r"\bresearch\w*\b"),
        ("product/model analysis", r"\banaly[sz]\w*.{0,45}\b(?:product|model)\b|\b(?:product|model)\b.{0,45}\banaly[sz]\w*\b"),
    )
    for label, pattern in prohibited_license_purposes:
        check(not matches(submitted_license, pattern), f"Submitted-content license must not authorize ordinary content for {label}")
    check(
        matches(feedback_license, r"voluntar\w*.{0,75}feedback.{0,180}(?:develop|improv)"),
        "Voluntary feedback must remain separately defined from ordinary submitted content",
    )
    content_rights = element_text(terms, "content-rights")
    for permission in ("copy", "save", "edit", "adapt", "export", "share"):
        check(permission in content_rights, f"Generated-output permission must retain the right to {permission}")
    check(
        matches(terms_text, r"historical developer fine-tuning.{0,120}current request generation.{0,100}does not itself retrain"),
        "terms.html must distinguish historical fine-tuning from current generation",
    )
    check(
        matches(privacy_text, r"does not include.{0,100}workflow.{0,140}current questions.{0,180}foundation-model training"),
        "privacy.html must not present current Questions as a foundation-model training workflow",
    )
    check(
        matches(privacy_text, r"openai's handling.{0,180}(?:api terms|terms and policies).{0,180}organization settings.{0,180}contractual controls"),
        "privacy.html must accurately condition OpenAI handling on provider terms, settings, and controls",
    )
    check(
        matches(privacy_text, r"feedback and operational or diagnostic metadata.{0,100}(?:maintain|improve)"),
        "privacy.html must retain the separate feedback/operational-metadata reliability use",
    )
    for item_source in re.findall(r"<li\b[^>]*>(.*?)</li>", privacy, re.IGNORECASE | re.DOTALL):
        item = visible_text(item_source)
        if matches(item, r"\b(?:question|professional letter|submitted content)s?\b"):
            check(
                not matches(item, r"\b(?:product|model)?\s*(?:improv\w*|train\w*|research\w*)\b"),
                "Privacy use-list must not authorize Question or Professional Letter content for improvement, training, or research",
            )

    # Direct use is 18+; 13+ remains only an App Store/storefront content rating.
    direct_use_pattern = r"(?:direct use|direct users?|use.{0,35}directly).{0,100}(?:18\+?|18 years|adults?)|(?:18\+?|18 years|adults?).{0,100}(?:direct use|direct users?|use.{0,35}directly)"
    rating_pattern = r"(?:app store|storefront).{0,80}13\+.{0,100}(?:content|storefront) rating"
    for filename in ("terms.html", "privacy.html", "index.html", "download.html"):
        text = policy_text[filename]
        check(matches(text, direct_use_pattern), f"{filename} must retain the direct-use 18+ rule")
        check(matches(text, rating_pattern), f"{filename} must characterize 13+ as an App Store/storefront content rating")
    for filename in ("terms.html", "privacy.html"):
        check(
            matches(policy_text[filename], r"13\+.{0,120}does not change.{0,120}(?:18|eligibility|direct users?)"),
            f"{filename} must state that the 13+ rating does not change contractual eligibility",
        )
    check(
        matches(privacy_text, r"(?:if|where) coppa.{0,90}applies"),
        "privacy.html must condition COPPA handling on legal applicability",
    )
    categorical_coppa_patterns = (
        r"\bcoppa (?:does not|doesn't|never) appl",
        r"\bnot (?:subject|covered) (?:to|by) coppa\b",
        r"\bcoppa categorically applies\b|\bcoppa applies to (?:pda question|all)\b",
    )
    for pattern in categorical_coppa_patterns:
        check(not matches(privacy_text, pattern), "privacy.html must not make a categorical COPPA applicability claim")

    # Families may share outputs with support professionals; institutions may not submit client data as a current service.
    for filename in ("terms.html", "privacy.html", "for-professionals.html"):
        text = policy_text[filename]
        check(
            matches(text, r"famil\w*.{0,180}(?:share|shared).{0,150}(?:teacher|clinician|professional|support)|(?:professional|teacher|clinician)s?.{0,160}(?:famil\w*.{0,90}share|share.{0,90}famil\w*)"),
            f"{filename} must preserve family sharing with support professionals",
        )
        check(
            matches(text, r"\b(?:not|does not|do not)\b.{0,220}\b(?:institution|organization|school|clinic|professional practice|client|patient|student)\b"),
            f"{filename} must retain the institutional/professional submission boundary",
        )
        check(
            not matches(text, r"\b(?:professional|organization|institution)s?\s+(?:may|can|are authorized to)\s+(?:independently )?(?:submit|enter|upload).{0,100}\b(?:client|student|patient)\b"),
            f"{filename} must not authorize professional submission of client/student/patient data",
        )

    # Named statutory rights are conditional on the law applying to PDA Question and the relevant processing.
    check(
        matches(privacy_text, r"\bif the california consumer privacy act.{0,180}\bapplies to pda question.{0,180}\bcalifornia residents may have rights\b"),
        "California rights must remain expressly conditional on CCPA/CPRA applicability",
    )
    check(
        matches(privacy_text, r"\bif the gdpr.{0,180}\bapplies to pda question.{0,180}\bit may provide rights\b"),
        "EEA/UK/Swiss rights must remain expressly conditional on named-law applicability",
    )
    unconditional_rights_patterns = (
        r"\b(?:all|every) california residents? (?:automatically )?(?:has|have|is entitled|are entitled)\b",
        r"\bas a california resident,? you (?:automatically )?(?:have|are entitled)\b",
        r"\bcalifornia residents have the following (?:ccpa|privacy) rights\b",
        r"\b(?:all|every) (?:eea|uk|swiss) users? (?:automatically )?(?:has|have|is entitled|are entitled)\b",
        r"\bif you (?:live|reside|are located) in (?:the )?(?:eea|uk|switzerland).{0,60}you have\b",
    )
    for pattern in unconditional_rights_patterns:
        check(not matches(privacy_text, pattern), "privacy.html must not promise named-law rights based solely on location")

    # Indemnity remains limited to qualifying third-party claims and excludes ordinary use/own alleged harm.
    indemnity = element_text(terms, "indemnity")
    check(matches(indemnity, r"indemnif\w*.{0,100}third-party claim"), "Indemnity must remain limited to third-party claims")
    check(matches(indemnity, r"unlawful conduct.{0,50}willful misuse"), "Indemnity must retain the unlawful/willful-misuse boundary")
    check(matches(indemnity, r"does not require.{0,110}ordinary use permitted"), "Indemnity must exclude ordinary permitted use")
    check(matches(indemnity, r"does not require.{0,180}your own allegation.{0,45}harmed"), "Indemnity must exclude the user's own alleged harm")
    check(matches(indemnity, r"user content.{0,55}(?:unlawful|infringes)"), "Content indemnity must remain tied to unlawful or infringing content")
    positive_indemnity = " ".join(
        sentence for sentence in re.split(r"(?<=[.!?])\s+", indemnity) if not matches(sentence, r"\b(?:do|does) not\b")
    )
    broad_indemnity_patterns = (
        r"indemnif\w*.{0,180}\byour (?:ordinary )?use of the services\b",
        r"indemnif\w*.{0,180}\b(?:reliance on|relying on) (?:an? )?(?:output|response|service)\b",
        r"indemnif\w*.{0,220}\bclaim.{0,80}\bharm(?:ed)? (?:to|by) you\b",
    )
    for pattern in broad_indemnity_patterns:
        check(not matches(positive_indemnity, pattern), "terms.html must not restore broad ordinary-use/reliance/own-harm indemnity")

    # Apple controls current subscription refunds and App deletion is not cancellation.
    payment = element_text(terms, "payment")
    check(
        matches(payment, r"refund eligibility and refund processing.{0,80}(?:governed|controlled) by apple"),
        "Payment terms must state that Apple governs refund eligibility and processing",
    )
    check(
        matches(terms_text, r"deleting the app.{0,90}does not cancel.{0,70}(?:apple )?subscription"),
        "Terms must state that deleting the App does not cancel an Apple subscription",
    )
    blanket_refund_patterns = (
        r"\bno refunds\b",
        r"\bnot entitled to (?:any|a) refund\b",
        r"\ball (?:fees|payments|purchases) are non-refundable\b",
        r"\brefunds? (?:are|is) never (?:available|provided|permitted)\b",
    )
    for pattern in blanket_refund_patterns:
        check(not matches(terms_text, pattern), "terms.html must not restore a blanket no-refund promise")

    # Safety and provider distinctions are core policy architecture, not generic boilerplate.
    check(
        matches(terms_text, r"educational support.{0,150}not.{0,80}(?:clinical|healthcare|diagnos|treat)"),
        "terms.html must retain the educational/non-clinical safety boundary",
    )
    check(matches(terms_text, r"not an emergency.{0,180}(?:911|crisis service)"), "terms.html must retain emergency guidance")
    check(
        matches(privacy_text, r"operational service providers selected by pda question")
        and matches(privacy_text, r"user-directed sharing and external links"),
        "privacy.html must distinguish selected operational providers from user-chosen destinations",
    )


def validate_policy_link_contrast_source() -> None:
    """Guard the source tokens/classes behind the browser-verified age-disclosure contrast."""

    try:
        css = (ROOT / "assets/css/styles.css").read_text(encoding="utf-8")
        pages = {
            filename: (ROOT / filename).read_text(encoding="utf-8")
            for filename in ("index.html", "download.html")
        }
    except (OSError, UnicodeError) as exc:
        errors.append(f"Policy-link contrast source guard could not read site files: {type(exc).__name__}")
        return

    for filename, source in pages.items():
        paragraphs = re.findall(r"<p\b[^>]*>.*?</p>", source, re.IGNORECASE | re.DOTALL)
        disclosure_blocks = [
            block
            for block in paragraphs
            if matches(block, r"class=[\"'][^\"']*\baudience-line\b[^\"']*[\"']")
            and matches(block, r"href=[\"'](?:\./)?terms\.html[\"'][^>]*>\s*terms\s*</a>")
            and "13+" in visible_text(block)
            and "18+" in visible_text(block)
        ]
        check(len(disclosure_blocks) == 1, f"{filename} must use the shared audience-line treatment for its age-disclosure Terms link")
        for block in disclosure_blocks:
            opening_tag = block.split(">", 1)[0]
            check("boundary" not in opening_tag, f"{filename} age-disclosure Terms link must not sit on the light boundary background")

    flat_blocks = re.findall(r"([^{}]+)\{([^{}]*)\}", css, re.DOTALL)
    root_block = next((body for selectors, body in flat_blocks if selectors.strip() == ":root"), "")
    light_match = re.search(r"--forest\s*:\s*(#[0-9a-fA-F]{3,6})", root_block)
    link_match = None
    dark_matches: list[re.Match[str]] = []
    for selectors, declarations in flat_blocks:
        selector_set = {selector.strip() for selector in selectors.split(",")}
        if ".download-card a" in selector_set:
            candidate = re.search(r"\bcolor\s*:\s*(#[0-9a-fA-F]{3,6})", declarations)
            if candidate:
                link_match = candidate
        if ".download-card" in selector_set:
            candidate = re.search(r"\bbackground\s*:\s*(#[0-9a-fA-F]{3,6})", declarations)
            if candidate:
                dark_matches.append(candidate)

    check(light_match is not None, "styles.css must retain the light download-card background token")
    check(link_match is not None, "styles.css must retain an explicit download-card link color")
    check(bool(dark_matches), "styles.css must retain an explicit dark-mode download-card background")
    if light_match and link_match and dark_matches:
        foreground = parse_hex_color(link_match.group(1))
        light_background = parse_hex_color(light_match.group(1))
        dark_background = parse_hex_color(dark_matches[-1].group(1))
        check(foreground is not None and light_background is not None and dark_background is not None, "Policy-link source colors must remain parseable hex values")
        if foreground and light_background and dark_background:
            check(contrast_ratio(foreground, light_background) >= 4.5, "Declared light-mode Terms-link colors must retain at least 4.5:1 contrast")
            check(contrast_ratio(foreground, dark_background) >= 4.5, "Declared dark-mode Terms-link colors must retain at least 4.5:1 contrast")
    check(
        matches(css, r":focus-visible\s*\{[^}]*outline\s*:\s*(?!none|0)[^;}]+;?[^}]*outline-offset"),
        "Keyboard focus must retain a visible outline and offset",
    )
    check(
        matches(css, r"a:hover\s*\{[^}]*text-decoration-thickness\s*:\s*\.15em"),
        "Link hover state must remain visually distinguishable",
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
    validate_terms_architecture(parsed)
    validate_policy_decisions()
    validate_policy_link_contrast_source()
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
