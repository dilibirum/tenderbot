from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
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
    # 'id', Реестровый номер извещения
    try:
        card_data['id'] = int(card.find('div', {'class': 'registry-entry__header-mid__number'})
                              .text
                              .strip()
                              .split()[1]
                              .strip())
    except AttributeError:
        msg = 'Data for the field "id" could not be found'
        logging.error(logger(msg))

    # 'law', Федеральный закон
    try:
        card_data['law'] = card.find('div', {'class': 'registry-entry__header-top__title text-truncate'}) \
            .text \
            .strip() \
            .split()[0] \
            .strip()
    except AttributeError:
        msg = 'Data for the field "law" could not be found'
        logging.error(logger(msg))

    # 'url', URL-закупки на ЕИС в сфере закупок
    try:
        _url = card.find('div', {'class': 'registry-entry__header-mid__number'}) \
            .find('a') \
            .get('href')
        if 'https://zakupki.gov.ru' not in _url:
            _url = f"https://zakupki.gov.ru{_url}"
        card_data['url'] = _url

    except AttributeError:
        msg = 'Data for the field "url" could not be found'
        logging.error(logger(msg))

    # 'price', Начальная (максимальная) цена договора
    try:
        card_data['price'] = to_numeric(card.find('div', {'class': 'price-block__value'})
                                        .text
                                        .replace('\xa0', '')
                                        .split()[0])
    except AttributeError:
        msg = 'Data for the field "price" could not be found'
        logging.error(logger(msg))

    # пишем данные из по ссылке закупки, для 44-ФЗ и 223-ФЗ представление страницы с данными различается
    try:
        lot_url = card_data['url']
        soup: BeautifulSoup = get_soup(get_request(lot_url))
        msg = f'Card #{hash(card)} starts recording by url'
        logging.info(logger(msg))

        # TODO: если новая структура HTML-страницы станет преимущественной, то блоки try – поменять местами
        # 'type', Способ размещения закупки
        try:
            card_data['type'] = soup.find('td', text='Способ размещения закупки') \
                .find_next('td') \
                .text \
                .strip()
        except AttributeError:
            try:
                card_data['type'] = soup.find('span', {'class': 'section__title'},
                                              text='Способ определения поставщика (подрядчика, исполнителя)') \
                    .find_next('span', {'class': 'section__info'}) \
                    .text
            except AttributeError:
                msg = 'Data for the field "type" could not be found'
                logging.error(logger(msg))

        # 'description', Наименование закупки
        try:
            card_data['description'] = soup.find('td', text='Наименование закупки') \
                .find_next('td') \
                .text \
                .strip()
        except AttributeError:
            try:
                card_data['description'] = soup.find('span', {'class': 'cardMainInfo__title'}, text='Объект закупки') \
                    .find_next('span', {'class': 'cardMainInfo__content'}) \
                    .text \
                    .strip()
            except AttributeError:
                msg = 'Data for the field "description" could not be found'
                logging.error(logger(msg))

        # 'init_date', Дата размещения извещения
        try:
            card_data['init_date'] = date_formatter(soup.find('td', text='Дата размещения извещения')
                                                    .find_next('td')
                                                    .text
                                                    .split()[0]
                                                    .strip())
        except AttributeError:
            try:
                card_data['init_date'] = datetime_formatter(soup.find('span', {'class': 'cardMainInfo__title'},
                                                                      text='Размещено в ЕИС')
                                                            .find_next('span', {'class': 'cardMainInfo__content'})
                                                            .text
                                                            .strip())
            except AttributeError:
                msg = 'Data for the field "init_date" could not be found'
                logging.error(logger(msg))

        # 'platform', Наименование электронной площадки
        try:
            card_data['platform'] = soup.find('td', text='Наименование электронной площадки в ' +
                                                         'информационно-телекоммуникационной сети «Интернет»') \
                .find_next('td') \
                .text \
                .strip()
        except AttributeError:
            try:
                card_data['platform'] = soup.find('span', {'class': 'section__title'},
                                                  text='Наименование электронной площадки в ' +
                                                       'информационно-телекоммуникационной сети "Интернет"') \
                    .find_next('span', {'class': 'section__info'}) \
                    .text \
                    .strip()
            except AttributeError:
                msg = 'Data for the field "platform" could not be found'
                logging.error(logger(msg))

        # 'platform_url', Адрес электронной площадки
        try:
            card_data['platform_url'] = soup.find('td', text='Адрес электронной площадки в ' +
                                                             'информационно-телекоммуникационной сети ' +
                                                             '«Интернет»') \
                .find_next('td') \
                .text \
                .strip()
        except AttributeError:
            try:
                card_data['platform_url'] = soup.find('span', {'class': 'section__title'},
                                                      text='Адрес электронной площадки в ' +
                                                           'информационно-телекоммуникационной сети "Интернет"') \
                    .find_next('span', {'class': 'section__info'}) \
                    .text \
                    .strip()
            except AttributeError:
                msg = 'Data for the field "platform_url" could not be found'
                logging.error(logger(msg))

        # 'tender_deposit', Обеспечение заявки
        try:
            card_data['tender_deposit'] = soup.find('td', text='Обеспечение заявки') \
                .find_next('td') \
                .text \
                .strip()
        except AttributeError:
            try:
                card_data['tender_deposit'] = to_numeric(''.join(soup.find('span', {'class': 'section__title'},
                                                                           text='Размер обеспечения заявки')
                                                                 .find_next('span', {'class': 'section__info'})
                                                                 .text
                                                                 .split('\xa0')[:-1])
                                                         .strip())
            except AttributeError:
                msg = 'Data for the field "tender_deposit" could not be found'
                logging.error(logger(msg))

        # 'contract_deposit', Обеспечение контракта
        try:
            raw_data = ''.join(soup.find('span', {'class': 'section__title'},
                                                            text='Размер обеспечения исполнения контракта')
                                                  .find_next('span', {'class': 'section__info'})
                                                  .text
                                                  .split()[0]) \
                .strip()

            contract_deposit = to_numeric(raw_data)
            if contract_deposit < 1:
                contract_deposit = card_data['price'] * contract_deposit
            card_data['contract_deposit'] = contract_deposit

        except AttributeError:
            msg = 'Data for the field "contract_deposit" could not be found'
            logging.error(logger(msg))

        # 'warranty_deposit', Обеспечение гарантийных обязательств
        try:
            warranty_deposit = to_numeric(''.join(soup.find('span', {'class': 'section__title'},
                                                            text='Размер обеспечения гарантийных обязательств')
                                                  .find_next('span', {'class': 'section__info'})
                                                  .text
                                                  .split('\xa0')[:-1])
                                          .strip())
            if warranty_deposit < 1:
                warranty_deposit = card_data['price'] * warranty_deposit
            card_data['warranty_deposit'] = warranty_deposit
        except AttributeError:
            msg = 'Data for the field "warranty_deposit" could not be found'
            logging.error(logger(msg))

        # 'author_name', Наименование организации
        try:
            card_data['author_name'] = soup.find('td', text='Наименование организации') \
                .find_next('td') \
                .text \
                .strip()
        except AttributeError:
            try:
                card_data['author_name'] = soup.find('span', {'class': 'section__title'},
                                                     text='Организация, осуществляющая размещение') \
                    .find_next('span', {'class': 'section__info'}) \
                    .text \
                    .strip()
            except AttributeError:
                msg = 'Data for the field "author_name" could not be found'
                logging.error(logger(msg))

        # 'author_inn', ИНН
        try:
            card_data['author_inn'] = soup.find('td', text='ИНН') \
                .find_next('td') \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "inn" could not be found'
            logging.error(logger(msg))

        # 'author_ogrn', ОГРН
        try:
            card_data['author_ogrn'] = soup.find('td', text='ОГРН') \
                .find_next('td') \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "author_ogrn" could not be found'
            logging.error(logger(msg))

        # 'address', Место нахождения
        try:
            card_data['address'] = soup.find('td', text='Место нахождения') \
                .find_next('td') \
                .text \
                .strip()
        except AttributeError:
            try:
                card_data['address'] = soup.find('span', {'class': 'section__title'},
                                                 text='Почтовый адрес') \
                    .find_next('span', {'class': 'section__info'}) \
                    .text \
                    .strip()
            except AttributeError:
                msg = 'Data for the field "address" could not be found'
                logging.error(logger(msg))

        # 'author_manager', Контактное лицо
        try:
            card_data['author_manager'] = soup.find('td', text='Контактное лицо') \
                .find_next('td') \
                .text \
                .strip()
        except AttributeError:
            try:
                card_data['author_manager'] = soup.find('span', {'class': 'section__title'},
                                                        text='Ответственное должностное лицо') \
                    .find_next('span', {'class': 'section__info'}) \
                    .text \
                    .strip()
            except AttributeError:
                msg = 'Data for the field "author_manager" could not be found'
                logging.error(logger(msg))

        # 'author_email', Электронная почта
        try:
            card_data['author_email'] = soup.find('td', text='Электронная почта') \
                .find_next('td') \
                .text \
                .strip()
        except AttributeError:
            try:
                card_data['author_email'] = soup.find('span', {'class': 'section__title'},
                                                      text='Адрес электронной почты') \
                    .find_next('span', {'class': 'section__info'}) \
                    .text \
                    .strip()
            except AttributeError:
                msg = 'Data for the field "author_email" could not be found'
                logging.error(logger(msg))

        # 'author_phone', Телефон
        try:
            card_data['author_phone'] = soup.find('td', text='Телефон') \
                .find_next('td') \
                .text \
                .strip()
        except AttributeError:
            try:
                card_data['author_phone'] = soup.find('span', {'class': 'section__title'},
                                                      text='Номер контактного телефона') \
                    .find_next('span', {'class': 'section__info'}) \
                    .text \
                    .strip()
            except AttributeError:
                msg = 'Data for the field "author_phone" could not be found'
                logging.error(logger(msg))

        # 'start_date', Дата начала срока подачи заявок
        try:
            card_data['start_date'] = date_formatter(soup
                                                     .find('td', text='Дата начала срока подачи заявок')
                                                     .find_next('td')
                                                     .text
                                                     .split()[0]
                                                     .strip())
        except AttributeError:
            try:
                card_data['start_date'] = datetime_formatter(soup.find('span', {'class': 'section__title'},
                                                                       text='Дата и время начала срока подачи заявок')
                                                             .find_next('span', {'class': 'section__info'})
                                                             .text
                                                             .strip())
            except AttributeError:
                msg = 'Data for the field "start_date" could not be found'
                logging.error(logger(msg))

        # 'end_date', Дата и время окончания подачи заявок(по местному времени заказчика)
        try:
            card_data['end_date'] = date_formatter(soup
                                                   .find('span', text='(по местному времени заказчика)')
                                                   .find_next('td')
                                                   .text
                                                   .split()[0]
                                                   .strip())
        except AttributeError:
            try:
                card_data['end_date'] = datetime_formatter(soup.find('span', {'class': 'section__title'},
                                                                     text='Дата и время окончания срока подачи заявок')
                                                           .find_next('span', {'class': 'section__info'})
                                                           .text
                                                           .strip())
            except AttributeError:
                msg = 'Data for the field "end_date" could not be found'
                logging.error(logger(msg))

        # 'timezone', Часовой пояс заказчика
        try:
            card_data['timezone'] = soup.find('td', text='Дата начала срока подачи заявок') \
                .find_next('td') \
                .text \
                .split()[1] \
                .replace('(', '') \
                .replace(')', '') \
                .strip()
        except AttributeError:
            msg = 'Data for the field "timezone" could not be found'
            logging.error(logger(msg))

        # 'result_date', Дата подведения итогов
        try:
            card_data['result_date'] = date_formatter(soup
                                                      .find('td', text='Дата подведения итогов')
                                                      .find_next('td')
                                                      .text
                                                      .split()[0]
                                                      .strip())
        except AttributeError:
            try:
                card_data['result_date'] = datetime_formatter(soup.find('span', {'class': 'section__title'},
                                                                        text="""
                            Дата и время рассмотрения и оценки первых частей заявок
                        """)
                                                              .find_next('span', {'class': 'section__info'})
                                                              .text
                                                              .strip())
            except AttributeError:
                msg = 'Data for the field "result_date" could not be found'
                logging.error(logger(msg))

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
