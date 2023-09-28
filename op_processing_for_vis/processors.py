import csv
import gzip
import logging
import os
import shutil
from collections import defaultdict
from itertools import groupby

import paramiko
import utm
from decouple import config
from shapely.geometry import LineString, Point
from utm import OutOfRangeError

from op_processing_for_vis.config import OUTPUT_PATH, TMP_PATH, SOURCE_DATA_PATH
from op_processing_for_vis.utils import get_route_id_info, write_csv, get_period_info, AdatrapSiteManager, angle_between

logger = logging.getLogger(__name__)


def create_stop_file(op_date, stop_path, output_directory):
    route_id_info = get_route_id_info(op_date)
    new_rows = []
    with open(stop_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')

        route_id_not_found_set = set()
        counter_by_route_id = defaultdict(lambda: 0)
        for row in reader:
            direction = 'I' if row['Sentido Servicio'] == 'Ida' else 'R'
            route_id = '{0}{1}{2}'.format(row['Código Usuario'], direction, row['Varian-te'])
            route_id_without_variant = '{0}{1}'.format(row['Código Usuario'], direction)

            if row['Código paradero TS'] == 'POR DEFINIR' or \
                    row['Código  paradero Usuario'] == 'POR DEFINIR' or \
                    row['x'] in ['', '0', 'POR DEFINIR'] or \
                    row['y'] in ['', '0', 'POR DEFINIR']:
                logger.warning('location is not defined for route_id "{0}" in stop "{1}"'.format(
                    route_id, row['Código paradero TS']))
                continue

            x = float(row['x'].replace(',', '.'))
            y = float(row['y'].replace(',', '.'))
            latitude, longitude = utm.to_latlon(x, y, 19, 'H')
            latitude = round(latitude, 8)
            longitude = round(longitude, 8)
            is_bus_station = 1 if row['Operación con Zona Paga'] == 'Zona Paga' else 0
            if route_id in route_id_info:
                new_row = [route_id_info[route_id]['auth_route_code'], route_id_without_variant, row['UN'],
                           counter_by_route_id[route_id], row['Código paradero TS'], row['Código  paradero Usuario'],
                           row['Nombre Paradero'], latitude, longitude, is_bus_station]
                new_rows.append(new_row)
                counter_by_route_id[route_id] += 1
            else:
                route_id_not_found_set.add(route_id)

    logger.info('route ids without translation: {}'.format(len(route_id_not_found_set)))
    logger.info(route_id_not_found_set)

    output_stop_filepath = os.path.join(output_directory, '{0}.stop'.format(op_date))
    header = ['Servicio', 'ServicioUsuario', 'Operador', 'Correlativo', 'Codigo', 'CodigoUsuario', 'Nombre',
              'Latitud', 'Longitud', 'esZP']
    write_csv(output_stop_filepath, header, new_rows)


def create_shape_file(op_date, shape_path, output_directory):
    route_id_info = get_route_id_info(op_date)
    segment_distance = 500  # distance to interpolate
    new_rows = []
    with open(shape_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        next(reader)
        for route_id, group_data in groupby(reader, key=lambda x: x[1]):
            original_point_list = list(map(lambda x: (float(x[2]), float(x[3])), group_data))
            original_shapely_line = LineString(original_point_list)
            simplified_shapely_line = original_shapely_line.simplify(0.5)
            simplified_point_list = list(simplified_shapely_line.coords)

            # get list of points that start a segment of segment_distance
            # omit distance == 0
            current_distance = segment_distance
            interpolated_points = []
            while current_distance < simplified_shapely_line.length:
                new_point = simplified_shapely_line.interpolate(current_distance)
                interpolated_points.append(new_point.coords[0])
                current_distance += segment_distance

            # insert interpolated points in point list
            inserted_points = 0
            index_that_starts_a_segment = []
            for index, current_xy_point in enumerate(simplified_shapely_line.coords[:-1]):
                current_xy_point = Point(current_xy_point)
                next_xy_point = Point(simplified_shapely_line.coords[index + 1])
                if inserted_points == len(interpolated_points):
                    break
                else:
                    current_interpolated_point = Point(interpolated_points[inserted_points])

                # just por simplicity
                # angle variable is the angle created from the lines P2 -> P1 -> P3
                p1 = current_xy_point
                p2 = current_interpolated_point
                p3 = next_xy_point
                angle = angle_between(p1, p2, p3)

                if current_xy_point.distance(current_interpolated_point) <= segment_distance and \
                        next_xy_point.distance(current_interpolated_point) <= segment_distance and \
                        160 < angle < 200:
                    index_to_insert = index + inserted_points + 1
                    simplified_point_list.insert(index_to_insert, interpolated_points[inserted_points])
                    inserted_points += 1
                    index_that_starts_a_segment.append(index_to_insert)

            auth_route_code = route_id_info[route_id]['auth_route_code']
            user_route_code = route_id_info[route_id]['user_route_code']
            operator_code = route_id_info[route_id]['operator_code']
            for index, point_data in enumerate(simplified_point_list):
                is_section_init = 0
                if index in index_that_starts_a_segment:
                    is_section_init = 1
                try:
                    latitude, longitude = utm.to_latlon(point_data[0], point_data[1], 19, 'H')
                    latitude = round(latitude, 6)
                    longitude = round(longitude, 6)
                    new_row = [auth_route_code, is_section_init, latitude, longitude, operator_code, user_route_code]
                    new_rows.append(new_row)
                except OutOfRangeError:
                    logger.warning('Route {0} ({1}) has wrong point ({2}, {3})'.format(
                        auth_route_code, user_route_code, point_data[0], point_data[1]))

    output_shape_filepath = os.path.join(output_directory, '{0}.shape'.format(op_date))
    header = ['Route', 'IsSectionInit', 'Latitude', 'Longitude', 'Operator', 'RouteUser']
    write_csv(output_shape_filepath, header, new_rows)


def create_op_info(op_date, data_path, output_directory):
    period_id_dict = get_period_info(op_date)

    suffix = op_date.replace('-', '')
    file_names = ['Frecuencias_{}.csv'.format(suffix), 'Capacidades_{}.csv'.format(suffix),
                  'Distancias_{}.csv'.format(suffix), 'Velocidades_{}.csv'.format(suffix)]

    transformed_data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
    for file_index, file_name in enumerate(file_names):
        file_path = os.path.join(data_path, file_name)
        with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            # skip first fifth rows
            next(reader)
            row = next(reader)

            # get day limit in file
            work_day_index = row.index('Laboral')
            saturday_index = row.index('Sábado')
            sunday_index = row.index('Domingo')

            next(reader)
            start_period_row = next(reader)[5:]
            end_period_row = next(reader)[5:]

            start_period_row = list(map(lambda x: x.zfill(5) + ':00', start_period_row))
            end_period_row = list(map(lambda x: x.zfill(5) + ':59', end_period_row))

            for row in reader:
                business_unit = row[0]
                direction = row[3]
                user_route_code = row[2]
                auth_route_code = row[1]

                direction_suffix = 'I' if direction == 'Ida' else 'R'
                user_route_code_with_direction = '{0}{1}'.format(user_route_code, direction_suffix)
                auth_route_code_with_direction = '{0}{1}'.format(auth_route_code, direction_suffix)
                meta_row = (user_route_code_with_direction, business_unit, user_route_code, direction,
                            auth_route_code_with_direction)

                aux = work_day_index
                while aux < saturday_index:
                    period_index = aux - work_day_index
                    start_period = start_period_row[period_index]
                    end_period = end_period_row[period_index]
                    period_id = period_id_dict[('0', start_period, end_period)]
                    transformed_data[meta_row]['0'][period_id][(start_period, end_period)].append(row[aux])
                    aux += 1

                aux = saturday_index
                while aux < sunday_index:
                    period_index = aux - work_day_index
                    start_period = start_period_row[period_index]
                    end_period = end_period_row[period_index]
                    period_id = period_id_dict[('1', start_period, end_period)]
                    transformed_data[meta_row]['1'][period_id][(start_period, end_period)].append(row[aux])
                    aux += 1

                aux = sunday_index
                while aux < len(row):
                    period_index = aux - work_day_index
                    start_period = start_period_row[period_index]
                    end_period = end_period_row[period_index]
                    period_id = period_id_dict[('2', start_period, end_period)]
                    transformed_data[meta_row]['2'][period_id][(start_period, end_period)].append(row[aux])
                    aux += 1

    # create rows
    new_rows = []
    for key in transformed_data.keys():
        for day_type in transformed_data[key]:
            for period_id in transformed_data[key][day_type]:
                for period_times in transformed_data[key][day_type][period_id]:
                    values = transformed_data[key][day_type][period_id][period_times]
                    new_row = list(key) + [day_type] + [period_id] + list(period_times) + values + ['']
                    new_rows.append(new_row)

    output_shape_filepath = os.path.join(output_directory, '{0}.opdata'.format(op_date))
    header = ['ServicioSentido', 'UN', 'Servicio', 'Sentido', 'ServicioTS', 'TipoDia', 'PeriodoTS', 'HoraIni',
              'HoraFin', 'Frecuencia', 'Capacidad', 'Distancia', 'Velocidad', '']
    write_csv(output_shape_filepath, header, new_rows)


def upload_op_data_to_server(op_date):
    output_directory = os.path.join(OUTPUT_PATH, op_date)
    file_extensions = ['opdata', 'shape', 'stop']

    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    k = paramiko.RSAKey.from_private_key_file(os.path.join(TMP_PATH, 'private.key'))
    ssh_client.connect(hostname=config('ADATRAP_HOST'), username=config('ADATRAP_SSH_USERNAME'), pkey=k)
    ftp_client = ssh_client.open_sftp()

    for file_extension in file_extensions:
        file_path = os.path.join(output_directory, '{0}.{1}'.format(op_date, file_extension))
        with open(file_path, mode='rb') as file_obj:
            gz_filename = '{0}.{1}.gz'.format(op_date, file_extension)
            gz_file_path = os.path.join(output_directory, gz_filename)
            with gzip.open(gz_file_path, 'wb') as gz_file_obj:
                gz_file_obj.writelines(file_obj)

        ftp_client.put(gz_file_path, '/tmp/{0}'.format(gz_filename))

    ftp_client.close()

    commands = [
        "mv /tmp/*.opdata.gz /var/lib/adatrap/data/opdata/",
        "mv /tmp/*.stop.gz /var/lib/adatrap/data/stop/",
        "mv /tmp/*.shape.gz /var/lib/adatrap/data/shape/",
        "/home/server/fondefVizServer/venv/bin/python /home/server/fondefVizServer/manage.py searchfiles"
    ]

    for command in commands:
        stdin, stdout, stderr = ssh_client.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()  # wait execution
        if exit_status == 0:
            logger.info("command '{}' executed successfully!".format(command))
        else:
            logger.error("Error in execution: '{}'".format(command), exit_status)

    ssh_client.close()


def upload_op_data_to_es(op_date):
    """

    :param op_date:
    :return:
    """
    adatrap_site_manager = AdatrapSiteManager()
    adatrap_site_manager.upload_file('{0}.shape.gz'.format(op_date))
    adatrap_site_manager.upload_file('{0}.stop.gz'.format(op_date))
    adatrap_site_manager.upload_file('{0}.opdata.gz'.format(op_date))


def upload_op_data_dictionary(op_date):
    adatrap_site_manager = AdatrapSiteManager()
    adatrap_site_manager.upload_dictionary(op_date)


def mark_date_as_op_change(op_date):
    adatrap_site_manager = AdatrapSiteManager()
    adatrap_site_manager.mark_date_as_op_change(op_date)


def build_op_data(op_date):
    # create output directory
    output_directory = os.path.join(OUTPUT_PATH, op_date)
    if os.path.exists(output_directory):
        shutil.rmtree(output_directory)
    os.makedirs(output_directory)

    data_path = os.path.join(SOURCE_DATA_PATH, op_date)
    # copy route dictionary
    route_dictionary_filename = 'Diccionario-Servicios_{0}.csv'.format(op_date.replace('-', ''))
    route_dictionary_path = os.path.join(data_path, route_dictionary_filename)
    shutil.copyfile(route_dictionary_path, os.path.join(output_directory, route_dictionary_filename))

    # generate stop file
    stop_filename = 'ConsolidadoParadas_{0}.csv'.format(op_date.replace('-', ''))
    stop_path = os.path.join(data_path, stop_filename)
    create_stop_file(op_date, stop_path, output_directory)

    # generate shape file
    shape_filename = 'ShapeRutas_{0}.csv'.format(op_date.replace('-', ''))
    shape_path = os.path.join(data_path, shape_filename)
    create_shape_file(op_date, shape_path, output_directory)

    # generate op info
    create_op_info(op_date, data_path, output_directory)
