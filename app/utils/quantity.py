def is_valid_quantity_step(quantity: float) -> bool:
    """数量が0.5刻みかどうかを判定する。"""
    return abs(
        quantity * 2 - round(quantity * 2)
    ) < 1e-9