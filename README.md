# op-processing-for-vis

Small program to generate operation data used by https://adatrap.cl.

The project lets you execute three independent processes:

1. Download operation data from FTP server
2. Generate operation data with the format used by adatrap.cl
3. Transfer data to adatrap.cl and upload it to elasticsearch

## Configuration

To use this project, you need to create a file with the name `.env` in the root directory with the following content:

```
# Notebooks use it to show data in maps. You don't need to provide a value if you don't use notebooks   
MAPBOX_ACCESS_TOKEN=

# FTP data to download operation data files 
FTP_HOST=
FTP_USERNAME=
FTP_PASSWORD=

# information about adatrap server where data is managed
ADATRAP_HOST=adatrap.cl
ADATRAP_SSH_USERNAME=

# user information to log in to the website. These credentials are used to upload operation data to elasticsearch
ADATRAP_SITE_USERNAME=
ADATRAP_SITE_PASSWORD=
```

## Commands

### download-op-data

```
 Usage: main.py download-op-data [OPTIONS] OP_DATE

 Download operation data from FTP server

╭─ Arguments ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    op_date      TEXT  operation program folder name. For instance, 2022-07-02 [default: None] [required]                                                                                                                           │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### process-op-data

```
 Usage: main.py process-op-data [OPTIONS] OP_DATE

 Generate operation data with the format used by adatrap.cl

╭─ Arguments ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    op_date      TEXT  operation program folder name. For instance, 2022-07-02 [default: None] [required]                                                                                                                           │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### upload-op-data

```
 Usage: main.py upload-op-data [OPTIONS] OP_DATE

 Transfer data to adatrap.cl and upload it to elasticsearch

╭─ Arguments ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    op_date      TEXT  operation program folder name. For instance, 2022-07-02 [default: None] [required]                                                                                                                           │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```
