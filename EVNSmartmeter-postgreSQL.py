import json
import sys
import os
import serial
from datetime import datetime
from binascii import unhexlify
from gurux_dlms.GXDLMSTranslator import GXDLMSTranslator
from gurux_dlms.TranslatorOutputType import TranslatorOutputType
from bs4 import BeautifulSoup
from Cryptodome.Cipher import AES
from time import sleep
import xml.etree.ElementTree as ET
import time
import logging

# load postgreSQL database information as a module
from postgresql_tasks import insert_smartmeter

# load environment variables (evn_schluessel)
from dotenv import load_dotenv

load_dotenv()

# config of logging module (DEBUG / INFO / WARNING / ERROR / CRITICAL)
logging.basicConfig(
    level=logging.DEBUG,
    filename="EVNSmartmeter-postgreSQL.log",
    encoding="utf-8",
    filemode="a",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Aktuellen Dateipfad finden und mit config.json erweitern
configFile = os.path.dirname(os.path.realpath(__file__)) + "/config.json"

# Überprüfung ob ein Config Datei vorhanden ist sonst kommt eine Fehlermeldung und beendet das Programm
if not os.path.exists(configFile):
    print("Kein Configfile gefunden bitte eines anlegen.")
    logging.error(f"{configFile} was not found", exc_info=True)
    sys.exit(-1)

# Überprüfung ob die Config gelesen werden kann
if not os.access(configFile, os.R_OK):
    print("ConfigFile " + configFile + " kann nicht gelesen werden!\n\n")
    logging.error(f"{configFile} can not be read", exc_info=True)
    sys.exit(-2)

# Einlesen der Config
config = json.load(open(configFile))

# Überprüfung ob alle Daten in der Config vorhanden sind
neededConfig = ["port", "baudrate", "printValue", "usePostgres"]
for conf in neededConfig:
    if conf not in config:
        print(conf + " Fehlt im Configfile!")
        logging.error(f"{conf} was not found in Configfile", exc_info=True)
        sys.exit(3)


# EVN Schlüssel eingeben zB. "36C66639E48A8CA4D6BC8B282A793BBB"
key = os.getenv("EVN_SCHLUESSEL")

# Aktulle Werte auf Console ausgeben (True | False)
printValue = config["printValue"]

# Postgresql Verwenden (True | False)
usePostgreSQL = config["usePostgres"]

# Comport Config/Init
comport = config["port"]

tr = GXDLMSTranslator()
ser = serial.Serial(
    port=comport,
    baudrate=2400,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
)

# Werte im XML File
octet_string_values = {}
octet_string_values["0100010800FF"] = "WirkenergieP"
octet_string_values["0100020800FF"] = "WirkenergieN"
octet_string_values["0100010700FF"] = "MomentanleistungP"
octet_string_values["0100020700FF"] = "MomentanleistungN"
octet_string_values["0100200700FF"] = "SpannungL1"
octet_string_values["0100340700FF"] = "SpannungL2"
octet_string_values["0100480700FF"] = "SpannungL3"
octet_string_values["01001F0700FF"] = "StromL1"
octet_string_values["0100330700FF"] = "StromL2"
octet_string_values["0100470700FF"] = "StromL3"
octet_string_values["01000D0700FF"] = "Leistungsfaktor"


def evn_decrypt(frame, key, systemTitel, frameCounter):
    frame = unhexlify(frame)
    encryption_key = unhexlify(key)
    init_vector = unhexlify(systemTitel + frameCounter)
    cipher = AES.new(encryption_key, AES.MODE_GCM, nonce=init_vector)
    return cipher.decrypt(frame).hex()


# set a start value for last_time_saved
last_time_saved = time.time()

while True:
    # save the current_time.
    current_time = time.time()
    # elapsed time in ms since the last entry in postgresQL smartmeter database
    elapsed_time = current_time - last_time_saved
    # check if elapsed time exceeds 10 minutes (600000ms) and exit the program if true
    if elapsed_time > 600000:
        logging.exception(
            f"No data was added to the postgresQL smartmeter database within the last 10 minutes"
        )
        sys.exit(1)

    # read data
    daten = ser.read(size=282).hex()
    mbusstart = daten[0:8]
    frameLen = int("0x" + mbusstart[2:4], 16)
    systemTitel = daten[22:38]
    frameCounter = daten[44:52]
    frame = daten[52 : 12 + frameLen * 2]
    if (
        mbusstart[0:2] == "68"
        and mbusstart[2:4] == mbusstart[4:6]
        and mbusstart[6:8] == "68"
    ):
        print(f"Daten ok ({time.ctime()})")
        logging.info(f"Incomming Data ok")
    else:
        print(f"wrong M-Bus Start, restarting ({time.ctime()})")
        logging.warning(f"Wrong M-Bus Start, restarting", exc_info=True)
        sleep(2.5)
        ser.flushOutput()
        ser.close()
        ser.open()

    apdu = evn_decrypt(frame, key, systemTitel, frameCounter)
    if apdu[0:4] != "0f80":
        continue
    try:
        xml = tr.pduToXml(
            apdu,
        )
        # print("xml: ",xml)

        root = ET.fromstring(xml)
        found_lines = []
        momentan = []

        items = list(root.iter())
        for i, child in enumerate(items):
            if child.tag == "OctetString" and "Value" in child.attrib:
                value = child.attrib["Value"]
                if value in octet_string_values.keys():
                    if "Value" in items[i + 1].attrib:
                        if value in ["0100010700FF", "0100020700FF"]:
                            # special handling for momentanleistung
                            momentan.append(int(items[i + 1].attrib["Value"], 16))
                        found_lines.append(
                            {
                                "key": octet_string_values[value],
                                "value": int(items[i + 1].attrib["Value"], 16),
                            }
                        )

    #        print(found_lines)
    except BaseException as err:
        # print("APU: ", format(apdu))
        print("Fehler: ", format(err))
        logging.exception(f"{err}")
        continue

    try:
        if len(momentan) == 2:
            found_lines.append(
                {"key": "Momentanleistung", "value": momentan[0] - momentan[1]}
            )

        for element in found_lines:
            if element["key"] == "WirkenergieP":
                WirkenergieP = element["value"]
            if element["key"] == "WirkenergieN":
                WirkenergieN = element["value"]

            if element["key"] == "MomentanleistungP":
                MomentanleistungP = element["value"]
            if element["key"] == "MomentanleistungN":
                MomentanleistungN = element["value"]

            if element["key"] == "SpannungL1":
                SpannungL1 = element["value"] * 0.1
            if element["key"] == "SpannungL2":
                SpannungL2 = element["value"] * 0.1
            if element["key"] == "SpannungL3":
                SpannungL3 = element["value"] * 0.1

            if element["key"] == "StromL1":
                StromL1 = element["value"] * 0.01
            if element["key"] == "StromL2":
                StromL2 = element["value"] * 0.01
            if element["key"] == "StromL3":
                StromL3 = element["value"] * 0.01

            if element["key"] == "Leistungsfaktor":
                Leistungsfaktor = element["value"] * 0.001

    except BaseException as err:
        print("Fehler: ", format(err))
        logging.exception(f"{err}")
        continue

    if printValue:
        now = datetime.now()
        print("\n\t\t*** KUNDENSCHNITTSTELLE ***\n\nOBIS Code\tBezeichnung\t\t\t Wert")
        print(now.strftime("%d.%m.%Y %H:%M:%S"))
        print("1.0.32.7.0.255\tSpannung L1 (V):\t\t " + str(round(SpannungL1, 2)))
        print("1.0.52.7.0.255\tSpannung L2 (V):\t\t " + str(round(SpannungL2, 2)))
        print("1.0.72.7.0.255\tSpannung L3 (V):\t\t " + str(round(SpannungL3, 2)))
        print("1.0.31.7.0.255\tStrom L1 (A):\t\t\t " + str(round(StromL1, 2)))
        print("1.0.51.7.0.255\tStrom L2 (A):\t\t\t " + str(round(StromL2, 2)))
        print("1.0.71.7.0.255\tStrom L3 (A):\t\t\t " + str(round(StromL3, 2)))
        print("1.0.1.7.0.255\tWirkleistung Bezug [W]: \t " + str(MomentanleistungP))
        print("1.0.2.7.0.255\tWirkleistung Lieferung [W]:\t " + str(MomentanleistungN))
        print("1.0.1.8.0.255\tWirkenergie Bezug [Wh]:\t " + str(WirkenergieP))
        print("1.0.2.8.0.255\tWirkenergie Lieferung [Wh]:\t " + str(WirkenergieN))
        print("-------------\tLeistungsfaktor:\t\t " + str(Leistungsfaktor))
        print(
            "-------------\tWirkleistunggesamt [w]:\t\t "
            + str(MomentanleistungP - MomentanleistungN)
        )

        # PostgreSQL
    if usePostgreSQL:
        try:
            data_id = insert_smartmeter(
                WirkenergieP,
                WirkenergieN,
                MomentanleistungP,
                MomentanleistungN,
                SpannungL1,
                SpannungL2,
                SpannungL3,
                StromL1,
                StromL2,
                StromL3,
                Leistungsfaktor,
            )
            # check if data was saved to the postgresQL Database
            if data_id is None:
                logging.exception(f"no Data added to postgresQL Smartmeter")
                sys.exit(1)
            else:
                logging.info(f"data_id: {data_id} was added to postgresQL Smartmeter")
                # save the current time in ms
                last_time_saved = time.time()
        except BaseException as err:
            print("Fehler: ", format(err))
            logging.exception(f"{err}")
            continue
