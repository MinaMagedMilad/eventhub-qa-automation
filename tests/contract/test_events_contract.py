"""Event endpoints vs. the published OpenAPI contract."""

from __future__ import annotations

import pytest

from framework.constants import NONEXISTENT_ID, EventCategory
from framework.defects import known_defect


@pytest.mark.smoke
def test_create_event_response_matches_contract(api, contract, event_factory, track_event):
    response = api.events.create(event_factory.build()).expect_status(201)
    track_event(response.json()["data"]["id"])

    contract.assert_conforms(response, "POST", "/events")


def test_list_events_response_matches_contract(api, contract, event):
    contract.assert_conforms(api.events.list(search=event.title).expect_status(200), "GET", "/events")


def test_get_event_response_matches_contract(api, contract, event):
    contract.assert_conforms(api.events.get(event.id).expect_status(200), "GET", "/events/{id}")


def test_update_event_response_matches_contract(api, contract, event, event_factory):
    response = api.events.update(event.id, event_factory.build()).expect_status(200)

    contract.assert_conforms(response, "PUT", "/events/{id}")


def test_delete_event_response_matches_contract(api, contract, event):
    contract.assert_conforms(api.events.delete(event.id).expect_status(200), "DELETE", "/events/{id}")


@pytest.mark.negative
def test_unknown_event_response_matches_contract(api, contract):
    contract.assert_conforms(api.events.get(NONEXISTENT_ID).expect_status(404), "GET", "/events/{id}")


@pytest.mark.negative
def test_invalid_event_response_matches_contract(api, contract, event_payload, track_event):
    event_payload.pop("title")

    response = api.events.create(event_payload)
    if response.status == 201:
        track_event(response.json()["data"]["id"])

    contract.assert_conforms(response.expect_status(400), "POST", "/events")


@known_defect("EH-03")
def test_event_price_is_a_json_number(api, contract, event):
    response = api.events.get(event.id).require_status(200)

    contract.assert_conforms(response, "GET", "/events/{id}", tolerate=())


def test_documented_categories_match_the_supported_categories(contract):
    """framework/constants.py EventCategory is the suite's copy of the documented category list."""
    parameters = contract.operation("GET", "/events")["parameters"]
    documented = next(p["schema"]["enum"] for p in parameters if p["name"] == "category")

    assert sorted(documented) == sorted(c.value for c in EventCategory)
