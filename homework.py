import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import NoResponseError

load_dotenv()
logger = logging.getLogger(__name__)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TOKENS = {
    'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
    'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
    'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
}
TIMEOUT = 10
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
ERROR = 'Ошибка: {0}'

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправить сообщение."""
    return bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


def get_api_answer(current_timestamp):
    """Проверка доступности API Яндекс.Практикума."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS,
                            params=params, timeout=TIMEOUT)
    if response.status_code != HTTPStatus.OK:
        error = ERROR.format(error=response.status_code)
        logging.error(error)
        raise NoResponseError(error)
    answer = response.json()
    return answer


def check_response(response):
    """Проверка наличия и статуса домашней работы."""
    homeworks = response['homeworks']
    if homeworks is None:
        msg = 'Домашняя работа отсутствует'
        logger.error(msg)
    if not isinstance(homeworks, list):
        msg = 'Ответ API должен быть списком!'
        logger.error(msg)
        raise TypeError(msg)
    return homeworks


def parse_status(homework):
    """Проверка изменения статуса домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Провека переменных окружения."""
    no_tokens = [token for token in TOKENS if globals()[token] is None]
    if no_tokens:
        logger.error('Токены отсутствуют')
        return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    time_now = int(time.time())
    while True:
        try:
            response = get_api_answer(time_now)
            homework = check_response(response)
            if homework:
                send_message(bot, parse_status(homework[0]))
            time_now = response.get(
                'current_date', time_now)
        except Exception as error:
            logger.error('Ошибка: программа не работает', error)
            send_message(bot, 'Ошибка: программа не работает', error)
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
