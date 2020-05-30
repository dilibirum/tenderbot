def to_numeric(string) -> float:
    """Функция преобразует строку в формат float

    :param string: str -- строковое представления числа
    :return: число в формате float
    """
    return int(''.join(string.split(',')).strip()) / 100
