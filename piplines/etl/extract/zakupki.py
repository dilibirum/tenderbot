from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
import numpy as np
import time
from piplines.etl.extract.utils import get_request
from piplines.etl.transform.converter import to_numeric, date_formatter, datetime_formatter
from utils.collecting import logger, Commentator
import logging

logging.basicConfig(filename='../../../data/logs/tenderbot.log', level=logging.INFO)  # add filemode="w" to overwrite


def search_query(search_string: str,
                 start_date: str,
                 end_date: str,
                 search_filter='Дате размещения',
                 page_number=1,
                 ) -> str:
    """Функция формирует GET-запрос к порталу https://zakupki.gov.ru/

    :param search_string: str -- поисковый запрос
    :param start_date: str -- дата начала фильтрации закупок, формат даты 01.01.2012
    :param end_date: str --дата окончания закупок, формат даты 01.01.2012
    :param search_filter: str -- тип сортировки, по умолчанию по дате размещения
    :param page_number: int -- номер страницы, по умолчанию 1 (первая страница)
    :return: str -- сформированный запрос
    """
    s_str = '+'.join(list(map(quote, search_string.split())))
    s_flt = '+'.join(list(map(quote, search_filter.split())))
    query = 'https://zakupki.gov.ru/epz/order/extendedsearch/results.html' \
            + f'?searchString={s_str}' \
            + '&morphology=on' \
            + f'&search-filter=+{s_flt}' \
            + f'&pageNumber={page_number}' \
            + '&sortDirection=true' \
            + '&recordsPerPage=_100' \
            + '&showLotsInfoHidden=true' \
            + '&sortBy=PUBLISH_DATE' \
            + '&fz44=on' \
            + '&fz223=on' \
            + '&af=on' \
            + '&selectedSubjectsIdNameHidden=%7B%7D' \
            + f'&publishDateFrom={start_date}' \
            + f'&publishDateTo={end_date}' \
            + '&currencyIdGeneral=-1' \
            + '&OrderPlacementSmallBusinessSubject=on' \
            + '&OrderPlacementRnpData=on' \
            + '&OrderPlacementExecutionRequirement=on' \
            + '&orderPlacement94_0=0' \
            + '&orderPlacement94_1=0' \
            + '&orderPlacement94_2=0'
    return query


def get_hrefs(response: requests.models.Response) -> list:
    """Функция ищет ссылки на закупки на странице поиска

    :param response: requests.models.Response -- ответ сервера
    :return: list -- список со сслыками
    """
    soup = get_soup(response)
    hrefs = []
    cards = soup.find_all('div', {'class': 'row no-gutters registry-entry__form mr-0'})
    for card in cards:
        hrefs.append(card.find('div', {'class': 'registry-entry__header-mid__number'})
                     .find('a')
                     .get('href'))
    return hrefs


def get_soup(response: requests.models.Response) -> BeautifulSoup:
    """Функция создает объект BeautifulSoup из ответа сервера

    :param response: requests.models.Response -- ответ сервера
    :return: BeautifulSoup -- объект BeautifulSoup
    """
    html = response.text
    return BeautifulSoup(html, 'lxml')


def create_card() -> dict:
    """Функция создает карточку закупки

    :return: dict -- словарь с данными карточки
    """
    return dict.fromkeys([
        'id',  # Реестровый номер извещения
        'law',  # Федеральный закон
        'type',  # Способ размещения закупки
        'description',  # Наименование закупки
        'init_date',  # Дата размещения извещения
        'platform',  # Наименование электронной площадки
        'platform_url',  # Адрес электронной площадки
        'author_name',  # Наименование организации
        'author_inn',  # ИНН
        'author_ogrn',  # ОГРН
        'address',  # Место нахождения
        'author_manager',  # Контактное лицо
        'author_email',  # Электронная почта
        'author_phone',  # Телефон
        'start_date',  # Дата начала срока подачи заявок
        'end_date',  # Дата и время окончания подачи заявок(по местному времени заказчика)
        'timezone',  # Часовой пояс заказчика
        'result_date',  # Дата подведения итогов
        'price',  # Начальная (максимальная) цена договора
        'tender_deposit',  # Обеспечение заявки
        'contract_deposit',  # Обеспечение контракта
        'warranty_deposit',  # Обеспечение гарантийных обязательств
        'costs',  # Себестоимость контракта
        'url',  # URL-закупки на ЕИС в сфере закупок
        'docs',  # URL-ссылка на документацию
        'comment',  # Комментарий к сделке
        'time',  # Дата записи карточки в формате unicode
    ])


def get_id(soup: BeautifulSoup, comment: Commentator) -> int:
    """Функция находит реестровый номер извещения

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: реестровый номер извещения
    """
    result = 0
    try:
        result = int(soup.find('div', {'class': 'registry-entry__header-mid__number'})
                     .text
                     .strip()
                     .split()[1]
                     .strip())
    except AttributeError:
        msg = 'Data for the field "id" could not be found'
        logging.error(logger(msg))
        comment.write('\t• реестровый номер извещения;')
    return result


def get_law(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит федеральный закон

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: федеральный закон
    """
    result = ''
    try:
        result = soup.find('div', {'class': 'registry-entry__header-top__title text-truncate'}) \
            .text \
            .strip() \
            .split()[0] \
            .strip()
    except AttributeError:
        msg = 'Data for the field "law" could not be found'
        logging.error(logger(msg))
        comment.write('\t• номер федерального закона;')
    return result


def get_url(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит URL-закупки на ЕИС в сфере закупок

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: URL-закупки на ЕИС в сфере закупок
    """
    result = ''
    try:
        _url = soup.find('div', {'class': 'registry-entry__header-mid__number'}) \
            .find('a') \
            .get('href')
        if 'https://zakupki.gov.ru' not in _url:
            _url = f"https://zakupki.gov.ru{_url}"
        result = _url
    except AttributeError:
        msg = 'Data for the field "url" could not be found'
        logging.error(logger(msg))
        comment.write('\t• URL-закупки на ЕИС в сфере закупок;')
    return result


def get_price(soup: BeautifulSoup, comment: Commentator) -> float:
    """Функция находит начальную (максимальную) цену договора

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: начальная (максимальная) цена договора
    """
    result = np.nan
    try:
        result = to_numeric(soup.find('div', {'class': 'price-block__value'})
                            .text
                            .replace('\xa0', '')
                            .split()[0])
    except AttributeError:
        msg = 'Data for the field "price" could not be found'
        logging.error(logger(msg))
        comment.write('\t• начальную (максимальную) цену договора;')
    return result


def get_type(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит способ размещения закупки

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: Способ размещения закупки
    """
    result = ''
    # TODO: если новая структура HTML-страницы станет преимущественной, то блоки try – поменять местами
    try:
        result = soup.find('td', text='Способ размещения закупки') \
            .find_next('td') \
            .text \
            .strip()
    except AttributeError:
        try:
            result = soup.find('span', {'class': 'section__title'},
                               text='Способ определения поставщика (подрядчика, исполнителя)') \
                .find_next('span', {'class': 'section__info'}) \
                .text
        except AttributeError:
            msg = 'Data for the field "type" could not be found'
            logging.error(logger(msg))
            comment.write('\t• способ размещения закупки;')
    return result


def get_description(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит наименование закупки

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: Наименование закупки
    """
    result = ''
    try:
        result = soup.find('td', text='Наименование закупки') \
            .find_next('td') \
            .text \
            .strip()
    except AttributeError:
        try:
            result = soup.find('span', {'class': 'cardMainInfo__title'}, text='Объект закупки') \
                .find_next('span', {'class': 'cardMainInfo__content'}) \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "description" could not be found'
            logging.error(logger(msg))
            comment.write('\t• наименование/объект закупки;')
    return result


def get_init_date(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит дату размещения извещения

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: Дата размещения извещения

    """
    result = ''
    try:
        result = date_formatter(soup.find('td', text='Дата размещения извещения')
                                .find_next('td')
                                .text
                                .split()[0]
                                .strip())
    except AttributeError:
        try:
            result = datetime_formatter(soup.find('span', {'class': 'cardMainInfo__title'},
                                                  text='Размещено в ЕИС')
                                        .find_next('span', {'class': 'cardMainInfo__content'})
                                        .text
                                        .strip())
        except AttributeError:
            msg = 'Data for the field "init_date" could not be found'
            logging.error(logger(msg))
            comment.write('\t• дату размещения извещения о закупке;')
    return result


def get_platform(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит наименование электронной площадки

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: Наименование электронной площадки
    """
    result = ''
    try:
        result = soup.find('td', text='Наименование электронной площадки в ' +
                                      'информационно-телекоммуникационной сети «Интернет»') \
            .find_next('td') \
            .text \
            .strip()
    except AttributeError:
        try:
            result = soup.find('span', {'class': 'section__title'},
                               text='Наименование электронной площадки в ' +
                                    'информационно-телекоммуникационной сети "Интернет"') \
                .find_next('span', {'class': 'section__info'}) \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "platform" could not be found'
            logging.error(logger(msg))
            comment.write('\t• наименование электронной площадки;')
    return result


def get_platform_url(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит адрес электронной площадки

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: Адрес электронной площадки

    """
    result = ''
    try:
        result = soup.find('td', text='Адрес электронной площадки в ' +
                                      'информационно-телекоммуникационной сети ' +
                                      '«Интернет»') \
            .find_next('td') \
            .text \
            .strip()
    except AttributeError:
        try:
            result = soup.find('span', {'class': 'section__title'},
                               text='Адрес электронной площадки в ' +
                                    'информационно-телекоммуникационной сети "Интернет"') \
                .find_next('span', {'class': 'section__info'}) \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "platform_url" could not be found'
            logging.error(logger(msg))
            comment.write('\t• адрес электронной площадки;')
    return result


def get_tender_deposit(soup: BeautifulSoup, comment: Commentator):
    """Функция находит обеспечение заявки

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: Обеспечение заявки
    """
    result = None
    try:
        response = soup.find('td', text='Обеспечение заявки') \
            .find_next('td') \
            .text \
            .strip()
        if response == 'Не требуется':
            result = 0.0
        else:
            try:
                result = to_numeric(response)
            except ValueError:
                result = response
                msg = f'Cannot convert "tender_deposit"={response} to float'
                logging.error(logger(msg))
    except AttributeError:
        try:
            result = to_numeric(''.join(soup.find('span', {'class': 'section__title'},
                                                  text='Размер обеспечения заявки')
                                        .find_next('span', {'class': 'section__info'})
                                        .text
                                        .split('\xa0')[:-1])
                                .strip())
        except AttributeError:
            msg = 'Data for the field "tender_deposit" could not be found'
            logging.error(logger(msg))
            comment.write('\t• обеспечение заявки;')
    return result


def get_contract_deposit(soup: BeautifulSoup, price: float, comment: Commentator) -> float:
    """Функция находит обеспечение контракта

    :param comment: -- объект Commentator
    :param price: -- цена котракта
    :param soup: -- объект BeautifulSoup
    :return: Обеспечение контракта
    """
    result = 0.0
    try:
        raw_data = ''.join(soup.find('span', {'class': 'section__title'},
                                     text='Размер обеспечения исполнения контракта')
                           .find_next('span', {'class': 'section__info'})
                           .text
                           .split()[0]) \
            .strip()
        contract_deposit = to_numeric(raw_data)
        if contract_deposit < 1:
            contract_deposit = price * contract_deposit
        result = contract_deposit
    except AttributeError:
        msg = 'Data for the field "contract_deposit" could not be found'
        logging.error(logger(msg))
        comment.write('\t• обеспечение контракта;')
    return result


def get_warranty_deposit(soup: BeautifulSoup, price: float, comment: Commentator) -> float:
    """Функция находит обеспечение гарантийных обязательств

    :param comment: -- объект Commentator
    :param price: -- цена котракта
    :param soup: -- объект BeautifulSoup
    :return: Обеспечение гарантийных обязательств
    """
    result = 0.0
    try:
        warranty_deposit = to_numeric(''.join(soup.find('span', {'class': 'section__title'},
                                                        text='Размер обеспечения гарантийных обязательств')
                                              .find_next('span', {'class': 'section__info'})
                                              .text
                                              .split('\xa0')[:-1])
                                      .strip())
        if warranty_deposit < 1:
            warranty_deposit = price * warranty_deposit
        result = warranty_deposit
    except AttributeError:
        msg = 'Data for the field "warranty_deposit" could not be found'
        logging.error(logger(msg))
        comment.write('\t• обеспечение гарантийных обязательств;')
    return result


def get_author_name(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит наименование организации

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: Наименование организации
    """
    result = ''
    try:
        result = soup.find('td', text='Наименование организации') \
            .find_next('td') \
            .text \
            .strip()
    except AttributeError:
        try:
            result = soup.find('span', {'class': 'section__title'},
                               text='Организация, осуществляющая размещение') \
                .find_next('span', {'class': 'section__info'}) \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "author_name" could not be found'
            logging.error(logger(msg))
            comment.write('\t• наименование организации;')
    return result


def get_author_inn(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит ИНН

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: ИНН
    """
    result = ''
    try:
        result = soup.find('td', text='ИНН') \
            .find_next('td') \
            .text \
            .strip()
    except AttributeError:
        msg = 'Data for the field "inn" could not be found'
        logging.error(logger(msg))
        comment.write('\t• ИНН организации;')
    return result


def get_author_ogrn(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит ОГРН

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: ОГРН
    """
    result = ''
    try:
        result = soup.find('td', text='ОГРН') \
            .find_next('td') \
            .text \
            .strip()
    except AttributeError:
        msg = 'Data for the field "author_ogrn" could not be found'
        logging.error(logger(msg))
        comment.write('\t• ОГРН организации;')
    return result


def get_address(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит адрес место нахождения

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: Место нахождения
    """
    result = ''
    try:
        result = soup.find('td', text='Место нахождения') \
            .find_next('td') \
            .text \
            .strip()
    except AttributeError:
        try:
            result = soup.find('span', {'class': 'section__title'},
                               text='Почтовый адрес') \
                .find_next('span', {'class': 'section__info'}) \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "address" could not be found'
            logging.error(logger(msg))
            comment.write('\t• адрес место нахождения организации;')
    return result


def get_author_manager(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит контактное лицо

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: Контактное лицо
    """
    result = ''
    try:
        result = soup.find('td', text='Контактное лицо') \
            .find_next('td') \
            .text \
            .strip()
    except AttributeError:
        try:
            result = soup.find('span', {'class': 'section__title'},
                               text='Ответственное должностное лицо') \
                .find_next('span', {'class': 'section__info'}) \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "author_manager" could not be found'
            logging.error(logger(msg))
            comment.write('\t• ФИО контактного лица организации;')
    return result


def get_author_email(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит электронную почту

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: Электронная почта
    """
    result = ''
    try:
        result = soup.find('td', text='Электронная почта') \
            .find_next('td') \
            .text \
            .strip()
    except AttributeError:
        try:
            result = soup.find('span', {'class': 'section__title'},
                               text='Адрес электронной почты') \
                .find_next('span', {'class': 'section__info'}) \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "author_email" could not be found'
            logging.error(logger(msg))
            comment.write('\t• электронную почту организации;')
    return result


def get_author_phone(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит телефон

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: Телефон
    """
    result = ''
    try:
        result = soup.find('td', text='Телефон') \
            .find_next('td') \
            .text \
            .strip()
    except AttributeError:
        try:
            result = soup.find('span', {'class': 'section__title'},
                               text='Номер контактного телефона') \
                .find_next('span', {'class': 'section__info'}) \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "author_phone" could not be found'
            logging.error(logger(msg))
            comment.write('\t• телефон организации;')
    return result


def get_start_date(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит дату начала срока подачи заявок

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: Дата начала срока подачи заявок
    """
    result = ''
    try:
        result = date_formatter(soup
                                .find('td', text='Дата начала срока подачи заявок')
                                .find_next('td')
                                .text
                                .split()[0]
                                .strip())
    except AttributeError:
        try:
            result = datetime_formatter(soup.find('span', {'class': 'section__title'},
                                                  text='Дата и время начала срока подачи заявок')
                                        .find_next('span', {'class': 'section__info'})
                                        .text
                                        .strip())
        except AttributeError:
            msg = 'Data for the field "start_date" could not be found'
            logging.error(logger(msg))
            comment.write('\t• дату начала срока подачи заявок;')
    return result


def get_end_date(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит дату и время окончания подачи заявок(по местному времени заказчика)

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: Дата и время окончания подачи заявок(по местному времени заказчика)
    """
    result = ''
    try:
        result = date_formatter(soup
                                .find('span', text='(по местному времени заказчика)')
                                .find_next('td')
                                .text
                                .split()[0]
                                .strip())
    except AttributeError:
        try:
            result = datetime_formatter(soup.find('span', {'class': 'section__title'},
                                                  text='Дата и время окончания срока подачи заявок')
                                        .find_next('span', {'class': 'section__info'})
                                        .text
                                        .strip())
        except AttributeError:
            msg = 'Data for the field "end_date" could not be found'
            logging.error(logger(msg))
            comment.write('\t• дату и время окончания подачи заявок;')
    return result


def get_timezone(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит часовой пояс заказчика

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: Часовой пояс заказчика
    """
    result = ''
    try:
        result = soup.find('td', text='Дата начала срока подачи заявок') \
            .find_next('td') \
            .text \
            .split()[1] \
            .replace('(', '') \
            .replace(')', '') \
            .strip()
    except AttributeError:
        msg = 'Data for the field "timezone" could not be found'
        logging.error(logger(msg))
        comment.write('\t• часовой пояс заказчика;')
    return result


def get_result_date(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит дату подведения итогов

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: Дата подведения итогов
    """
    result = ''
    try:
        result = date_formatter(soup
                                .find('td', text='Дата подведения итогов')
                                .find_next('td')
                                .text
                                .split()[0]
                                .strip())
    except AttributeError:
        try:
            result = datetime_formatter(soup.find('span', {'class': 'section__title'},
                                                  text="""
                            Дата и время рассмотрения и оценки первых частей заявок
                        """)
                                        .find_next('span', {'class': 'section__info'})
                                        .text
                                        .strip())
        except AttributeError:
            msg = 'Data for the field "result_date" could not be found'
            logging.error(logger(msg))
            comment.write('\t• дату подведения итогов;')
    return result


# TODO: передалать, убрать костыли
def get_comment(soup: BeautifulSoup, comment: Commentator) -> str:
    """Функция находит преимущества, требования к участникам

    :param comment: -- объект Commentator
    :param soup: -- объект BeautifulSoup
    :return: Преимущества, требования к участникам
    """
    result = ''
    _result = ''
    try:
        result += '\nПреимущества:\n\n'
        result += soup.find('span', {'class': 'section__title'}, text='Преимущества') \
                      .find_next('span', {'class': 'section__info'}) \
                      .text \
                      .strip() + '\n'
        result += '\nТребования к участникам:\n\n'
        result += soup.find('span', {'class': 'section__title'}, text='Требования к участникам') \
            .find_next('span', {'class': 'section__info'}) \
            .text \
            .strip() \
            .replace('\n', '') \
            .replace('\t', '') \
            .replace('\xa0', ' ') + '\n'
        result += '\nОграничения и запреты:\n\n'
        result += soup.find('span', {'class': 'section__title'}, text='Ограничения и запреты') \
            .find_next('span', {'class': 'section__info'}) \
            .text \
            .strip() \
            .replace('\n', '') \
            .replace('\t', '') \
            .replace('\xa0', ' ') + '\n'
        _result = result
    except AttributeError:
        msg = 'Data for the field "timezone" could not be found'
        logging.error(logger(msg))
        comment.write('\t• требования и ограничения к участникам;')
    return _result


# TODO: 30 мая 2020 года изменилась структура сайта!!!
def get_card_data(card=None) -> dict:
    """Функция парсит информацию о закупке и записывает с структурированный словарь

    :param card: -- объект BeautifulSoup
    :return: -- словарь со структуированной информацией о закупке
    """
    comment = Commentator()
    card_data = create_card()
    msg = f'Card #{hash(card)} starts recording'
    logging.info(logger(msg))
    card_data['time'] = time.time()

    # пишем данные из карточки закупки
    card_data['id'] = get_id(card, comment)  # 'id', Реестровый номер извещения
    card_data['law'] = get_law(card, comment)  # 'law', Федеральный закон
    card_data['url'] = get_url(card, comment)  # 'url', URL-закупки на ЕИС в сфере закупок
    card_data['price'] = get_price(card, comment)  # 'price', Начальная (максимальная) цена договора

    # пишем данные из по ссылке закупки, для 44-ФЗ и 223-ФЗ представление страницы с данными различается
    try:
        lot_url = card_data['url']
        soup: BeautifulSoup = get_soup(get_request(lot_url))
        msg = f'Card #{hash(card)} starts recording by url'
        logging.info(logger(msg))

        card_data['type'] = get_type(soup, comment)  # 'type', Способ размещения закупки
        card_data['description'] = get_description(soup, comment)  # 'description', Наименование закупки
        card_data['init_date'] = get_init_date(soup, comment)  # 'init_date', Дата размещения извещения
        card_data['platform'] = get_platform(soup, comment)  # 'platform', Наименование электронной площадки
        card_data['platform_url'] = get_platform_url(soup, comment)  # 'platform_url', Адрес электронной площадки
        card_data['tender_deposit'] = get_tender_deposit(soup, comment)  # 'tender_deposit', Обеспечение заявки
        card_data['contract_deposit'] = get_contract_deposit(soup, card_data[
            'price'], comment)  # 'contract_deposit', Обеспечение контракта
        card_data['warranty_deposit'] = get_warranty_deposit(soup, card_data[
            'price'], comment)  # 'warranty_deposit', Обеспечение гарантийных обязательств
        card_data['author_name'] = get_author_name(soup, comment)  # 'author_name', Наименование организации
        card_data['author_inn'] = get_author_inn(soup, comment)  # 'author_inn', ИНН
        card_data['author_ogrn'] = get_author_ogrn(soup, comment)  # 'author_ogrn', ОГРН
        card_data['address'] = get_address(soup, comment)  # 'address', Место нахождения
        card_data['author_manager'] = get_author_manager(soup, comment)  # 'author_manager', Контактное лицо
        card_data['author_email'] = get_author_email(soup, comment)  # 'author_email', Электронная почта
        card_data['author_phone'] = get_author_phone(soup, comment)  # 'author_phone', Телефон
        card_data['start_date'] = get_start_date(soup, comment)  # 'start_date', Дата начала срока подачи заявок
        card_data['end_date'] = get_end_date(
            soup, comment)  # 'end_date', Дата и время окончания подачи заявок(по местному времени заказчика)
        card_data['timezone'] = get_timezone(soup, comment)  # 'timezone', Часовой пояс заказчика
        card_data['result_date'] = get_result_date(soup, comment)  # 'result_date', Дата подведения итогов
        comment.write(get_comment(soup, comment))  # 'comment',  # Комментарий к сделке
    except AttributeError:
        msg = f'Failed to make an entry from the purchasing #{hash(card)}'
        logging.error(logger(msg))

    # Пишем данные из раздела документы карточки закупки
    try:
        docs_url = make_part_url(card_data['url'])
        soup = get_soup(get_request(docs_url))
        msg = f'Card #{hash(card)} starts recording by documets url {docs_url}'
        logging.info(logger(msg))
        try:
            card_data['docs'] = get_docs_hrefs223(soup)
        except AttributeError:
            card_data['docs'] = get_docs_hrefs44(soup)
    except AttributeError:
        msg = f'Data for the field "docs" could not be found by url'
        logging.error(logger(msg))
        comment.write('\t• ссылки на документы;')

    card_data['comment'] = comment.comment  # 'comment',  # Комментарий к сделке

    return card_data


def make_part_url(common_url, part='documents') -> str:
    """Функция создает ссылку на другие разделы карточки закупки из общей ссылки,
       по умолчанию на раздел документы

    :param common_url: str -- общая ссылка на карточку закупки
    :param part: str -- требуемый раздел карточки закупки, по умолчанию documents
    :return: str -- ссылка на новвый раздел карточки закупки
    """
    i = common_url.index('common-info.')
    j = common_url.index('.html?')
    return f"{common_url[:i]}{part}{common_url[j:]}"


def get_docs_hrefs223(soup: BeautifulSoup) -> str:
    """Функция возращает ссылки на документы закупки

    :param soup: BeautifulSoup -- объект класса BeautifulSoup
    :return: str -- ссылки на документы
    """
    hr = []
    hrefs = soup.find('div', {'class': 'addingTbl padTop10 padBtm10 autoTh'}) \
        .find_all('a', {'class': 'epz_aware'})

    for href in hrefs:
        hr.append('https://zakupki.gov.ru' + href.get('href'))

    return '\n'.join(hr)


def get_docs_hrefs44(soup: BeautifulSoup) -> str:
    """Функция возращает ссылки на документы закупки

    :param soup: BeautifulSoup -- объект класса BeautifulSoup
    :return: str -- ссылки на документы
    """
    hr = []
    hrefs = soup.find_all('div', {'class': 'attachment row'})

    for href in hrefs:
        hr.append(href.find('span', {'class': 'section__value'})
                  .find('a')
                  .get('href'))

    return '\n'.join(hr)
