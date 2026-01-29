from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from sqlmodel import col

from ..helpers.summary import (
    build_category_product_sums,
    expense_transactions_in_period_q,
    resolve_user_period_range,
)
from ..helpers.wallets import ensure_wallet_member
from ..models import Category, Product, ProductImportance, Transaction, User
from ..schemas.aggregation import (
    CategoriesProductsSummaryRead,
    CategoriesWithProductsSummaryRead,
    ImportanceSummaryRead,
    ProductWithSumRead,
)
from ..schemas.category import CategoryRead
from ..schemas.transaction import ProductInTransactionRead

ZERO = Decimal("0")


def summary_categories_products(
    *,
    wallet_id: UUID,
    db: Session,
    current_user: User,
    current_period: bool = True,
    from_date: date | None = None,
    to_date: date | None = None,
    include_empty: bool = False,
) -> CategoriesProductsSummaryRead:
    membership = ensure_wallet_member(db, wallet_id, current_user)
    currency = membership.wallet.currency

    period = resolve_user_period_range(
        user=current_user,
        current_period=current_period,
        from_date=from_date,
        to_date=to_date,
    )
    period_start_utc = period.period_start_utc
    period_end_utc = period.period_end_utc

    base_q = expense_transactions_in_period_q(
        db,
        wallet_id=wallet_id,
        period_start_utc=period_start_utc,
        period_end_utc=period_end_utc,
    )

    agg_rows_raw = (
        base_q.with_entities(
            col(Transaction.category_id),
            col(Transaction.product_id),
            func.coalesce(func.sum(col(Transaction.amount_base)), ZERO).label(
                "sum_amount"
            ),
        )
        .group_by(col(Transaction.category_id), col(Transaction.product_id))
        .all()
    )

    agg_rows = cast(list[tuple[UUID, UUID | None, Decimal]], agg_rows_raw)

    (
        category_sum,
        no_product_sum,
        product_sum,
        used_category_ids,
        used_product_ids,
        total,
    ) = build_category_product_sums(agg_rows)

    used_category_ids_list = list(used_category_ids)
    used_product_ids_list = list(used_product_ids)

    if include_empty:
        cat_q = db.query(Category).filter(col(Category.wallet_id) == wallet_id)
        if used_category_ids_list:
            cat_q = cat_q.filter(
                or_(
                    col(Category.deleted_at).is_(None),
                    col(Category.id).in_(used_category_ids_list),
                )
            )
        else:
            cat_q = cat_q.filter(col(Category.deleted_at).is_(None))

        categories = cat_q.order_by(col(Category.created_at)).all()

        prod_q = db.query(Product).filter(col(Product.wallet_id) == wallet_id)
        if used_product_ids_list:
            prod_q = prod_q.filter(
                or_(
                    col(Product.deleted_at).is_(None),
                    col(Product.id).in_(used_product_ids_list),
                )
            )
        else:
            prod_q = prod_q.filter(col(Product.deleted_at).is_(None))

        products = prod_q.order_by(col(Product.created_at)).all()

    else:
        if not used_category_ids_list:
            return CategoriesProductsSummaryRead(
                currency=currency,
                period_start=period_start_utc,
                period_end=period_end_utc,
                total=ZERO,
                categories=[],
            )

        categories = (
            db.query(Category)
            .filter(
                col(Category.wallet_id) == wallet_id,
                col(Category.id).in_(used_category_ids_list),
            )
            .order_by(col(Category.created_at))
            .all()
        )

        if used_product_ids_list:
            products = (
                db.query(Product)
                .filter(
                    col(Product.wallet_id) == wallet_id,
                    col(Product.id).in_(used_product_ids_list),
                )
                .order_by(col(Product.created_at))
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
            key = (c.id, p.id)
            if not include_empty and key not in product_sum:
                continue

            ps = product_sum.get(key, ZERO)

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
                category=CategoryRead.model_validate(c),
                category_sum=category_sum.get(c.id, ZERO),
                no_product_sum=no_product_sum.get(c.id, ZERO),
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


def summary_by_importance(
    *,
    wallet_id: UUID,
    db: Session,
    current_user: User,
    current_period: bool = True,
    from_date: date | None = None,
    to_date: date | None = None,
) -> ImportanceSummaryRead:
    membership = ensure_wallet_member(db, wallet_id, current_user)
    currency = membership.wallet.currency

    period = resolve_user_period_range(
        user=current_user,
        current_period=current_period,
        from_date=from_date,
        to_date=to_date,
    )
    period_start_utc = period.period_start_utc
    period_end_utc = period.period_end_utc

    base_q = expense_transactions_in_period_q(
        db,
        wallet_id=wallet_id,
        period_start_utc=period_start_utc,
        period_end_utc=period_end_utc,
    )

    rows_raw = (
        base_q.outerjoin(Product, col(Transaction.product_id) == col(Product.id))
        .with_entities(
            col(Product.importance),
            func.coalesce(func.sum(col(Transaction.amount_base)), ZERO).label(
                "sum_amount"
            ),
        )
        .group_by(col(Product.importance))
        .all()
    )

    rows = cast(list[tuple[ProductImportance | None, Decimal]], rows_raw)

    necessary = ZERO
    important = ZERO
    unnecessary = ZERO
    unassigned = ZERO

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
