"""Test data for requests: valid-by-default builders with per-field overrides, and a catalogue of
known-bad values for negative tests (``invalid_data``).

Factories only *build* objects. Where randomness comes from (``framework.utils.random_data``) and how a
run is labelled (``framework.utils.run_context``) are separate concerns, injected by ``fixtures/data.py``.
"""

from framework.factories.booking_factory import BookingFactory
from framework.factories.event_factory import EventFactory
from framework.factories.sources import CustomerDataSource, EventDataSource

__all__ = ["BookingFactory", "CustomerDataSource", "EventDataSource", "EventFactory"]
