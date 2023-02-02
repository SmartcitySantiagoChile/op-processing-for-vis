import os

PROJECT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OUTPUT_PATH = os.path.join(PROJECT_PATH, 'output')
TMP_PATH = os.path.join(PROJECT_PATH, 'tmp')

SOURCE_DATA_PATH = os.path.join(TMP_PATH, '00Entrada', '01_FichaServicios')
