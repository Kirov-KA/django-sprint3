"""Собственные исключения проекта."""


class PracticumAPIError(Exception):
    """Базовое исключение для ошибок API Практикум Домашка."""


class EndpointUnavailableError(PracticumAPIError):
    """Эндпоинт недоступен (сетевые ошибки, 5xx, 404 и т.п.)."""


class InvalidResponseError(ValueError):
    """Ответ API не соответствует ожидаемой структуре."""


class MissingKeyError(InvalidResponseError, KeyError):
    """В ответе API отсутствует ожидаемый ключ."""


class UnexpectedStatusError(PracticumAPIError):
    """Обнаружен неизвестный статус домашней работы."""


class SendMessageError(Exception):
    """Сбой при отправке сообщения в VK."""
