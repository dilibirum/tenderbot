import requests


def get_html(url: str) -> str:
    """Функция делает запрос по URL

    :param url: str -- URL-адрес
    :return: HTML-страницу в виде текста
    """
    response = requests.get(url)
    return response.text