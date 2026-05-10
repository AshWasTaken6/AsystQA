from contextvars import ContextVar

correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str):
    return correlation_id_var.set(correlation_id)


def reset_correlation_id(token) -> None:
    correlation_id_var.reset(token)
