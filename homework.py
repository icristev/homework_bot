import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import NoResponseError, VerdictError

load_dotenv()
logger = logging.getLogger(__name__)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

LIST_TOKENS = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]

TOKENS = {
    'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
    'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
    'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
}

TIMEOUT = 5
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
ERROR = 'Ошибка: {0}'

VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправить сообщение."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.TelegramError as error:
        logger.exception(f'Сообщение {message} не отправлено: {error}')


def get_api_answer(current_timestamp):
    """Проверка доступности API Яндекс.Практикума."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS,
                                params=params, timeout=TIMEOUT)
    except requests.RequestException as exception:
        raise ConnectionError(f'Ошибка сервера. {exception},'
                              f'URL{ENDPOINT}, HEADERS, params, TIMEOUT')

    if response.status_code != HTTPStatus.OK:
        error = ERROR.format(error=response.status_code)
        logging.error(error)
        raise NoResponseError(error)
    try:
        answer = response.json() or None
    except ValueError:
        error = 'Сервер вернул пустой ответ'
        logger.error(error)
    return answer


def check_response(response):
    """Проверка наличия и статуса домашней работы."""
    try:
        homeworks = response['homeworks']
    except KeyError:
        raise KeyError('Нет ключа homeworks')
    if not isinstance(homeworks, list):
        msg = 'Ответ API должен быть списком!'
        logger.error(msg)
        raise TypeError(msg)
    return homeworks


def parse_status(homework):
    """Проверка изменения статуса домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    msg = 'Такого статуса домашней работы не сущетвует'
    if homework_status not in VERDICTS:
        logger.error(msg)
        raise KeyError(msg)
    verdict = VERDICTS[homework_status]
    if homework_status in VERDICTS:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    raise VerdictError(msg)


def check_tokens():
    """Провека переменных окружения."""
    tokens = all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])
    if tokens:
        return True
    return False


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    time_now = int(time.time())
    msg = 'Ошибка: программа не работает'
    while True:
        try:
            response = get_api_answer(time_now)
            homework = check_response(response)
            if homework:
                send_message(bot, parse_status(homework[0]))
            time_now = response.get(
                'current_date', time_now)
        except Exception as error:
            a = logger.error(msg, error)
            b = send_message(bot, msg, error)
            if a == b:
                return b
            else:
                return a, b
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
