import ftplib
import logging

import typer
from decouple import config

from op_processing_for_vis.config import TMP_PATH
from op_processing_for_vis.ftp import download_ftp_tree
from op_processing_for_vis.processors import build_op_data, mark_date_as_op_change, upload_op_data_to_server, \
    upload_op_data_to_es, upload_op_data_dictionary

app = typer.Typer()

logger = logging.getLogger(__name__)


@app.command()
def download_op_data(
        op_date: str = typer.Argument(..., help='operation program folder name. For instance, 2022-07-02')):
    """
    Download operation data from FTP server
    """
    logger.info('downloading files ...')
    host = config('FTP_HOST')
    username = config('FTP_USERNAME')
    password = config('FTP_PASSWORD')
    remote_dir = '00Entrada/01_FichaServicios/{0}'.format(op_date)
    ftp = ftplib.FTP(host, username, password)
    pattern = None
    download_ftp_tree(ftp, remote_dir, TMP_PATH, pattern=pattern, overwrite=True, guess_by_extension=True)

    logger.info('done!')


@app.command()
def process_op_data(op_date: str = typer.Argument(..., help='operation program folder name. For instance, 2022-07-02')):
    """
    Generate operation data with the format used by adatrap.cl
    """
    build_op_data(op_date)


@app.command()
def upload_op_data(op_date: str = typer.Argument(..., help='operation program folder name. For instance, 2022-07-02')):
    """
    Transfer data to adatrap.cl and upload it to elasticsearch
    """
    # send files to server
    upload_op_data_to_server(op_date)

    # upload files to elasticsearch
    upload_op_data_to_es(op_date)

    # upload route dictionary
    upload_op_data_dictionary(op_date)

    # mark date as operation program change
    mark_date_as_op_change(op_date)


@app.command()
def run_all_processes(
        op_date: str = typer.Argument(..., help='operation program folder name. For instance, 2022-07-02')):
    """
    download, process and upload operation program data
    :param op_date: date where operation program starts to work
    """
    download_op_data(op_date)
    process_op_data(op_date)
    upload_op_data(op_date)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app()
