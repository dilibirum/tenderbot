from datetime import datetime


class Commentator(object):
    """Класс комментатор, союирает комметарии в процессе выполнения скрипта
    в одну строку

    """

    def __init__(self, comment='', sep='\n'):
        self.comment = f'Необходимо уточнить: \n{comment}'
        self.sep = sep

    def write(self, comment):
        if self.comment == 'Необходимо заполнить: \n':
            self.comment += comment
        else:
            self.comment += self.sep + comment


def logger(message: str):
    """Функция создает типовой комметарий логгера

    :param message: str -- Текст лога
    :return: str -- типовой комметарий с текущей датой
    """
    return f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: {message}'
