import csv
import logging
import math
import os

import requests
from decouple import config

from op_processing_for_vis.config import SOURCE_DATA_PATH

logger = logging.getLogger(__name__)


def angle_between(p1, p2, p3):
    x1, y1 = p1.x, p1.y
    x2, y2 = p2.x, p2.y
    x3, y3 = p3.x, p3.y
    deg1 = (360 + math.degrees(math.atan2(x1 - x2, y1 - y2))) % 360
    deg2 = (360 + math.degrees(math.atan2(x3 - x2, y3 - y2))) % 360
    return deg2 - deg1 if deg1 <= deg2 else 360 - (deg1 - deg2)


def get_route_id_info(op_date):
    data_path = os.path.join(SOURCE_DATA_PATH, op_date)
    stop_filename = 'Diccionario-Servicios_{0}.csv'.format(op_date.replace('-', ''))
    stop_path = os.path.join(data_path, stop_filename)

    route_id_info = dict()
    with open(stop_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            route_id_info[row['Route_Name']] = dict(auth_route_code=row['COD_SINRUT'],
                                                    user_route_code=row['COD_USUARI'],
                                                    operator_code=row['UN'])

    return route_id_info


def get_period_info(op_date):
    data_path = os.path.join(SOURCE_DATA_PATH, op_date)
    period_filename = 'Diccionario-PeriodosTS_{0}.csv'.format(op_date.replace('-', ''))
    period_path = os.path.join(data_path, period_filename)

    period_id_info = dict()
    with open(period_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            if row['TIPODIA'] == 'LABORAL':
                day_type = '0'
            elif row['TIPODIA'] == 'SABADO':
                day_type = '1'
            elif row['TIPODIA'] == 'DOMINGO':
                day_type = '2'
            start_period = row['HORAINI'].zfill(8)
            end_period = row['HORAFIN'].zfill(8)
            period_id_info[(day_type, start_period, end_period)] = row['ID']

    return period_id_info


def write_csv(filepath, header, rows):
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter='|', quoting=csv.QUOTE_MINIMAL)
        spamwriter.writerow(header)
        for row in rows:
            spamwriter.writerow(row)


class AdatrapSiteManager:

    def __init__(self):
        self.server_name = 'https://{0}'.format(config('ADATRAP_HOST'))
        self.server_username = config('ADATRAP_SITE_USERNAME')
        # urls
        self.LOGIN_URL = '{0}/user/login/'.format(self.server_name)
        self.UPLOAD_FILE_DATA_PAGE = '{0}/admin/datamanager/managerOP/'.format(self.server_name)
        self.UPLOAD_FILE_DATA = '{0}/admin/datamanager/uploadData/'.format(self.server_name)

        self.session = self.get_logged_session()

    def get_logged_session(self):
        payload = {
            'username': self.server_username,
            'password': config('ADATRAP_SITE_PASSWORD'),
            'next': '/admin'
        }

        req_session = requests.Session()
        res = req_session.get(self.LOGIN_URL)
        csrf_token = res.cookies['csrftoken']
        payload['csrfmiddlewaretoken'] = csrf_token

        req_session.headers.update({'referer': self.LOGIN_URL})
        response = req_session.post(self.LOGIN_URL, data=payload, cookies=res.cookies)

        logger.info('se intenta iniciar sesión en "{0}" con usuario "{1}". Resultado: {2}'.format(
            self.server_name, self.server_username, response.status_code))

        return req_session

    def upload_file(self, filename):
        payload = {
            'fileName': filename
        }

        self.session.headers.update({
            'referer': self.UPLOAD_FILE_DATA
        })

        response = self.session.post(self.UPLOAD_FILE_DATA, data=payload)
        logger.info('Resultado de envío: {0}'.format(response.status_code))
