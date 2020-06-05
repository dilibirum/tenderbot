import yaml
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from datetime import datetime
import logging

logging.basicConfig(filename='../../../data/logs/tenderbot.log', level=logging.INFO)  # add filemode="w" to overwrite


class DataBase(object):
    """Класс создает подключение к базе данных

    Атрибуты:
    :param engine: объект sqlalchemy.engine.base.Engine -- движок подключения к БД
    """

    def __init__(self, path):

        def get_db_configs(config_file_path='../configs/dbconfig.yaml'):
            """

            :param config_file_path: str -- путь к конфигурационному файлу с параметрами базы данных,
                                            по умолчанию к папке configs
            :return: dict -- словарь с параметрами базы данных
            """
            with open(config_file_path) as f:
                configs = yaml.safe_load(f)

            return dict(
                database=configs['database'],  # название базы данных
                user=configs['user'],          # имя пользователя
                password=configs['password'],  # пароль
                host=configs['host'],          # адрес сервера
                port=configs['port']           # порт подключения
            )

        def get_engine(config):
            """Функция создает подключение к базе данным

            :param config: dict -- словарь с конфигурацией
            :return: объект sqlalchemy.engine.base.Engine
            """
            connection_string = "postgresql://{}:{}@{}:{}/{}".format(config['user'],
                                                                     config['password'],
                                                                     config['host'],
                                                                     config['port'],
                                                                     config['database'])
            return create_engine(connection_string)

        try:
            self.engine = get_engine(get_db_configs(path))
            msg = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Connection to PostgreSQL DB {get_db_configs(path)['database']} successful"
            print(msg)
            logging.info(msg)
        except OperationalError as e:
            msg = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: The error '{e}' occurred"
            print(msg)
            logging.error(msg)
