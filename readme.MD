## Necessary additional Modules

pip install python-dotenv

'''
pip install psycopg2 or pip install psycopg2-binary
'''

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

The config.py file loads this information, which is then used in postgresl_tasks.py to establish a connection to the database.

### Connect to the smartmeter and read the data

The python routine to connect to the smartmeter and read the data is based on Michael Reitbauers work.
Further explanations can be found here:
https://www.michaelreitbauer.at/sagemcom-t210-d-auslesen-smart-meter-evn/

### start the file

using: python3 EVNSmartmeter-postgreSQL.py in the project directory.

### troubleshooting postgres

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
