"""사용자가 수정할 수 있는 숫자 입력 오류의 공통 4xx 계약."""
import math

from fastapi import HTTPException


def number(value, label, *, default=None, integer=False, minimum=0):
    if value is None or value == "":
        value = default
    try:
        if isinstance(value, bool):
            raise ValueError
        parsed = float(value)
        if not math.isfinite(parsed) or parsed < minimum:
            raise ValueError
        if integer and not parsed.is_integer():
            raise ValueError
    except (TypeError, ValueError, OverflowError):
        kind = "정수" if integer else "숫자"
        raise HTTPException(422, f"{label}: {minimum} 이상의 유한한 {kind}를 입력하세요") from None
    return int(parsed) if integer else parsed
