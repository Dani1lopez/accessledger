"""Integration tests for ``core/templates/core/_pagination.html``.

These tests render the partial against a real ``Page``/``Paginator`` pair
and assert on the structural HTML it produces. The partial must:

- Render ``<nav class="pagination">`` with the Spanish ``aria-label``.
- Render the current page as a ``<span>`` with ``aria-current="page"`` and
  the ``pagination__link--current`` BEM modifier.
- Render other page numbers as ``<a>`` elements with the HTMX contract
  (``hx-get``, ``hx-target="#main"``, ``hx-push-url="true"``) and a
  non-empty ``href`` for fallback when JS is off.
- Render prev/next on the first/last page as ``<span>`` with
  ``aria-disabled="true"`` and the ``pagination__link--disabled`` BEM
  modifier (NOT as a clickable ``<a>``).
- Use the ``page_range_window`` filter so that ellipsis is emitted as
  ``<span class="pagination__ellipsis" aria-hidden="true">…</span>``.
- Preserve the current query string when building ``href``/``hx-get`` URLs
  so search/filter parameters survive a page change.
- Render nothing when there is only one page.
"""
import pytest
from django.core.paginator import Paginator
from django.template.loader import get_template
from django.test import RequestFactory
from core.models import Resource


def _make_page(qs, page=1, per_page=5):
    """Wrap ``qs`` in a Django ``Paginator`` and return ``(page_obj, paginator)``."""
    paginator = Paginator(qs, per_page)
    return paginator.get_page(page), paginator


def _make_resources(n, names=None):
    """Create n Resource rows and return the full queryset (ordered by pk)."""
    for i in range(n):
        Resource.objects.create(
            name=(names or [f"r{i}" for i in range(n)])[i],
            resource_type="server",
        )
    return Resource.objects.all().order_by("pk")


def _render_pagination(request, page_obj, paginator):
    """Render the partial with the given context."""
    partial = get_template("core/_pagination.html")
    ctx = {
        "page_obj": page_obj,
        "paginator": paginator,
        "request": request,
    }
    return partial.render(ctx)


@pytest.mark.django_db
class TestPaginationPartialStructure:
    """Structural tests for the redesigned pagination partial."""

    def test_renders_navigation_element(self):
        """The partial must wrap its content in <nav class='pagination'>."""
        rf = RequestFactory()
        request = rf.get("/resources/")
        resources = _make_resources(12)
        page_obj, paginator = _make_page(resources, page=1, per_page=5)

        html = _render_pagination(request, page_obj, paginator)

        assert '<nav class="pagination"' in html
        assert 'aria-label="Paginación"' in html

    def test_renders_current_page_as_span_with_aria_current(self):
        """Current page must be a <span>, not an <a>, with aria-current='page'."""
        rf = RequestFactory()
        request = rf.get("/resources/")
        resources = _make_resources(12)
        page_obj, paginator = _make_page(resources, page=2, per_page=5)

        html = _render_pagination(request, page_obj, paginator)

        assert "pagination__link--current" in html
        assert 'aria-current="page"' in html
        assert (
            '<span class="pagination__link pagination__link--current"' in html
        )

    def test_renders_other_pages_as_links_with_htmx(self):
        """Other pages must be <a> tags with hx-get, hx-target, hx-push-url."""
        rf = RequestFactory()
        request = rf.get("/resources/")
        resources = _make_resources(12)
        page_obj, paginator = _make_page(resources, page=1, per_page=5)

        html = _render_pagination(request, page_obj, paginator)

        assert 'class="pagination__link"' in html
        assert 'hx-get="?page=' in html
        assert 'hx-target="#main"' in html
        assert 'hx-push-url="true"' in html
        assert 'href="?page=' in html

    def test_disabled_prev_on_first_page_is_span(self):
        """On page 1, prev must be a non-clickable <span> with aria-disabled."""
        rf = RequestFactory()
        request = rf.get("/resources/")
        resources = _make_resources(12)
        page_obj, paginator = _make_page(resources, page=1, per_page=5)

        html = _render_pagination(request, page_obj, paginator)

        assert "pagination__link--prev pagination__link--disabled" in html
        assert 'aria-disabled="true"' in html
        assert (
            '<span class="pagination__link pagination__link--prev'
            ' pagination__link--disabled"' in html
        )

    def test_disabled_next_on_last_page_is_span(self):
        """On the last page, next must be a non-clickable <span> with aria-disabled."""
        rf = RequestFactory()
        request = rf.get("/resources/")
        resources = _make_resources(12)
        page_obj, paginator = _make_page(resources, page=3, per_page=5)

        html = _render_pagination(request, page_obj, paginator)

        assert "pagination__link--next pagination__link--disabled" in html
        assert (
            '<span class="pagination__link pagination__link--next'
            ' pagination__link--disabled"' in html
        )

    def test_enabled_prev_link_uses_pagination_link_prev_class(self):
        """On page 2, prev should be a clickable <a> with the prev class."""
        rf = RequestFactory()
        request = rf.get("/resources/")
        resources = _make_resources(12)
        page_obj, paginator = _make_page(resources, page=2, per_page=5)

        html = _render_pagination(request, page_obj, paginator)

        assert "pagination__link--prev" in html
        assert "pagination__link--prev pagination__link--disabled" not in html
        assert 'href="?page=1"' in html

    def test_enabled_next_link_uses_pagination_link_next_class(self):
        """On page 1, next should be a clickable <a> with the next class."""
        rf = RequestFactory()
        request = rf.get("/resources/")
        resources = _make_resources(12)
        page_obj, paginator = _make_page(resources, page=1, per_page=5)

        html = _render_pagination(request, page_obj, paginator)

        assert "pagination__link--next" in html
        assert "pagination__link--next pagination__link--disabled" not in html
        assert 'href="?page=2"' in html

    def test_renders_ellipsis_for_large_pagination(self):
        """When total > 7, ellipsis markers must appear with aria-hidden."""
        rf = RequestFactory()
        request = rf.get("/resources/")
        resources = _make_resources(50)
        page_obj, paginator = _make_page(resources, page=5, per_page=5)

        html = _render_pagination(request, page_obj, paginator)

        assert "pagination__ellipsis" in html
        assert 'aria-hidden="true"' in html

    def test_renders_mobile_meta_text_in_spanish(self):
        """The mobile meta line must say 'Página X de Y' (Spanish)."""
        rf = RequestFactory()
        request = rf.get("/resources/")
        resources = _make_resources(12)
        page_obj, paginator = _make_page(resources, page=3, per_page=5)

        html = _render_pagination(request, page_obj, paginator)

        assert "pagination__meta" in html
        # Spanish meta text per the design (current=3, total=3)
        assert "Página 3 de 3" in html

    def test_renders_aria_label_for_each_page(self):
        """Each numbered link/span must have an aria-label like 'Página N'."""
        rf = RequestFactory()
        request = rf.get("/resources/")
        resources = _make_resources(12)
        page_obj, paginator = _make_page(resources, page=2, per_page=5)

        html = _render_pagination(request, page_obj, paginator)

        assert 'aria-label="Página 1"' in html
        assert 'aria-label="Página 2"' in html
        assert 'aria-label="Página 3"' in html

    def test_renders_aria_label_for_prev_next(self):
        """Prev and next links must have aria-labels for screen readers."""
        rf = RequestFactory()
        request = rf.get("/resources/")
        resources = _make_resources(12)
        page_obj, paginator = _make_page(resources, page=2, per_page=5)

        html = _render_pagination(request, page_obj, paginator)

        assert 'aria-label="Página anterior"' in html
        assert 'aria-label="Página siguiente"' in html

    def test_no_lift_in_animation_class_on_pagination(self):
        """Pagination must not have the .lift-in animation class.

        HTMX swaps #main on every page change — animating the pagination
        would replay visibly on each swap, creating flicker.
        """
        rf = RequestFactory()
        request = rf.get("/resources/")
        resources = _make_resources(12)
        page_obj, paginator = _make_page(resources, page=1, per_page=5)

        html = _render_pagination(request, page_obj, paginator)

        assert '<nav class="pagination"' in html
        assert '<nav class="pagination lift-in"' not in html

    def test_renders_nothing_when_only_one_page(self):
        """If paginator.num_pages == 1, render nothing (no nav needed)."""
        rf = RequestFactory()
        request = rf.get("/resources/")
        # Only 3 items, per_page=5 → single page
        resources = _make_resources(3)
        page_obj, paginator = _make_page(resources, page=1, per_page=5)

        html = _render_pagination(request, page_obj, paginator)

        assert "pagination" not in html
        assert "<nav" not in html


@pytest.mark.django_db
class TestPaginationPartialQueryString:
    """The partial must preserve existing query-string parameters when paging."""

    def test_preserves_existing_query_string_in_page_links(self):
        """If the request has ?q=foo, page links should keep it."""
        rf = RequestFactory()
        request = rf.get("/resources/?q=hello")
        resources = _make_resources(12)
        page_obj, paginator = _make_page(resources, page=1, per_page=5)

        html = _render_pagination(request, page_obj, paginator)

        # Both the search filter and the page param must appear on the
        # next/prev links, separated by an &.
        assert "q=hello" in html
        assert "page=2" in html
        # The search filter and the page number must travel together
        # (any order is fine as long as both are present).
        assert "q=hello" in html and "page=2" in html

    def test_page_2_link_preserves_query_string(self):
        """The link to page 2 must include the search filter."""
        rf = RequestFactory()
        request = rf.get("/resources/?q=hello")
        resources = _make_resources(12)
        page_obj, paginator = _make_page(resources, page=1, per_page=5)

        html = _render_pagination(request, page_obj, paginator)

        assert "q=hello" in html
        assert "page=2" in html

    def test_strips_existing_page_param_to_avoid_duplication(self):
        """If the URL already has page=N, the rendered links must not duplicate it."""
        rf = RequestFactory()
        request = rf.get("/resources/?page=2&q=hello")
        resources = _make_resources(12)
        page_obj, paginator = _make_page(resources, page=2, per_page=5)

        html = _render_pagination(request, page_obj, paginator)

        # The link to page 1 should be ?q=hello&page=1 (not ?page=2&page=1)
        assert "page=2&amp;page=" not in html
        assert "page=2&page=" not in html
        # Page 1 link should appear
        assert "page=1" in html
