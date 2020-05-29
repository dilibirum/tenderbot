from urllib.parse import quote
import requests
from bs4 import BeautifulSoup


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
    :return: str сформированный запрос
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
    :return: список со сслыками
    """
    html = response.text
    soup = BeautifulSoup(html, 'lxml')
    hrefs = []
    cards = soup.find_all('div', {'class': 'row no-gutters registry-entry__form mr-0'})
    for card in cards:
        hrefs.append(card.find('div', {'class': 'registry-entry__header-mid__number'})
                         .find('a')
                         .get('href'))
    return hrefs
