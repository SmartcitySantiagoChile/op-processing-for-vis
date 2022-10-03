import csv
import logging
import os
import shutil
from collections import defaultdict
from itertools import groupby

import utm
from shapely.geometry import LineString, Point

from op_processing_for_vis.config import OUTPUT_PATH, TMP_PATH
from op_processing_for_vis.utils import get_route_id_info, write_csv

logger = logging.getLogger(__name__)


def create_stop_file(op_date, data_path, output_directory):
    route_id_info = get_route_id_info(op_date)
    stop_filename = 'ConsolidadoParadas_{0}.csv'.format(op_date.replace('-', ''))
    stop_path = os.path.join(data_path, 'Paraderos', stop_filename)
    new_rows = []
    with open(stop_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')

        route_id_not_found_set = set()
        counter_by_route_id = defaultdict(lambda: 0)
        for row in reader:
            direction = 'I' if row['Sentido Servicio'] == 'Ida' else 'R'
            route_id = '{0}{1}{2}'.format(row['Código Usuario'], direction, row['Varian-te'])
            route_id_without_variant = '{0}{1}'.format(row['Código Usuario'], direction)

            if row['x'] in ['', '0'] or row['y'] in ['', '0']:
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


def create_shape_file(op_date, data_path, output_directory):
    route_id_info = get_route_id_info(op_date)
    segment_distance = 500  # distance to interpolate
    shape_filename = 'ShapeRutas_{0}.csv'.format(op_date.replace('-', ''))
    stop_path = os.path.join(data_path, 'Rutas', shape_filename)
    new_rows = []
    with open(stop_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        next(reader)
        for route_id, group_data in groupby(reader, key=lambda x: x[1]):
            original_point_list = list(map(lambda x: (float(x[2]), float(x[3])), group_data))
            shapely_line = LineString(original_point_list)
            simplified_shapely_line = shapely_line.simplify(0.5)
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
            for index, xy_point in enumerate(simplified_shapely_line.coords):
                distance = simplified_shapely_line.project(Point(xy_point))
                if distance == 0:
                    inserted_points += 1
                    index_that_starts_a_segment.append(0)
                elif distance > inserted_points * segment_distance:
                    index_to_insert = index + inserted_points - 1
                    simplified_point_list.insert(index_to_insert, interpolated_points[inserted_points - 1])
                    inserted_points += 1
                    index_that_starts_a_segment.append(index_to_insert)

            auth_route_code = route_id_info[route_id]['auth_route_code']
            user_route_code = route_id_info[route_id]['user_route_code']
            operator_code = route_id_info[route_id]['operator_code']
            for index, point_data in enumerate(simplified_point_list):
                is_section_init = 0
                if index in index_that_starts_a_segment:
                    is_section_init = 1
                latitude, longitude = utm.to_latlon(point_data[0], point_data[1], 19, 'H')
                latitude = round(latitude, 6)
                longitude = round(longitude, 6)
                new_row = [auth_route_code, is_section_init, latitude, longitude, operator_code, user_route_code]
                new_rows.append(new_row)

    output_shape_filepath = os.path.join(output_directory, '{0}.shape'.format(op_date))
    header = ['Route', 'IsSectionInit', 'Latitude', 'Longitude', 'Operator', 'RouteUser']
    write_csv(output_shape_filepath, header, new_rows)


def create_op_info(op_date):
    pass


def build_op_data(op_date):
    # create output directory
    output_directory = os.path.join(OUTPUT_PATH, op_date)
    if os.path.exists(output_directory):
        shutil.rmtree(output_directory)
    os.makedirs(output_directory)

    data_path = os.path.join(TMP_PATH, '00Entrada', op_date)
    # copy route dictionary
    route_dictionary_filename = 'Diccionario-Servicios_{0}.csv'.format(op_date.replace('-', ''))
    route_dictionary_path = os.path.join(data_path, 'Diccionarios', route_dictionary_filename)
    shutil.copyfile(route_dictionary_path, os.path.join(output_directory, route_dictionary_filename))

    # generate stop file
    create_stop_file(op_date, data_path, output_directory)

    # generate shape file
    create_shape_file(op_date, data_path, output_directory)

    # generate op info
    create_op_info(op_date)
