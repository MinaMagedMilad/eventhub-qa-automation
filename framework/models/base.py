from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """Base for response models: snake_case in Python, camelCase on the wire.

    ``extra="allow"`` keeps the contract check focused on what the story and docs promise: required
    fields must be present and correctly typed, while additive fields do not break the suite.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="allow",
        frozen=True,
    )
