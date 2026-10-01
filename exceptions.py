"""Собственные исключения проекта."""


class PracticumAPIError(Exception):
    """Базовое исключение для ошибок API Практикум Домашка."""


class EndpointUnavailableError(PracticumAPIError):
    """Эндпоинт недоступен (сетевые ошибки, 5xx, 404 и т.п.)."""


class InvalidResponseError(PracticumAPIError):
    """Ответ API не соответствует ожидаемой структуре."""


class UnexpectedStatusError(PracticumAPIError):
    """Обнаружен неизвестный статус домашней работы."""
