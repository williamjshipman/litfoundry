"""JSON serialization and validation helpers."""

import json
import uuid
from datetime import datetime
from typing import Any

import dateutil.parser
import dateutil.tz


class LitFoundryJSONEncoder(json.JSONEncoder):
    """JSON encoder for LitFoundry objects."""

    def default(self, o: Any) -> Any:
        """Encode UUIDs and datetimes."""
        if isinstance(o, uuid.UUID):
            return str(o)
        if isinstance(o, datetime):
            # Always return UTC ISO-8601 with Z suffix
            if o.tzinfo is None:
                # Assume UTC if no tzinfo
                o = o.replace(tzinfo=dateutil.tz.UTC)
            return o.isoformat().replace("+00:00", "Z")
        return super().default(o)


def serialize_uuid(u: uuid.UUID) -> str:
    """Serialize a UUID to string."""
    return str(u)


def serialize_datetime(dt: datetime) -> str:
    """Serialize a datetime to UTC ISO-8601 with Z suffix."""
    if dt.tzinfo is None:
        # Assume UTC if no tzinfo
        dt = dt.replace(tzinfo=dateutil.tz.UTC)
    iso = dt.isoformat()
    # Convert +00:00 to Z
    return iso.replace("+00:00", "Z")


def parse_datetime(dt_str: str) -> datetime:
    """Parse an ISO-8601 datetime string (may have Z suffix)."""
    return dateutil.parser.isoparse(dt_str)
