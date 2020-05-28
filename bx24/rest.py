import urllib
import requests


class BX24(object):
    """Класс создает объект :class:`Bitrix24 <Bitrix24>`
    Используется для отправки запросов к REST API Битрикс24

    Атрибуты:
    :param domain: -- адрес портала Битрикс24
    :param uid: -- идентификационный номер пользователя, от имени которого осуществляется доступ к API Битрикс24
    :param webhook: -- вебхук для доступа к API Битрикс24
    :param timeout: -- задержка для отправки запросов к API Битрикс24, по умолчанию 60 сек.

    Использование:
        >>> from bx24.rest import BX24
        >>> bx24 = BX24(domain='https://yourdomain.bitrix24.ru/rest/',
        >>>             uid=0,
        >>>             webhook='yoursecretwebhook')
    """
    # TODO: добавить обработчик ошибок
    def __init__(self, domain: str, uid: int, webhook: str, timeout=60):
        self.url = f"{domain}/{uid}/{webhook}"
        self.timeout = timeout

    def callMethod(self, api_method, params=None):
        """Функция обращается к API Битрикс24

        :param api_method: метод API
        :param params: параметры метода
        :return: ответ сервера
        """
        query = f"{self.url}/{api_method}"
        data = http_build_query(params)

        if api_method.split('.')[-1] in ['add', 'update', 'delete', 'set']:
            query += '.json'
            response = requests.post(query, data=data).json()
        else:
            response = requests.get(query, params=data).json()
        return response


def http_build_query(query_data,
                     numeric_prefix=None,
                     arg_separator='&',
                     enc_type='RFC1738') -> str:
    """Функция генерирует URL-кодированную строку запроса из предоставленного словаря или списка

    Аргументы:
    :param query_data: str -- словарь или список, может быть как простой одномерной структурой,
                           так и списком списков или словарем словарей
    :param numeric_prefix: int -- числовые префиксы переменных
    :param arg_separator: str -- используется в качестве разделителя аргументов, по умолчанию '&'
    :param enc_type: str -- используется для кодирования контента,
                         по умолчанию используется кодирование по типу RFC1738,
                         который подразумевает, что пробелы кодируются как символы "плюс"(+),
                         Если enc_type равен 'RFC3986',
                         тогда кодирование осуществляется в соответствии RFC 3986,
                         и пробелы будут кодированы как %20.
    :return: возвращает URL-кодированную строку
    """
    # TODO: сделать функцию более универсальной, для любого уровня вложенности словарей
    query = ''
    ENCODE = {'RFC1738': {'left_bracket': '%5B',
                          'right_bracket': '%5D',
                          'space': '+',
                          },
              'RFC3986': {'left_bracket': '%5B',
                          'right_bracket': '%5D',
                          'space': '%20',
                          },
              }

    def build_query_from_dict(qd=query_data, np=numeric_prefix, sep=arg_separator, et=enc_type):
        q = ''
        count = 0

        for key, value in qd.items():
            if not isinstance(value, (dict, list)):
                q += f"{key}={ENCODE[et]['space'].join(map(lambda s: urllib.parse.quote(s).replace('/', '%2F'), str(value).split()))}"
            elif isinstance(value, dict):

                c = 0
                for k, v in value.items():
                    if not isinstance(v, (dict, list)):
                        q += f"{key}{ENCODE[et]['left_bracket']}{k}{ENCODE[et]['right_bracket']}=" + \
                             f"{ENCODE[et]['space'].join(map(lambda s: urllib.parse.quote(s).replace('/', '%2F'), str(v).split()))}"

                    elif isinstance(v, list):
                        q += build_query_from_list(qd=v)

                    elif isinstance(v, dict):

                        _c = 0
                        for _k, _v in v.items():
                            q += f"{key}{ENCODE[et]['left_bracket']}{k}{ENCODE[et]['right_bracket']}" + \
                                 f"{ENCODE[et]['left_bracket']}{_k}{ENCODE[et]['right_bracket']}=" + \
                                 f"{ENCODE[et]['space'].join(map(lambda s: urllib.parse.quote(s).replace('/', '%2F'), str(_v).split()))}"
                            _c += 1

                            if _c < len(v):
                                q += f"{sep}"

                    c += 1

                    if c < len(value):
                        q += f"{sep}"

            elif isinstance(value, list):

                c = 0
                for i, v in enumerate(value):
                    pr = i
                    if np is not None:
                        pr = f"{np}{i}"

                    if not isinstance(v, (dict, list)):
                        q += f"{key}{ENCODE[et]['left_bracket']}{pr}{ENCODE[et]['right_bracket']}=" + \
                             f"{ENCODE[et]['space'].join(map(lambda s: urllib.parse.quote(s).replace('/', '%2F'), str(v).split()))}"

                    elif isinstance(v, list):
                        q += build_query_from_list(qd=v)

                    elif isinstance(v, dict):
                        q += build_query_from_dict(qd=v)

                    c += 1

                    if c < len(value):
                        q += f"{sep}"

            count += 1
            if count < len(qd):
                q += f"{sep}"

        return q

    def build_query_from_list(qd=query_data, np=numeric_prefix, sep=arg_separator, et=enc_type):
        q = ''
        count = 0

        for i, value in enumerate(qd):
            pref = i
            if np is not None:
                pref = f"{np}{i}"

            if not isinstance(value, (dict, list)):
                q += f"{pref}={ENCODE[et]['space'].join(map(lambda s: urllib.parse.quote(s).replace('/', '%2F'), str(value).split()))}"
            elif isinstance(value, dict):
                q += build_query_from_dict(qd=value)
            elif isinstance(value, list):
                q += build_query_from_list(qd=value)

            count += 1
            if count < len(qd):
                q += f"{sep}"

        return q

    if isinstance(query_data, dict):
        query += build_query_from_dict()
    elif isinstance(query_data, list):
        query += build_query_from_list()

    return query
