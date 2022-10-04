import csv
import os

from op_processing_for_vis.config import TMP_PATH


def get_route_id_info(op_date):
    data_path = os.path.join(TMP_PATH, '00Entrada', op_date)
    stop_filename = 'Diccionario-Servicios_{0}.csv'.format(op_date.replace('-', ''))
    stop_path = os.path.join(data_path, 'Diccionarios', stop_filename)

    route_id_info = dict()
    with open(stop_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            route_id_info[row['Route_Name']] = dict(auth_route_code=row['COD_SINRUT'],
                                                    user_route_code=row['COD_USUARI'],
                                                    operator_code=row['UN'])

    return route_id_info


def get_period_info(op_date):
    data_path = os.path.join(TMP_PATH, '00Entrada', op_date)
    period_filename = 'Diccionario-PeriodosTS_{0}.csv'.format(op_date.replace('-', ''))
    period_path = os.path.join(data_path, 'Diccionarios', period_filename)

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
