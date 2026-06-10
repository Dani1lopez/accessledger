"""Tests for the pagination CSS rules in ``core/static/core/css/app.css``.

CSS is a static asset: there is no runtime hook to introspect a stylesheet
from a Django request. The contract we can assert from Python is that the
stylesheet source file contains the selectors, properties, and design-token
references the design requires.

The visual outcome (pill shape, hover effect, focus ring, disabled state,
no entrance animation, responsive hiding of numeric links) is verified
manually via the visual QA checklist in ``docs/pagination-visual-qa.md``.
"""
import re
from pathlib import Path

import pytest

CSS_PATH = Path("core/static/core/css/app.css")
CSS_TEXT = CSS_PATH.read_text() if CSS_PATH.exists() else ""


def _selectors_for(block: str) -> str:
    """Return the contiguous CSS block for a given selector (best-effort).

    Strips out /* comments */ first so they don't fool the rule matcher.
    Walks braces to handle nested rules inside the block.
    """
    cleaned = re.sub(r"/\*.*?\*/", "", CSS_TEXT, flags=re.DOTALL)
    start = re.search(rf"({re.escape(block)}\s*\{{)", cleaned)
    if not start:
        return ""
    depth = 0
    i = start.start(1)
    while i < len(cleaned):
        ch = cleaned[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return cleaned[start.start(1) : i + 1]
        i += 1
    return ""


def _has_selector(selector: str) -> bool:
    """True if the given selector is defined as a CSS rule somewhere in the file."""
    pattern = rf"(^|\s){re.escape(selector)}\s*\{{"
    return bool(re.search(pattern, CSS_TEXT))


def _has_rule_in_block(block: str, prop: str) -> bool:
    """True if ``prop:`` appears inside the contiguous block of ``block``.

    ``prop`` is matched as a substring of the declaration; it may be a
    full property+value (e.g. ``"display: flex"``) or just a property name
    (e.g. ``"display"``). The match is anchored at a word boundary so that
    ``"flex"`` does not match inside ``"flex-grow"``.
    """
    snippet = _selectors_for(block)
    if not snippet:
        return False
    pattern = rf"(^|[\s;{{}}]){re.escape(prop)}(\s|;|\}}|$)"
    return bool(re.search(pattern, snippet))


def _has_at_rule_under(media: str, selector: str) -> bool:
    """True if ``selector { ... }`` appears inside the @media (max-width: ...) block.

    ``media`` is passed as a regex pattern (e.g. ``r"\\\(max-width:\\s*640px\\\)"``)
    describing only the media-query expression. ``selector`` is a plain CSS
    selector and gets escaped for regex use.

    Uses a brace-balancing walk so nested rules inside the @media are honoured.
    """
    cleaned = re.sub(r"/\*.*?\*/", "", CSS_TEXT, flags=re.DOTALL)
    head_re = re.compile(rf"@media\s+{media}\s*\{{")
    head = head_re.search(cleaned)
    if not head:
        return False
    depth = 0
    i = head.end() - 1  # position of the opening "{"
    while i < len(cleaned):
        ch = cleaned[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                body = cleaned[head.end() : i]
                if re.search(rf"{re.escape(selector)}\s*\{{", body):
                    return True
                return False
        i += 1
    return False


# ─────────────────── Existence guards ───────────────────


class TestPaginationCssExists:
    """The pagination block must be present in app.css."""

    def test_pagination_block_selector_defined(self):
        assert _has_selector(".pagination"), (
            ".pagination block missing from app.css"
        )

    def test_pagination_link_selector_defined(self):
        assert _has_selector(".pagination__link"), (
            ".pagination__link block missing from app.css"
        )

    def test_pagination_link_current_selector_defined(self):
        assert _has_selector(".pagination__link--current"), (
            ".pagination__link--current block missing from app.css"
        )

    def test_pagination_link_disabled_selector_defined(self):
        assert _has_selector(".pagination__link--disabled"), (
            ".pagination__link--disabled block missing from app.css"
        )

    def test_pagination_ellipsis_selector_defined(self):
        assert _has_selector(".pagination__ellipsis"), (
            ".pagination__ellipsis block missing from app.css"
        )

    def test_pagination_meta_selector_defined(self):
        assert _has_selector(".pagination__meta"), (
            ".pagination__meta block missing from app.css"
        )


# ─────────────────── Pill design ───────────────────


class TestPaginationPillDesign:
    """The links must be pill-shaped: border-radius: 999px."""

    def test_pagination_link_is_pill_shaped(self):
        assert _has_rule_in_block(".pagination__link", "border-radius: 999px"), (
            ".pagination__link must use border-radius: 999px for the pill shape"
        )


# ─────────────────── Design tokens ───────────────────


class TestPaginationDesignTokens:
    """The CSS must reference the project's design tokens, not hardcoded colors."""

    def test_pagination_block_uses_design_tokens(self):
        # The block must reference at least one of the established tokens.
        snippet = _selectors_for(".pagination")
        for token in ("--line", "--text", "--muted", "--accent", "--bg", "--fg"):
            if token in snippet:
                return
        pytest.fail(
            f".pagination must reference at least one design token, got: {snippet!r}"
        )

    def test_current_link_uses_accent_token(self):
        """The current-page link must use --accent to match the design system."""
        snippet = _selectors_for(".pagination__link--current")
        assert "var(--accent)" in snippet, (
            f".pagination__link--current must use var(--accent), got: {snippet!r}"
        )


# ─────────────────── Hover / focus / disabled ───────────────────


class TestPaginationInteractions:
    """Hover, focus-visible, and disabled states must be styled."""

    def test_pagination_link_hover_block_exists(self):
        assert _has_selector(".pagination__link:hover")

    def test_pagination_link_focus_visible_block_exists(self):
        assert _has_selector(".pagination__link:focus-visible")

    def test_focus_visible_uses_box_shadow_ring(self):
        snippet = _selectors_for(".pagination__link:focus-visible")
        assert "box-shadow" in snippet, (
            "focus-visible must add a glow via box-shadow"
        )

    def test_disabled_link_blocks_pointer_events(self):
        snippet = _selectors_for(".pagination__link--disabled")
        assert "pointer-events: none" in snippet, (
            "Disabled pagination link must set pointer-events: none"
        )

    def test_disabled_link_reduces_opacity(self):
        snippet = _selectors_for(".pagination__link--disabled")
        assert "opacity" in snippet, (
            "Disabled pagination link must reduce opacity"
        )


# ─────────────────── No entrance animation ───────────────────


class TestPaginationNoEntranceAnimation:
    """The pagination <nav> must NOT animate on every HTMX swap."""

    def test_no_lift_in_on_pagination_block(self):
        # The .pagination block must not include the .lift-in animation.
        snippet = _selectors_for(".pagination")
        assert "lift-in" not in snippet, (
            "Pagination must NOT include the lift-in animation (HTMX swap flicker)"
        )

    def test_no_animation_property_on_pagination_block(self):
        snippet = _selectors_for(".pagination")
        # The block-level <nav class="pagination"> must not animate
        assert not re.search(r"(^|\s)animation\s*:", snippet), (
            "Pagination must not declare an animation property"
        )


# ─────────────────── Responsive (mobile) ───────────────────


class TestPaginationResponsive:
    """Numeric links must hide on small screens; meta line becomes primary."""

    def test_max_width_breakpoint_defined(self):
        # The @media (max-width: 480px) block exists with pagination rules
        # Look for the @media block that hides .pagination__ellipsis
        assert _has_at_rule_under(
            r"\(max-width:\s*480px\)", ".pagination__ellipsis"
        ) or _has_at_rule_under(
            r"\(max-width:\s*640px\)", ".pagination__ellipsis"
        ), (
            "No @media (max-width: ...) rule hides .pagination__ellipsis on mobile"
        )

    def test_ellipsis_hidden_on_mobile(self):
        # Inside the @media block, .pagination__ellipsis must be display:none
        pattern = (
            r"@media\s+\(max-width:\s*\d+px\)\s*\{[^{}]*?"
            r"\.pagination__ellipsis\s*\{[^}]*?display\s*:\s*none"
        )
        assert re.search(pattern, CSS_TEXT, re.DOTALL), (
            "On mobile, .pagination__ellipsis must be display: none"
        )

    def test_meta_line_visible_on_mobile(self):
        """The .pagination__meta element should default to hidden, then show on mobile."""
        snippet = _selectors_for(".pagination__meta")
        # Default state: hidden
        assert re.search(r"display\s*:\s*none", snippet), (
            ".pagination__meta should be display: none by default (mobile-only)"
        )

    def test_meta_line_shown_on_mobile(self):
        pattern = (
            r"@media\s+\(max-width:\s*\d+px\)\s*\{[^{}]*?"
            r"\.pagination__meta\s*\{[^}]*?display\s*:\s*(inline|inline-block|block)"
        )
        assert re.search(pattern, CSS_TEXT, re.DOTALL), (
            "On mobile, .pagination__meta must be visible (display: inline|block|...)"
        )


# ─────────────────── Spacing / layout ───────────────────


class TestPaginationLayout:
    """The pagination bar must be a flex container centered on the page."""

    def test_pagination_block_uses_flex(self):
        assert _has_rule_in_block(".pagination", "display: flex")

    def test_pagination_block_uses_justify_center(self):
        assert _has_rule_in_block(
            ".pagination", "justify-content: center"
        ) or _has_rule_in_block(".pagination", "justify-content:center")
