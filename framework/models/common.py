from __future__ import annotations

from typing import Generic, Literal, TypeVar

from framework.models.base import ApiModel

T = TypeVar("T")


class Pagination(ApiModel):
    total: int
    page: int
    limit: int
    total_pages: int


class DataEnvelope(ApiModel, Generic[T]):
    """``{"success": true, "data": {...}, "message": "..."}``"""

    success: Literal[True]
    data: T
    message: str | None = None


class ListEnvelope(ApiModel, Generic[T]):
    """``{"success": true, "data": [...], "pagination": {...}}``"""

    success: Literal[True]
    data: list[T]
    pagination: Pagination


class MessageEnvelope(ApiModel):
    """``{"success": true, "message": "..."}`` (e.g. cancel booking)."""

    success: Literal[True]
    message: str


class FieldError(ApiModel):
    field: str
    message: str


class ErrorResponse(ApiModel):
    """``{"success": false, "error": "...", "details": [{"field": ..., "message": ...}]}``"""

    success: Literal[False]
    error: str
    details: list[FieldError] | None = None

    def messages_for(self, field: str) -> list[str]:
        return [d.message for d in self.details or [] if d.field == field]
