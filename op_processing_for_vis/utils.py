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


def write_csv(filepath, header, rows):
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter='|', quoting=csv.QUOTE_MINIMAL)
        spamwriter.writerow(header)
        for row in rows:
            spamwriter.writerow(row)
