"""Shared JSON-schema fragments reused across multiple tool parameter schemas."""
from __future__ import annotations

FILTER_SCHEMA = {
    "type": "object",
    "properties": {
        "column": {"type": "string"},
        "operator": {
            "type": "string",
            "enum": ["eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in", "contains", "is_null", "not_null"],
        },
        "value": {"description": "Required for all operators except is_null/not_null."},
    },
    "required": ["column", "operator"],
}

METRIC_SCHEMA = {
    "type": "object",
    "properties": {
        "column": {"type": "string", "description": "Required unless aggregation is 'count'."},
        "aggregation": {"type": "string", "enum": ["sum", "mean", "median", "count", "min", "max", "std"]},
        "alias": {"type": "string", "description": "Result column name. Defaults to '<aggregation>_<column>'."},
    },
    "required": ["aggregation"],
}
