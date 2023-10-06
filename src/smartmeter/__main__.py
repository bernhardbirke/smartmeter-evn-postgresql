# from fronius_data_postgresql import FroniusToInflux
import os
import logging

from dev.definitions import ROOT_DIR
from src.smartmeter.postgresql_tasks import PostgresTasks
from src.smartmeter.data import SmartmeterToPostgres
from src.smartmeter.config import Configuration

# instance of Configuration class
config = Configuration()

# instance of PostgresTasks class
client = PostgresTasks()

# initialize logging
loggingFile: str = os.path.join(ROOT_DIR, "smartmeter-postgres.log")

# config of logging module (DEBUG / INFO / WARNING / ERROR / CRITICAL)
logging.basicConfig(
    level=logging.WARNING,
    filename=loggingFile,
    encoding="utf-8",
    filemode="a",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

smartmeter_postg = SmartmeterToPostgres(config, client)

if __name__ == "__main__":
    smartmeter_postg.run()
