## Necessary additional Modules

pip install python-dotenv

'''
pip install psycopg2
'''

## postgreSQL

### Initialize

Install PostgreSQL on Windows:
https://www.postgresqltutorial.com/postgresql-getting-started/install-postgresql/

Install PostgreSQL on Linux:
https://www.postgresqltutorial.com/postgresql-getting-started/install-postgresql-linux/

### Create a new database

Log in to the PostgreSQL database server using any client tool such as pgAdmin or psql.

Create a postgreSQL Userusing the corresponding commands:
CREATE ROLE name_of_user
CREATEDB
LOGIN
PASSWORD 'Abcd1234';

use the following statement to create a new database named smartmeter in the PostgreSQL database server:

CREATE DATABASE smartmeter;

### Connect to your database

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
