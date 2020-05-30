from datetime import datetime
import numpy as np
import logging

logging.basicConfig(filename='../data/logs/tenderbot.log', level=logging.INFO)  # add filemode="w" to overwrite


def to_numeric(string) -> float:
    """Функция преобразует строку в формат float

    :param string: str -- строковое представления числа
    :return: число в формате float
    """
    try:
        if string != '' or string is not None:
            result_int = int(''.join(string.split(',')).strip()) / 100
        else:
            result_int = np.nan
    except ValueError as e:
        result_int = np.nan
        logging.error(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} Cannot convert {string} to numeric. {e}')
    return result_int


def date_formatter(date: str, formatter='%Y-%m-$d'):
    """Функция преобразует формат даты День.Месяц.Год в Год-Месяц-День

    :param date: str -- исходная дата в форме строки
    :param formatter: str -- шаблон формата даты
    :return: str -- дата в требуемом формате
    """
    try:
        result_date = datetime.strptime(date, '%d.%m.%Y').strftime(formatter)
    except ValueError as e:
        result_date = date
        logging.error(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} Cannot format {date} to %Y-%m-%d. {e}')
    return result_date
