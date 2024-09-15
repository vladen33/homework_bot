import logging
import os
import time

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

class WrongDataFormatExceptions(Exception):
    pass


def check_tokens():
    """Проверка, что в Окружении есть требуемые переменные"""
    if any([
        PRACTICUM_TOKEN is None,
        TELEGRAM_TOKEN is None,
        TELEGRAM_CHAT_ID is None]
    ):
        raise NotFoundTokenException



def send_message(bot, message):
    """Отправка сообщения в Телеграм"""
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message,
    )


def get_api_answer(timestamp):
    """Запрос к API о статусе домашней работы"""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except EndPointNotAvailableException as error:
        logging.warning(f'Невозможно получить данные через API: {error}')
    else:
        return response.json()


def check_response(response):
    """Проверка, что ответ от API вернулся в правильном формате"""
    is_good_format = all(['homeworks' in response, 'current_date' in response])
    if not is_good_format:
        raise WrongDataFormatExceptions


def parse_status(homework):
    """Получение из ответной строки API значений переменных"""
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[homework['status']]


    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    bot.polling()  # Потом поставить интревал
    while True:
        try:
            timestamp = int(time.time())
            response = get_api_answer(timestamp - MONTH_SECONDS * 1)
            check_response(response)
            if len(response['homeworks']) > 0:
                message = parse_status(response['homeworks'][0])
                send_message(bot, message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'

        time.sleep(10)




if __name__ == '__main__':
    main()
