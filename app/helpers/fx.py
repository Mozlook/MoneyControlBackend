from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException, status

TWOPLACES = Decimal("0.01")

FX_TO_PLN: dict[str, Decimal] = {
    "PLN": Decimal("1"),
    "EUR": Decimal("4.30"),
    "USD": Decimal("3.95"),
}


def q2(x: Decimal) -> Decimal:
    return x.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def normalize_currency(v: str) -> str:
    cur = (v or "").strip().upper()
    if len(cur) != 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="currency must be a 3-letter code",
        )
    return cur


def _get_rate_to_pln(cur: str) -> Decimal:
    if cur not in FX_TO_PLN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported currency: {cur}",
        )
    rate = FX_TO_PLN[cur]
    if rate <= 0:
        raise HTTPException(status_code=500, detail=f"Invalid FX_TO_PLN rate for {cur}")
    return rate


def fx_rate(from_cur: str, to_cur: str) -> Decimal:
    if from_cur == to_cur:
        return Decimal("1")
    return _get_rate_to_pln(from_cur) / _get_rate_to_pln(to_cur)


def compute_amounts(
    *,
    amount: Decimal,
    input_currency: str,
    wallet_currency: str,
) -> tuple[Decimal, str, Decimal | None, str | None, Decimal | None]:
    if input_currency == wallet_currency:
        amount_base = q2(amount)
        return amount_base, wallet_currency, None, None, None

    rate = q2(fx_rate(input_currency, wallet_currency))
    amount_original = q2(amount)
    amount_base = q2(amount_original * rate)
    return amount_base, wallet_currency, amount_original, input_currency, rate
