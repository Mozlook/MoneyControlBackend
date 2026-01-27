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


def last_n_period_ranges_utc(
    *,
    billing_day: int,
    timezone_name: str,
    periods: int,
    now_utc: datetime | None = None,
) -> list[PeriodRangeUTC]:
    cursor = now_utc or datetime.now(timezone.utc)
    out: list[PeriodRangeUTC] = []

    for _ in range(periods):
        pr = resolve_period_range_utc(
            billing_day=billing_day,
            timezone_name=timezone_name,
            current_period=True,
            now_utc=cursor,
        )
        out.append(pr)

        cursor = pr.period_start_utc - timedelta(microseconds=1)

    return out
