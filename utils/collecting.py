class Commentator(object):
    """Класс комментатор, союирает комметарии в процессе выполнения скрипта
    в одну строку

    """

    def __init__(self, comment='', sep='\n'):
        self.comment = comment
        self.sep = sep

    def write(self, comment):
        if self.comment == '':
            self.comment += comment
        else:
            self.comment += self.sep + comment
