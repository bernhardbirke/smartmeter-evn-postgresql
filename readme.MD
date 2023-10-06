## Read Smartmeter Data (Sagemcom Drehstromzähler T210-D) and store in a database.

The script collects a encrypted hex string emmited by the smartmeter via a MBUS Adapter.
The hex string is then decrypted using a personal encryption key and the data extracted via XML.
Finally the data is saved to a defined postgreSQL database.

## Necessary additional Modules

Please refer to `requirements.txt`

pip install python-dotenv

'''
pip install psycopg2 or pip install psycopg2-binary
'''

## Environment Variables

### Configuration for reading the data from the smartmeter

A main_config.yaml file is necessary in the root directory of the project.

### Environment Variables

Create a `.env` file in the root directory of the project with the following contents:

'''
#EVN Schlüssel (as received by the EVN):

EVN_SCHLUESSEL = 4283YOUR3948EVN928175KEY2884

'''

### Database

A database.ini file has to be added to the root of the working directory containing the following specifications:
[postgresql]
host=localhost
database=smartmeter
user=name_of_user
password=Abcd1234

### Necessary hardware to connect to the smartmeter

This python script is based on Michael Reitbauers work.
Further explanations can be found here:
`https://www.michaelreitbauer.at/sagemcom-t210-d-auslesen-smart-meter-evn/`

## postgreSQL

### Initialize

Install PostgreSQL on Windows:
https://www.postgresqltutorial.com/postgresql-getting-started/install-postgresql/

Install PostgreSQL on Linux:
https://www.postgresqltutorial.com/postgresql-getting-started/install-postgresql-linux/

### Create a new database

Log in to the PostgreSQL database server using any client tool such as pgAdmin or psql.

Create a postgreSQL User using the corresponding commands:
CREATE ROLE name_of_user
CREATEDB
LOGIN
PASSWORD 'Abcd1234';

use the following statement to create a new database named smartmeter in the PostgreSQL database server:

CREATE DATABASE smartmeter;

### Connect to your database

switch over to the postgres role using:
sudo -i -u postgres

then start psql.

A database.ini file has to be added to the working directory containing the following specifications:
[postgresql]
host=localhost
database=smartmeter
user=name_of_user
password=Abcd1234

The config.py file loads this information, which is then used in postgresql_tasks.py to establish a connection to the database.

### start the file

using: `python /src/smartmeter/__main__.py` in the project root directory.

### run the python file as a service

for further explanations please refer to:
`https://medium.com/@benmorel/creating-a-linux-service-with-systemd-611b5c8b91d6`

Let’s create a file called
`/etc/systemd/system/smartmeter.service:`

```
[Unit]
Description= smartmeter evn postgresql service
After=multi-user.target


[Service]
Type=simple
Restart=always
RestartSec=1
User=raspi #your user name
ExecStart=/usr/bin/python3 /whole/path/to/script/src/smartmeter/__main__.py
WorkingDirectory=/whole/path/to/script/src/smartmeter

[Install]
WantedBy=multi-user.target

```

#### enable the service via command line

```
sudo systemctl enable smartmeter.service
sudo systemctl start smartmeter.service
```

check if service is running:

```
systemctl list-units --type=service
```

#### sidenote: troubleshooting postgres

Check if pg_lsclusters is running or down.

```
pg_lsclusters
```

if the main cluster is down, check:

```
systemctl status postgresql@13-main.service
```

if the error is something like

```
19:55:40.429 CEST [124777] FATAL:  data directory "/var/lib/postgresql/13/main" has invalid permissions
 19:55:40.429 CEST [124777] DETAIL:  Permissions should be u=rwx (0700) or u=rwx,g=rx (0750).
could not start server
```

Reset Permissions:

```
sudo chmod -R 0700 /var/lib/postgresql/13/main
```

Then restart the cluster:

```
sudo pg_ctlcluster 13 main start
```
