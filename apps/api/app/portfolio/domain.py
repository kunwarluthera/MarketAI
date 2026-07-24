from decimal import Decimal


def weighted_average(
    old_quantity: Decimal, old_price: Decimal, added_quantity: Decimal, added_price: Decimal
) -> Decimal:
    total = old_quantity + added_quantity
    if total <= 0:
        raise ValueError("INVALID_POSITION_QUANTITY")
    return ((old_quantity * old_price + added_quantity * added_price) / total).quantize(
        Decimal("0.0001")
    )


def realised_pnl(
    quantity: Decimal,
    entry: Decimal,
    exit_price: Decimal,
    allocated_entry_charges: Decimal,
    exit_charges: Decimal,
) -> Decimal:
    return ((exit_price - entry) * quantity - allocated_entry_charges - exit_charges).quantize(
        Decimal("0.01")
    )
