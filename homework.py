import logging
import os
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
MONTH_SECONDS = 30*24*3600


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


class NotFoundTokenException(Exception):
    pass

class EndPointNotAvailableException(Exception):
    pass

class WrongDataFormatException(Exception):
    pass

class SendMessageException(Exception):
    pass

class KeyNotFoundExcepton(Exception):
    pass

class WrongResponseException(Exception):
    pass



logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    filemode='w',
    format='%(asctime)s [%(levelname)s] - %(message)s)'
)


def check_tokens():
    """Проверка, что в Окружении есть требуемые переменные"""
    if any([
        PRACTICUM_TOKEN is None,
        TELEGRAM_TOKEN is None,
        TELEGRAM_CHAT_ID is None]
    ):
        logging.critical('Отсутствуют обязательные переменные '
                         'окружения во время запуска бота')
        raise NotFoundTokenException



def send_message(bot, message):
    """Отправка сообщения в Телеграм"""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
    except:
        logging.error('Сбой при отправке сщщбщения в Telegram.')
        # raise SendMessageException
    else:
        logging.debug('Сообщение в Telegram успешно отправлено.')



def get_api_answer(timestamp):
    """Запрос к API о статусе домашней работы"""

    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            raise WrongResponseException('Сбой в работе программы')
    except requests.RequestException:
        logging.error('Ошибка запроса к API')


    return response.json()


def check_response(response):
    """Проверка, что ответ от API вернулся в правильном формате"""
    if not isinstance(response, dict):
        raise TypeError
    if 'homeworks' not in response:
        raise KeyNotFoundExcepton
    if not isinstance(response['homeworks'], list):
        raise TypeError
    is_good_format = all(['homeworks' in response, 'current_date' in response])
    if not is_good_format:
        raise WrongDataFormatException


def parse_status(homework):
    """Получение из ответной строки API значений переменных"""
    if not 'homework_name' in homework:
        raise KeyNotFoundExcepton('Не найдено название домашней работы')
    if not 'status' in homework:
        raise KeyNotFoundExcepton('Не найден статус домашней работы')
    if not homework['status'] in HOMEWORK_VERDICTS:
        raise KeyError('Получен неожиданный статус домашней работы!')
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[homework['status']]


    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""

    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)


    while True:
        try:
            timestamp = int(time.time())
            response = get_api_answer(timestamp - MONTH_SECONDS * 1)
            check_response(response)
            if len(response['homeworks']) > 0:
                message = parse_status(response['homeworks'][0])
                send_message(bot, message)
            else:
                logging.debug('Новых статусов в ответе API нет.')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'

        else:
            time.sleep(RETRY_PERIOD)
            bot.polling()  # Потом поставить интревал




if __name__ == '__main__':
    main()
