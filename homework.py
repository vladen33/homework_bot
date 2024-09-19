import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot

from exceptions import (KeyNotFoundExcepton, SendMessageException,
                        WrongResponseException)


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
MONTH_SECONDS = 30 * 24 * 3600

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка, что в Окружении есть требуемые переменные."""
    tokens = {'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
              'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
              'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
              }
    missing_tokens = [token for token, value in tokens.items() if not value]
    if missing_tokens:
        logging.critical('Отсутствуют обязательные переменные '
                         'окружения во время запуска бота: '
                         f'{", ".join(missing_tokens)}')
        return False
    return True


def send_message(bot, message):
    """Отправка сообщения в Телеграм."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logging.debug('Сообщение в Telegram успешно отправлено.')
    except Exception as error:
        raise SendMessageException(
            f'Сбой при отправке сообщения в Telegram: {error}'
        )


def get_api_answer(timestamp):
    """Запрос к API о статусе домашней работы."""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS,
                                params={'from_date': timestamp})
    except requests.RequestException as error:
        raise WrongResponseException(
            f'Сбой при запросе к эндпоинту {error}'
        )
    if response.status_code != HTTPStatus.OK:
        raise WrongResponseException(
            f'Сбой в работе программы: Эндпоинт {ENDPOINT} недоступен. '
            f'Код ответа API: {response.status_code}'
        )
    return response.json()


def check_response(response):
    """Проверка, что ответ от API вернулся в правильном формате."""
    if not isinstance(response, dict):
        raise TypeError(
            'Неправильный тип данных. Требуется тип \'dict\''
        )
    if 'homeworks' not in response:
        raise KeyNotFoundExcepton('В ответе API нет ключа \'homeworks\'')
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            'Неправильный тип данных. Требуется тип \'list\''
        )


def parse_status(homework):
    """Получение из ответной строки API значений переменных."""
    missing_keys = []
    for key in ('homework_name', 'status'):
        if key not in homework:
            missing_keys.append(key)
    if missing_keys:
        raise KeyNotFoundExcepton(
            'В словаре \'homework\' отсутствуют ключи:'
            f' {", ".join(missing_keys)}'
        )
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyNotFoundExcepton(
            'Получен неожиданный статус домашней работы: '
            f'{homework_status}'
        )
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    prev_error = ''
    while True:
        try:
            response = get_api_answer(timestamp - MONTH_SECONDS * 1)
            timestamp = response.get('current_date', timestamp)
            check_response(response)
            homework_response = response['homeworks']
            if homework_response:
                message = parse_status(homework_response[0])
                send_message(bot, message)
            else:
                logging.debug('Новых статусов в ответе API нет.')
        except Exception as error:
            if prev_error != error:
                try:
                    send_message(bot, error)
                    prev_error = error
                except SendMessageException:
                    logging.error('Не удалось отправить сообщение '
                                  'об ошибке в Telegram!')
            logging.error(error)
        finally:
            time.sleep(RETRY_PERIOD)
            bot.polling()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename='main.log',
        filemode='w',
        format='%(asctime)s [%(levelname)s] - %(message)s)'
    )
    main()
