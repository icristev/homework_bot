import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

from exceptions import JsonError, WrongStatus

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TOKENS = {
    'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
    'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
    'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
}

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
TIMEOUT = 5

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

HOMEWORK_STATUSES = 'Статус проверки работу изменился "{0}"-{1}'
MESSAGE_FAIL = 'Сообщение {0} не отправлено: {1}.'
SERVER_ERROR = 'Ошибка сервера. {0}, URL{1},Headers{2}, Params{3}, Timeout{4}'
JSON_ERROR = 'Отказ обслуживания. {0}, {1}, {2}, {3}, {4}'
STATUS_FAIL = 'Статус {0} не найден.'
CHECK_TOKENS_ERROR = 'Запуск программы невозможен.'
MESSAGE_SUCCESS = 'Сообщение {0} отправлено!'
TYPE_FAIL = 'Неверный тип для homeworks. Тип: {0}'
EMPTY_LIST = 'Работ нет.'
MISSING_TOKENS = 'Нет токенов: {0}.'
KEY_FAIL = 'Не обнаружен ключ homeworks!'
PROGRAMM_ERROR = 'Сбой в работе программы: {0}'
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


def send_message(bot, message):
    """Отправка сообщния."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(MESSAGE_SUCCESS.format(message))
    except telegram.TelegramError as error:
        logger.exception(MESSAGE_FAIL.format(message, error))


def get_api_answer(current_timestamp):
    """Запрос API Практикума."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=params,
                                timeout=TIMEOUT)
    except requests.RequestException as e:
        raise ConnectionError(SERVER_ERROR.format(
            e, ENDPOINT, HEADERS, params, TIMEOUT))
    if response.status_code != requests.codes.ok:
        raise WrongStatus(SERVER_ERROR.format(
            response.status_code, ENDPOINT, HEADERS, params, TIMEOUT))
    answer = response.json()
    if 'code' in answer:
        raise JsonError(JSON_ERROR.format(
            answer['code'], ENDPOINT, HEADERS, params, TIMEOUT))
    if 'error' in answer:
        raise JsonError(JSON_ERROR.format(
            answer['error'], ENDPOINT, HEADERS, params, TIMEOUT))
    return answer


def check_response(response):
    """Ответ."""
    try:
        homeworks = response['homeworks']
    except KeyError:
        raise KeyError(KEY_FAIL)
    if not isinstance(homeworks, list):
        raise TypeError(TYPE_FAIL.format(type(homeworks)))
    if not homeworks:
        logger.info(EMPTY_LIST)
    return homeworks


def parse_status(homework):
    """Извлечение статуса."""
    homework_name = homework.get('homework_bot', None)
    status = homework['status']
    if status in HOMEWORK_STATUSES:
        return HOMEWORK_STATUSES.format(f'Изменился статус проверки'
                                        f'работы"{homework_name}"',
                                        HOMEWORK_STATUSES[status])
    raise ValueError(STATUS_FAIL.format(status))


def check_tokens():
    """Доступность токенов."""
    lost_tokens = [token for token in TOKENS if globals()[token] is None]
    if lost_tokens:
        logger.error(MISSING_TOKENS.format(lost_tokens))
        return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise RuntimeError(CHECK_TOKENS_ERROR)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                send_message(bot, parse_status(homeworks[0]))
            current_timestamp = response.get(
                'current_date', current_timestamp)
        except Exception as error:
            logger.error(PROGRAMM_ERROR.format(error))
            send_message(bot, PROGRAMM_ERROR.format(error))
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        filename=__file__ + '.log',
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        level=logging.INFO)
    main()
