import requests
import json
import random


with open('../configs/user-agents.txt') as f:
    USER_AGENTS = json.loads(f.read())


def create_headers():
    """Функция генерирует случайный HEADERS для обращения к серверу

    :return: словарь, содержащий HEADERS
    """

    user_agent = random.choice(USER_AGENTS['browsers'][USER_AGENTS['randomize'][str(random.randint(0, 984))]])
    return {"User-Agent": user_agent, "content-type": "text"}


def get_html(url: str,
             timeout=30) -> requests.models.Response:
    """Функция делает запрос по URL

    :param url: str -- URL-адрес
    :param timeout: int -- задержка, по умолчанию 30 сек
    :return: ответ сервера, объект requests.models.Response
    """
    headers = create_headers()
    response = requests.get(url, timeout=timeout, headers=headers)
    return response