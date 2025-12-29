from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..helpers.wallets import ensure_wallet_member
from ..models import Category, Product, Transaction, User, ProductImportance
from ..schemas.aggregation import (
    CategoriesProductsSummaryRead,
    CategoriesWithProductsSummaryRead,
    ProductWithSumRead,
    ImportanceSummaryRead,
)
from ..schemas.category import CategoryRead
from ..schemas.transaction import ProductInTransactionRead

router = APIRouter(
    prefix="/wallets/{wallet_id}/summary",
    tags=["summary"],
)


@router.get(
    "/categories-products",
    response_model=CategoriesProductsSummaryRead,
    status_code=200,
)
def summary_categories_products(
    wallet_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    current_period: bool = True,
    from_date: date | None = None,
    to_date: date | None = None,
    include_empty: bool = False,
):
    membership = ensure_wallet_member(db, wallet_id, current_user)
    currency = membership.wallet.currency

    settings = current_user.user_settings
    local_tz = ZoneInfo(settings.timezone)
    now_utc = datetime.now(timezone.utc)

    if current_period:
        now_local = now_utc.astimezone(local_tz)
        year = now_local.year
        month = now_local.month
        billing_day = settings.billing_day

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

        period_start_utc = period_start_local.astimezone(timezone.utc)
        period_end_utc = period_end_local.astimezone(timezone.utc)
    else:
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

    base_q = db.query(Transaction).filter(
        Transaction.wallet_id == wallet_id,
        Transaction.deleted_at.is_(None),
        Transaction.type == "expense",
        Transaction.occurred_at >= period_start_utc,
        Transaction.occurred_at < period_end_utc,
    )

    agg_rows = (
        base_q.with_entities(
            Transaction.category_id,
            Transaction.product_id,
            func.coalesce(func.sum(Transaction.amount_base), 0).label("sum_amount"),
        )
        .group_by(Transaction.category_id, Transaction.product_id)
        .all()
    )

    category_sum: defaultdict[UUID, Decimal] = defaultdict(lambda: Decimal("0"))
    no_product_sum: defaultdict[UUID, Decimal] = defaultdict(lambda: Decimal("0"))
    product_sum: dict[tuple[UUID, UUID], Decimal] = {}

    used_category_ids: set[UUID] = set()
    used_product_ids: set[UUID] = set()

    total = Decimal("0")

    for cat_id, prod_id, sum_amount in agg_rows:
        used_category_ids.add(cat_id)

        category_sum[cat_id] += sum_amount
        total += sum_amount

        if prod_id is None:
            no_product_sum[cat_id] += sum_amount
        else:
            used_product_ids.add(prod_id)
            product_sum[(cat_id, prod_id)] = sum_amount

    if include_empty:
        cat_q = db.query(Category).filter(Category.wallet_id == wallet_id)
        if used_category_ids:
            cat_q = cat_q.filter(
                or_(Category.deleted_at.is_(None), Category.id.in_(used_category_ids))
            )
        else:
            cat_q = cat_q.filter(Category.deleted_at.is_(None))
        categories = cat_q.order_by(Category.created_at).all()

        prod_q = db.query(Product).filter(Product.wallet_id == wallet_id)
        if used_product_ids:
            prod_q = prod_q.filter(
                or_(Product.deleted_at.is_(None), Product.id.in_(used_product_ids))
            )
        else:
            prod_q = prod_q.filter(Product.deleted_at.is_(None))
        products = prod_q.order_by(Product.created_at).all()
    else:
        if not used_category_ids:
            return CategoriesProductsSummaryRead(
                currency=currency,
                period_start=period_start_utc,
                period_end=period_end_utc,
                total=Decimal("0"),
                categories=[],
            )

        categories = (
            db.query(Category)
            .filter(Category.wallet_id == wallet_id, Category.id.in_(used_category_ids))
            .order_by(Category.created_at)
            .all()
        )

        if used_product_ids:
            products = (
                db.query(Product)
                .filter(
                    Product.wallet_id == wallet_id, Product.id.in_(used_product_ids)
                )
                .order_by(Product.created_at)
                .all()
            )
        else:
            products = []

    products_by_category: defaultdict[UUID, list[Product]] = defaultdict(list)
    for p in products:
        products_by_category[p.category_id].append(p)

    category_items: list[CategoriesWithProductsSummaryRead] = []

    for c in categories:
        prod_items: list[ProductWithSumRead] = []

        for p in sorted(products_by_category.get(c.id, []), key=lambda x: x.created_at):
            ps = product_sum.get((c.id, p.id), Decimal("0"))

            if not include_empty and (c.id, p.id) not in product_sum:
                continue

            prod_items.append(
                ProductWithSumRead(
                    product=ProductInTransactionRead(
                        id=p.id,
                        name=p.name,
                        importance=p.importance,
                    ),
                    product_sum=ps,
                )
            )

        category_items.append(
            CategoriesWithProductsSummaryRead(
                category=CategoryRead(
                    id=c.id,
                    name=c.name,
                    color=c.color,
                    icon=c.icon,
                    created_at=c.created_at,
                ),
                category_sum=category_sum.get(c.id, Decimal("0")),
                no_product_sum=no_product_sum.get(c.id, Decimal("0")),
                products=prod_items,
            )
        )

    return CategoriesProductsSummaryRead(
        currency=currency,
        period_start=period_start_utc,
        period_end=period_end_utc,
        total=total,
        categories=category_items,
    )


@router.get(
    "/by-importance",
    response_model=ImportanceSummaryRead,
    status_code=200,
)
def summary_by_importance(
    wallet_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    current_period: bool = True,
    from_date: date | None = None,
    to_date: date | None = None,
):
    membership = ensure_wallet_member(db, wallet_id, current_user)
    currency = membership.wallet.currency

    settings = current_user.user_settings
    local_tz = ZoneInfo(settings.timezone)
    now_utc = datetime.now(timezone.utc)

    if current_period:
        now_local = now_utc.astimezone(local_tz)
        year = now_local.year
        month = now_local.month
        billing_day = settings.billing_day

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

        period_start_utc = period_start_local.astimezone(timezone.utc)
        period_end_utc = period_end_local.astimezone(timezone.utc)
    else:
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

    query = db.query(Transaction).filter(
        Transaction.wallet_id == wallet_id,
        Transaction.deleted_at.is_(None),
        Transaction.type == "expense",
        Transaction.occurred_at >= period_start_utc,
        Transaction.occurred_at < period_end_utc,
    )

    rows = (
        query.outerjoin(Product, Transaction.product_id == Product.id)
        .with_entities(
            Product.importance,
            func.coalesce(func.sum(Transaction.amount_base), 0).label("sum_amount"),
        )
        .group_by(Product.importance)
        .all()
    )

    necessary = Decimal("0")
    important = Decimal("0")
    unnecessary = Decimal("0")
    unassigned = Decimal("0")

    for importance, sum_amount in rows:
        match importance:
            case None:
                unassigned += sum_amount
            case ProductImportance.IMPORTANT:
                important += sum_amount

            case ProductImportance.NECESSARY:
                necessary += sum_amount

            case ProductImportance.UNNECESSARY:
                unnecessary += sum_amount

    total = necessary + important + unnecessary + unassigned

    return ImportanceSummaryRead(
        currency=currency,
        period_start=period_start_utc,
        period_end=period_end_utc,
        total=total,
        necessary=necessary,
        important=important,
        unnecessary=unnecessary,
        unassigned=unassigned,
    )
