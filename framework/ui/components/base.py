"""Building blocks shared by components and pages.

Locator policy (applied everywhere in ``framework.ui``):
  1. ``data-testid`` where the app provides one (most stable, intent-revealing);
  2. otherwise role / label / text - what a user perceives (Playwright's recommended default);
  3. ``id`` / CSS class only when neither exists (noted inline where used).
Locators are lazy, so components can be created up-front and resolved when used.
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page


class Component:
    """A region of a page, scoped to ``root``. Subclasses expose behaviour, not raw selectors."""

    def __init__(self, page: Page, root: Locator) -> None:
        self.page = page
        self.root = root


def value_next_to(container: Locator, label: str) -> Locator:
    """Value cell of a ``<label-span><value-span>`` row, a pattern used across the app's summaries.

    E.g. ``<div><span>Total</span><span>$3,750</span></div>`` -> locator of ``$3,750``.
    """
    return container.get_by_text(label, exact=True).locator("xpath=following-sibling::*[1]")
