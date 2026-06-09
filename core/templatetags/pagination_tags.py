"""Template tags for the pagination controls.

Currently exposes a single filter, :func:`page_range_window`, that turns the
``(current, total)`` pair of page numbers into a compact list of integer page
numbers and ``"..."`` sentinels suitable for rendering a smart-ellipsis
pagination bar in a Django template.

The output always includes page 1, the current page, the page immediately
before and after the current, and the last page. ``"..."`` is inserted in
any gap where consecutive numbers are not adjacent.
"""
from django import template

register = template.Library()

# Number of neighbours to render on each side of the current page.
WINDOW = 1


@register.filter
def page_range_window(current, total):
    """Return a list of ints and ``"..."`` sentinels describing the pagination.

    Examples
    --------
    >>> page_range_window(1, 1)
    [1]
    >>> page_range_window(5, 7)
    [1, 2, 3, 4, 5, 6, 7]
    >>> page_range_window(10, 20)
    [1, '...', 9, 10, 11, '...', 20]
    """
    current = int(current)
    total = int(total)

    if total <= 0:
        return []
    if total == 1:
        return [1]

    # When the total fits on screen, return every page without ellipsis.
    if total <= 7:
        return list(range(1, total + 1))

    # Compute the "window" around the current page (current ± WINDOW).
    first = max(2, current - WINDOW)
    last = min(total - 1, current + WINDOW)

    pages = [1]
    if first > 2:
        pages.append("...")
    pages.extend(range(first, last + 1))
    if last < total - 1:
        pages.append("...")
    pages.append(total)
    return pages
