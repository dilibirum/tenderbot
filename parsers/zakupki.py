from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from parsers.utils import get_request
from utils.converter import to_numeric, date_formatter
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
            + '&showLotsInfoHidden=false' \
            + '&sortBy=PUBLISH_DATE' \
            + '&fz44=on' \
            + '&fz223=on' \
            + '&af=on' \
            + '&placingWayList=PO44%2CPOP44%2CZPESMBO%2CZKI44%2COKDI504%2CZKKUI44%2' \
            + 'CZP504%2CZPP504%2CEZP504%2CZKESMBO%2CKESMBO%2COA%2COK111%2COKU111%2COKD' \
            + '111%2CZK111%2CZKB111%2CZP111%2CPO111%2CZP44%2CZPP44%2CPK44%2CPO44%2CPOP44%2CZP44%2CZPP44%2CPR' \
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
        'platform_url',  # Место предоставления
        'price',  # Начальная (максимальная) цена договора
        'tender_deposit',  # Обеспечение заявки
        'contract_deposit',  # Обеспечение контракта
        'costs',  # Себестоимость контракта
        'url',  # URL-закупки на ЕИС в сфере закупок
        'docs',  # URL-ссылка на документацию
        'comment',  # Комментарий к сделке
        'date',  # Дата записи карточки
    ])


def get_card_data(card=None) -> dict:
    """Функция парсит информацию о закупке и записывает с структурированный словарь

    :param card: -- объект BeautifulSoup
    :return: -- словарь со структуированной информацией о закупке
    """
    card_data = create_card()
    msg = f'Card #{hash(card)} starts recording'
    logging.info(logger(msg))

    # пишем данные из карточки закупки
    try:
        card_data['id'] = int(card.find('div', {'class': 'registry-entry__header-mid__number'})
                              .text
                              .strip()
                              .split()[1]
                              .strip())
    except AttributeError:
        msg = 'Data for the field "id" could not be found'
        logging.error(logger(msg))

    try:
        card_data['law'] = card.find('div', {'class': 'registry-entry__header-top__title text-truncate'}) \
            .text \
            .strip() \
            .split()[0] \
            .strip()
    except AttributeError:
        msg = 'Data for the field "law" could not be found'
        logging.error(logger(msg))

    try:
        card_data['url'] = card.find('div', {'class': 'registry-entry__header-mid__number'}) \
            .find('a') \
            .get('href')

    except AttributeError:
        msg = 'Data for the field "url" could not be found'
        logging.error(logger(msg))

    try:
        card_data['price'] = to_numeric(card.find('div', {'class': 'price-block__value'})
                                        .text
                                        .replace('\xa0', '')
                                        .split()[0])
    except AttributeError:
        msg = 'Data for the field "price" could not be found'
        logging.error(logger(msg))

    # пишем данные из по ссылке закупки
    try:
        lot_url = card_data['url']
        soup = get_soup(get_request(lot_url))
        msg = f'Card #{hash(card)} starts recording by url'
        logging.info(logger(msg))

        # читаем таблицу "Общие сведения о закупке"
        try:
            card_data['type'] = soup.find('h2', text='Общие сведения о закупке') \
                .find_next('div') \
                .find('table') \
                .find('tbody') \
                .find_all('tr')[1] \
                .find_all('td')[1] \
                .find('span') \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "type" could not be found'
            logging.error(logger(msg))

        try:
            card_data['description'] = soup.find('h2', text='Общие сведения о закупке') \
                .find_next('div') \
                .find('table') \
                .find('tbody') \
                .find_all('tr')[2] \
                .find_all('td')[1] \
                .find('span') \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "description" could not be found'
            logging.error(logger(msg))

        try:
            card_data['init_date'] = date_formatter(soup.find('h2', text='Общие сведения о закупке')
                                                    .find_next('div')
                                                    .find('table')
                                                    .find('tbody')
                                                    .find_all('tr')[5]
                                                    .find_all('td')[1]
                                                    .text
                                                    .split()[0]
                                                    .strip())
        except AttributeError:
            msg = 'Data for the field "init_date" could not be found'
            logging.error(logger(msg))

        try:
            card_data['platform'] = soup.find('h2', text='Общие сведения о закупке') \
                .find_next('div') \
                .find('table') \
                .find('tbody') \
                .find_all('tr')[7] \
                .find_all('td')[1] \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "platform" could not be found'
            logging.error(logger(msg))

        # читаем таблицу "Заказчик"
        try:
            card_data['author_name'] = soup.find('h2', text='Заказчик') \
                .find_next('div') \
                .find('table') \
                .find_all('tr')[0] \
                .find_all('td')[1] \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "author_name" could not be found'
            logging.error(logger(msg))

        try:
            card_data['author_inn'] = soup.find('h2', text='Заказчик') \
                .find_next('div') \
                .find('table') \
                .find_all('tr')[1] \
                .find_all('td')[1] \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "inn" could not be found'
            logging.error(logger(msg))

        try:
            card_data['author_ogrn'] = soup.find('h2', text='Заказчик') \
                .find_next('div') \
                .find('table') \
                .find_all('tr')[3] \
                .find_all('td')[1] \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "author_ogrn" could not be found'
            logging.error(logger(msg))

        try:
            card_data['address'] = soup.find('h2', text='Заказчик') \
                .find_next('div') \
                .find('table') \
                .find_all('tr')[4] \
                .find_all('td')[1] \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "address" could not be found'
            logging.error(logger(msg))

        # читаем таблицу "Контактная информация"
        try:
            card_data['author_manager'] = soup.find('h2', text='Контактная информация') \
                .find_next('div') \
                .find('table') \
                .find_all('tr')[1] \
                .find_all('td')[1] \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "author_manager" could not be found'
            logging.error(logger(msg))

        try:
            card_data['author_email'] = soup.find('h2', text='Контактная информация') \
                .find_next('div') \
                .find('table') \
                .find_all('tr')[2] \
                .find_all('td')[1] \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "author_email" could not be found'
            logging.error(logger(msg))

        try:
            card_data['author_phone'] = soup.find('h2', text='Контактная информация') \
                .find_next('div') \
                .find('table') \
                .find_all('tr')[3] \
                .find_all('td')[1] \
                .text \
                .strip()
        except AttributeError:
            msg = 'Data for the field "author_phone" could not be found'
            logging.error(logger(msg))

        # читаем таблицу "Порядок проведения процедуры"
        try:
            card_data['start_date'] = date_formatter(soup.find('h2', text='Порядок проведения процедуры')
                                                     .find_next('div')
                                                     .find('table')
                                                     .find_all('tr')[1]
                                                     .find_all('td')[1]
                                                     .text
                                                     .split()[0]
                                                     .strip())
        except AttributeError:
            msg = 'Data for the field "start_date" could not be found'
            logging.error(logger(msg))

        try:
            card_data['end_date'] = date_formatter(soup.find('h2', text='Порядок проведения процедуры')
                                                   .find_next('div')
                                                   .find('table')
                                                   .find_all('tr')[2]
                                                   .find_all('td')[1]
                                                   .text
                                                   .split()[0]
                                                   .strip())
        except AttributeError:
            msg = 'Data for the field "end_date" could not be found'
            logging.error(logger(msg))

        try:
            card_data['timezone'] = soup.find('h2', text='Порядок проведения процедуры') \
                .find_next('div') \
                .find('table') \
                .find_all('tr')[1] \
                .find_all('td')[1] \
                .text \
                .split()[1] \
                .replace('(', '') \
                .replace(')', '') \
                .strip()
        except AttributeError:
            msg = 'Data for the field "timezone" could not be found'
            logging.error(logger(msg))

        try:
            card_data['result_date'] = date_formatter(soup.find('h2', text='Порядок проведения процедуры')
                                                      .find_next('div')
                                                      .find('table')
                                                      .find_all('tr')[6]
                                                      .find_all('td')[1]
                                                      .text
                                                      .split()[0]
                                                      .strip())
        except AttributeError:
            msg = 'Data for the field "result_date" could not be found'
            logging.error(logger(msg))

        # читаем таблицу "Предоставление документации"
        try:
            card_data['platform_url'] = soup.find('h2', text='Предоставление документации') \
                .find_next('div') \
                .find('table') \
                .find_all('tr')[1] \
                .find_all('td')[1] \
                .text \
                .split()[0] \
                .strip()
        except AttributeError:
            msg = 'Data for the field "platform_url" could not be found'
            logging.error(logger(msg))

    except AttributeError:
        msg = f'Failed to make an entry from the purchasing #{hash(card)}'
        logging.error(logger(msg))

    return card_data
