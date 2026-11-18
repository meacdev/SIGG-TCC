from decimal import Decimal, InvalidOperation

from backend.errors import APIError


def number(value, field, places=2, maximum="999.99"):
    try:
        if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
            raise ValueError
        result = Decimal(str(value))
        if (
            not result.is_finite()
            or result.as_tuple().exponent < -places
            or abs(result) > Decimal(maximum)
        ):
            raise ValueError
        return result
    except InvalidOperation, ValueError:
        raise APIError(
            422, "VALIDACAO", "Informe um número decimal válido.", {field: "Valor inválido."}
        ) from None
