from datetime import date, datetime

from flask import jsonify


def error(message: str, status: int = 400):
    return jsonify({"message": message}), status


def normalize_date(value: str) -> date:
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value[:10], fmt).date()
        except ValueError:
            continue
    return date.fromisoformat(value[:10])


def normalize_datetime(value: str) -> datetime:
    value = (value or "").strip()
    if not value:
        return datetime.now()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(value.replace("Z", "")[:26], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now()


def dt_to_json(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")
