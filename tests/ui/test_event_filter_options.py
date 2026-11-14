"""The events-page filters offer exactly the categories and cities defined in framework/constants.py.

The constants are the suite's single definition of both lists (the factories build events from them);
the product owns the real lists. These tests fail the day the two drift apart, naming what changed.
"""

from __future__ import annotations

from framework.constants import EVENT_CITIES, EventCategory


def test_city_filter_offers_exactly_the_supported_cities(app):
    events = app.events.open()

    assert sorted(events.filter_values(events.city_filter)) == sorted(EVENT_CITIES)


def test_category_filter_offers_exactly_the_supported_categories(app):
    events = app.events.open()

    assert sorted(events.filter_values(events.category_filter)) == sorted(c.value for c in EventCategory)
