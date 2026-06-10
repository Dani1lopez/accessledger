"""Unit tests for the ``page_range_window`` template filter.

This filter implements smart ellipsis logic for pagination: it returns a list
of page numbers and the string ``"..."`` so the template can render a compact
pagination control without long lists of page numbers.

The expected output always contains the current page, the first page, the
last page, the page ± 1 around the current, and ``"..."`` sentinels in any
gaps where adjacent pages are not consecutive.

Examples:
    page_range_window(1, 1)  == [1]
    page_range_window(1, 7)  == [1, 2, "..."]   # ellipsis only on the right
    page_range_window(5, 20) == [1, "...", 4, 5, 6, "...", 20]
"""
import pytest


class TestPageRangeWindow:
    """Behavior tests for the page_range_window filter (template filter)."""

    # ─── Trivial cases (≤ 2 pages): no ellipsis needed ───

    def test_single_page_returns_only_page_1(self):
        from core.templatetags.pagination_tags import page_range_window

        assert page_range_window(1, 1) == [1]

    def test_two_pages_returns_both(self):
        from core.templatetags.pagination_tags import page_range_window

        assert page_range_window(1, 2) == [1, 2]

    def test_two_pages_at_end(self):
        from core.templatetags.pagination_tags import page_range_window

        assert page_range_window(2, 2) == [1, 2]

    # ─── Total ≤ 7: show all pages, no ellipsis ───

    def test_three_pages_no_ellipsis(self):
        from core.templatetags.pagination_tags import page_range_window

        assert page_range_window(2, 3) == [1, 2, 3]

    def test_seven_pages_no_ellipsis(self):
        from core.templatetags.pagination_tags import page_range_window

        assert page_range_window(4, 7) == [1, 2, 3, 4, 5, 6, 7]

    # ─── Total > 7: ellipsis appears around gaps ───

    def test_current_at_start_ellipsis_only_on_right(self):
        """current=2, total=20: show 1, 2, 3, then ellipsis, then last page."""
        from core.templatetags.pagination_tags import page_range_window

        result = page_range_window(2, 20)
        # First page, current, current+1, ellipsis, last
        assert result == [1, 2, 3, "...", 20]

    def test_current_at_end_ellipsis_only_on_left(self):
        """current=19, total=20: show first, ellipsis, current-1, current, last."""
        from core.templatetags.pagination_tags import page_range_window

        result = page_range_window(19, 20)
        assert result == [1, "...", 18, 19, 20]

    def test_current_in_middle_ellipsis_both_sides(self):
        """current=10, total=20: first, ellipsis, current-1, current, current+1, ellipsis, last."""
        from core.templatetags.pagination_tags import page_range_window

        result = page_range_window(10, 20)
        assert result == [1, "...", 9, 10, 11, "...", 20]

    def test_current_in_middle_with_total_8(self):
        """Edge: total=8 with current=4 → [1, "...", 3, 4, 5, "...", 8]."""
        from core.templatetags.pagination_tags import page_range_window

        result = page_range_window(4, 8)
        # current ± 1 = 3, 4, 5; first 1; last 8; gaps on both sides
        assert result == [1, "...", 3, 4, 5, "...", 8]

    def test_current_in_middle_with_total_9(self):
        """Edge: total=9, current=5 → [1, "...", 4, 5, 6, "...", 9]."""
        from core.templatetags.pagination_tags import page_range_window

        result = page_range_window(5, 9)
        # current ± 1 = 4, 5, 6; gap left of 4, gap right of 6
        assert result == [1, "...", 4, 5, 6, "...", 9]

    # ─── Edge: gap collapses to no ellipsis (consecutive pages) ───

    def test_no_ellipsis_when_first_and_current_neighbor_are_consecutive(self):
        """If first page (1) is consecutive to current-1, no left ellipsis."""
        from core.templatetags.pagination_tags import page_range_window

        result = page_range_window(3, 20)
        # current ± 1 = 2, 3, 4; 1 is consecutive to 2 → no left gap
        # last=20; gap right between 4 and 20
        assert result == [1, 2, 3, 4, "...", 20]

    def test_no_ellipsis_when_last_and_current_neighbor_are_consecutive(self):
        """If last page is consecutive to current+1, no right ellipsis."""
        from core.templatetags.pagination_tags import page_range_window

        result = page_range_window(18, 20)
        # current ± 1 = 17, 18, 19; 20 is consecutive to 19 → no right gap
        # first=1; gap left between 1 and 17
        assert result == [1, "...", 17, 18, 19, 20]

    # ─── Output type contract ───

    def test_returns_list(self):
        from core.templatetags.pagination_tags import page_range_window

        result = page_range_window(1, 1)
        assert isinstance(result, list)

    def test_first_element_is_always_page_1(self):
        from core.templatetags.pagination_tags import page_range_window

        assert page_range_window(5, 20)[0] == 1
        assert page_range_window(1, 1)[0] == 1
        assert page_range_window(10, 10)[0] == 1

    def test_last_numeric_element_equals_total_when_total_greater_than_1(self):
        from core.templatetags.pagination_tags import page_range_window

        result = page_range_window(5, 20)
        # The last non-ellipsis item must be 20
        numeric_items = [x for x in result if isinstance(x, int)]
        assert numeric_items[-1] == 20

    def test_ellipsis_marker_is_string_dots(self):
        from core.templatetags.pagination_tags import page_range_window

        result = page_range_window(10, 20)
        ellipsis_items = [x for x in result if not isinstance(x, int)]
        # For current=10, total=20 there are gaps on both sides, so two
        # ellipsis sentinels are emitted.
        assert ellipsis_items == ["...", "..."]

    def test_no_duplicate_ellipsis_sentinels(self):
        """The filter must never emit two consecutive '...' sentinels."""
        from core.templatetags.pagination_tags import page_range_window

        result = page_range_window(10, 20)
        for i in range(len(result) - 1):
            assert not (result[i] == "..." and result[i + 1] == "..."), (
                f"Duplicate ellipsis at index {i}: {result}"
            )
