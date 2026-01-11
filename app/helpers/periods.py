from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def _add_months(dt: datetime, months: int) -> datetime:
    """
    Month arithmetic safe for billing_day <= 28.
    Keeps day/time/tzinfo, changes month/year.
    """
    m = dt.month - 1 + months
    year = dt.year + (m // 12)
    month = (m % 12) + 1
    return dt.replace(year=year, month=month)


def resolve_period_range_utc(
    *,
    billing_day: int,
    timezone_name: str,
    current_period: bool,
    from_date: date | None = None,
    to_date: date | None = None,
    now_utc: datetime | None = None,
) -> tuple[datetime, datetime]:
    """
    Returns (period_start_utc, period_end_utc) for DB filtering:
        occurred_at >= period_start_utc AND occurred_at < period_end_utc

    Behavior matches your current implementation:
    - current_period=True -> billing period based on billing_day + user's timezone
    - current_period=False -> open range:
        start defaults to 1970-01-01 UTC (unless from_date provided)
        end defaults to now_utc (unless to_date provided; end is exclusive)
    """
    if billing_day < 1 or billing_day > 28:
        raise ValueError("billing_day must be between 1 and 28")

    local_tz = ZoneInfo(timezone_name)

    now_utc = now_utc or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    if current_period:
        now_local = now_utc.astimezone(local_tz)

        start_local = datetime(
            now_local.year,
            now_local.month,
            billing_day,
            tzinfo=local_tz,
        )

        if now_local.day < billing_day:
            start_local = _add_months(start_local, -1)

        end_local = _add_months(start_local, 1)

        period_start_utc = start_local.astimezone(timezone.utc)
        period_end_utc = end_local.astimezone(timezone.utc)
        return period_start_utc, period_end_utc

    # current_period == False: open range
    period_start_utc = datetime(1970, 1, 1, tzinfo=timezone.utc)
    period_end_utc = now_utc

    if from_date is not None:
        start_local = datetime.combine(from_date, time.min, tzinfo=local_tz)
        period_start_utc = start_local.astimezone(timezone.utc)

    if to_date is not None:
        end_local_exclusive = datetime.combine(
            to_date, time.min, tzinfo=local_tz
        ) + timedelta(days=1)
        period_end_utc = end_local_exclusive.astimezone(timezone.utc)

    return period_start_utc, period_end_utc
