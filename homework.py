"""Бот для проверки статуса домашних работ на сервисе Практикум Домашка."""

import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import vk_api
from dotenv import load_dotenv

from exceptions import (
    EndpointUnavailableError,
    InvalidResponseError,
    UnexpectedStatusError,
)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
VK_TOKEN = os.getenv('VK_TOKEN')
VK_USER_ID = os.getenv('VK_USER_ID')

RETRY_PERIOD_IN_SECONDS = 600
# Алиас для совместимости с тестами, которые ищут имя RETRY_PERIOD.
RETRY_PERIOD = RETRY_PERIOD_IN_SECONDS

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)


def check_tokens():
    """Проверяет доступность обязательных переменных окружения.

    Возвращает список имён отсутствующих переменных.
    Пустой список означает, что все переменные на месте.
    """
    required_tokens = (
        ('PRACTICUM_TOKEN', PRACTICUM_TOKEN),
        ('VK_TOKEN', VK_TOKEN),
        ('VK_USER_ID', VK_USER_ID),
    )
    return [name for name, token_value in required_tokens if not token_value]


def send_message(vk, message):
    """Отправляет сообщение в VK-чат.

    Возвращает True при успешной отправке, иначе False.
    """
    try:
        vk.messages.send(
            user_id=VK_USER_ID,
            message=message,
            random_id=int(time.time() * 1000),
        )
    except Exception as error:
        logger.error('Сбой при отправке сообщения в VK: %s', error)
        return False
    logger.debug('Бот отправил сообщение "%s"', message)
    return True


def get_api_answer(timestamp):
    """Делает запрос к API Практикум Домашка.

    Возвращает ответ API, приведённый к типам данных Python.
    """
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params,
            timeout=10,
        )
    except requests.RequestException as error:
        raise EndpointUnavailableError(
            f'Сбой при запросе к эндпоинту {ENDPOINT}: {error}'
        ) from error

    if response.status_code != HTTPStatus.OK:
        raise EndpointUnavailableError(
            f'Эндпоинт {ENDPOINT} недоступен. '
            f'Код ответа API: {response.status_code}. '
            f'Параметры запроса: {params}. '
            f'Тело ответа: {response.text}'
        )

    try:
        return response.json()
    except ValueError as error:
        raise InvalidResponseError(
            f'Ответ API не является JSON: {error}'
        ) from error


def check_response(response):
    """Проверяет ответ API на соответствие документации.

    Возвращает список домашних работ.
    """
    if not isinstance(response, dict):
        raise TypeError(
            f'Ответ API не является словарём, получен {type(response)}.'
        )

    if 'homeworks' not in response:
        raise InvalidResponseError(
            'В ответе API отсутствует ключ "homeworks".'
        )

    if 'current_date' not in response:
        raise InvalidResponseError(
            'В ответе API отсутствует ключ "current_date".'
        )

    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(
            'Ключ "homeworks" в ответе API не является списком, '
            f'получен {type(homeworks)}.'
        )

    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы и формирует сообщение.

    Возвращает строку с вердиктом из словаря HOMEWORK_VERDICTS.
    """
    if 'homework_name' not in homework:
        raise InvalidResponseError(
            'В информации о домашней работе отсутствует ключ "homework_name".'
        )

    if 'status' not in homework:
        raise InvalidResponseError(
            'В информации о домашней работе отсутствует ключ "status".'
        )

    homework_name = homework['homework_name']
    status = homework['status']

    if status not in HOMEWORK_VERDICTS:
        raise UnexpectedStatusError(
            f'Неожиданный статус домашней работы: {status}'
        )

    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    missing_tokens = check_tokens()
    if missing_tokens:
        logger.critical(
            'Отсутствует обязательная переменная окружения: %s. '
            'Программа принудительно остановлена.',
            ', '.join(missing_tokens),
        )
        sys.exit(1)

    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()

    timestamp = int(time.time())
    last_error_message = None

    while True:
        try:
            api_answer = get_api_answer(timestamp)
            homeworks = check_response(api_answer)

            if not homeworks:
                logger.debug('В ответе API нет новых статусов.')
            else:
                for homework in homeworks:
                    message = parse_status(homework)
                    send_message(vk, message)

            timestamp = api_answer.get('current_date', timestamp)
            last_error_message = None

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if str(error) != last_error_message:
                send_message(vk, message)
                last_error_message = str(error)

        finally:
            time.sleep(RETRY_PERIOD_IN_SECONDS)


if __name__ == '__main__':
    main()
