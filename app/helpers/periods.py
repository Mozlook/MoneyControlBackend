from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class PeriodRangeUTC:
    period_start_utc: datetime
    period_end_utc: datetime


def resolve_period_range_utc(
    *,
    billing_day: int,
    timezone_name: str,
    current_period: bool = True,
    from_date: date | None = None,
    to_date: date | None = None,
    now_utc: datetime | None = None,
) -> PeriodRangeUTC:
    """
    Zwraca [period_start_utc, period_end_utc) (end EXCLUSIVE).
    - current_period=True: okres wg billing_day i timezone usera
    - current_period=False: zakres ręczny (from_date/to_date) w timezone usera
    """
    local_tz = ZoneInfo(timezone_name)
    now_utc = now_utc or datetime.now(timezone.utc)

    if current_period:
        now_local = now_utc.astimezone(local_tz)
        year = now_local.year
        month = now_local.month

        if now_local.day >= billing_day:
            period_start_local = datetime(year, month, billing_day, tzinfo=local_tz)
            if month == 12:
                period_end_local = datetime(year + 1, 1, billing_day, tzinfo=local_tz)
            else:
                period_end_local = datetime(
                    year, month + 1, billing_day, tzinfo=local_tz
                )
        else:
            period_end_local = datetime(year, month, billing_day, tzinfo=local_tz)
            if month == 1:
                period_start_local = datetime(
                    year - 1, 12, billing_day, tzinfo=local_tz
                )
            else:
                period_start_local = datetime(
                    year, month - 1, billing_day, tzinfo=local_tz
                )

        return PeriodRangeUTC(
            period_start_utc=period_start_local.astimezone(timezone.utc),
            period_end_utc=period_end_local.astimezone(timezone.utc),
        )

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

    return PeriodRangeUTC(
        period_start_utc=period_start_utc, period_end_utc=period_end_utc
    )
