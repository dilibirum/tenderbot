from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
import numpy as np
import time
from parsers.utils import get_request
from utils.converter import to_numeric, date_formatter, datetime_formatter
from utils.collecting import logger
import logging

logging.basicConfig(filename='../data/logs/tenderbot.log', level=logging.INFO)  # add filemode="w" to overwrite


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


def get_id(soup: BeautifulSoup) -> int:
    """Функция находит реестровый номер извещения

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
    return result


def get_law(soup: BeautifulSoup) -> str:
    """Функция находит федеральный закон

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
    return result


def get_url(soup: BeautifulSoup) -> str:
    """Функция находит URL-закупки на ЕИС в сфере закупок

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
    return result


def get_price(soup: BeautifulSoup) -> float:
    """Функция находит начальную (максимальную) цену договора

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
    return result


def get_type(soup: BeautifulSoup) -> str:
    """Функция находит способ размещения закупки

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
    return result


def get_description(soup: BeautifulSoup) -> str:
    """Функция находит наименование закупки

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
    return result


def get_init_date(soup: BeautifulSoup) -> str:
    """Функция находит дату размещения извещения

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
    return result


def get_platform(soup: BeautifulSoup) -> str:
    """Функция находит наименование электронной площадки

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
    return result


def get_platform_url(soup: BeautifulSoup) -> str:
    """Функция находит адрес электронной площадки

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
    return result


def get_tender_deposit(soup: BeautifulSoup):
    """Функция находит обеспечение заявки

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
    return result


def get_contract_deposit(soup: BeautifulSoup, price: float) -> float:
    """Функция находит обеспечение контракта

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
    return result


def get_warranty_deposit(soup: BeautifulSoup, price: float) -> float:
    """Функция находит обеспечение гарантийных обязательств

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
    return result


def get_author_name(soup: BeautifulSoup) -> str:
    """Функция находит наименование организации

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
    return result


def get_author_inn(soup: BeautifulSoup) -> str:
    """Функция находит ИНН

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
    return result


def get_author_ogrn(soup: BeautifulSoup) -> str:
    """Функция находит ОГРН

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
    return result


def get_address(soup: BeautifulSoup) -> str:
    """Функция находит место нахождения

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
    return result


def get_author_manager(soup: BeautifulSoup) -> str:
    """Функция находит контактное лицо

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
    return result


def get_author_email(soup: BeautifulSoup) -> str:
    """Функция находит электронную почту

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
    return result


def get_author_phone(soup: BeautifulSoup) -> str:
    """Функция находит телефон

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
    return result


def get_start_date(soup: BeautifulSoup) -> str:
    """Функция находит дату начала срока подачи заявок

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
    return result


def get_end_date(soup: BeautifulSoup) -> str:
    """Функция находит дату и время окончания подачи заявок(по местному времени заказчика)

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
    return result


def get_timezone(soup: BeautifulSoup) -> str:
    """Функция находит часовой пояс заказчика

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
    return result


def get_result_date(soup: BeautifulSoup) -> str:
    """Функция находит дату подведения итогов

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
    return result


# TODO: 30 мая 2020 года изменилась структура сайта!!!
def get_card_data(card=None) -> dict:
    """Функция парсит информацию о закупке и записывает с структурированный словарь

    :param card: -- объект BeautifulSoup
    :return: -- словарь со структуированной информацией о закупке
    """
    card_data = create_card()
    msg = f'Card #{hash(card)} starts recording'
    logging.info(logger(msg))
    card_data['time'] = time.time()

    # пишем данные из карточки закупки
    card_data['id'] = get_id(card)  # 'id', Реестровый номер извещения
    card_data['law'] = get_law(card)  # 'law', Федеральный закон
    card_data['url'] = get_url(card)  # 'url', URL-закупки на ЕИС в сфере закупок
    card_data['price'] = get_price(card)  # 'price', Начальная (максимальная) цена договора

    # пишем данные из по ссылке закупки, для 44-ФЗ и 223-ФЗ представление страницы с данными различается
    try:
        lot_url = card_data['url']
        soup: BeautifulSoup = get_soup(get_request(lot_url))
        msg = f'Card #{hash(card)} starts recording by url'
        logging.info(logger(msg))

        card_data['type'] = get_type(soup)  # 'type', Способ размещения закупки
        card_data['description'] = get_description(soup)  # 'description', Наименование закупки
        card_data['init_date'] = get_init_date(soup)  # 'init_date', Дата размещения извещения
        card_data['platform'] = get_platform(soup)  # 'platform', Наименование электронной площадки
        card_data['platform_url'] = get_platform_url(soup)  # 'platform_url', Адрес электронной площадки
        card_data['tender_deposit'] = get_tender_deposit(soup)  # 'tender_deposit', Обеспечение заявки
        card_data['contract_deposit'] = get_contract_deposit(soup, card_data[
            'price'])  # 'contract_deposit', Обеспечение контракта
        card_data['warranty_deposit'] = get_warranty_deposit(soup, card_data[
            'price'])  # 'warranty_deposit', Обеспечение гарантийных обязательств
        card_data['author_name'] = get_author_name(soup)  # 'author_name', Наименование организации
        card_data['author_inn'] = get_author_inn(soup)  # 'author_inn', ИНН
        card_data['author_ogrn'] = get_author_ogrn(soup)  # 'author_ogrn', ОГРН
        card_data['address'] = get_address(soup)  # 'address', Место нахождения
        card_data['author_manager'] = get_author_manager(soup)  # 'author_manager', Контактное лицо
        card_data['author_email'] = get_author_email(soup)  # 'author_email', Электронная почта
        card_data['author_phone'] = get_author_phone(soup)  # 'author_phone', Телефон
        card_data['start_date'] = get_start_date(soup)  # 'start_date', Дата начала срока подачи заявок
        card_data['end_date'] = get_end_date(
            soup)  # 'end_date', Дата и время окончания подачи заявок(по местному времени заказчика)
        card_data['timezone'] = get_timezone(soup)  # 'timezone', Часовой пояс заказчика
        card_data['result_date'] = get_result_date(soup)  # 'result_date', Дата подведения итогов
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
        msg = f'Data for the field "docs" could not be found by url {docs_url}'
        logging.error(logger(msg))

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
