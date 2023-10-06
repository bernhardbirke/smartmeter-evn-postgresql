import sys
import serial
from datetime import datetime
from binascii import unhexlify
from gurux_dlms.GXDLMSTranslator import GXDLMSTranslator
from gurux_dlms.TranslatorOutputType import TranslatorOutputType
from bs4 import BeautifulSoup
from Cryptodome.Cipher import AES
from time import sleep
from typing import Any
import xml.etree.ElementTree as ET
import logging


from src.smartmeter.config import Configuration
from src.smartmeter.postgresql_tasks import PostgresTasks


class SmartmeterToPostgres:
    def __init__(
        self,
        config: Configuration,
        client: PostgresTasks,
    ) -> None:
        self.config_postgres = config.postgresql_config()
        self.config_yaml = config.yaml_config()
        self.config_env = config.env_config()
        self.client = client
        self.data: dict[int] = {}  # processed data - ready to store
        self.ser = None  # serial port
        self.translator = GXDLMSTranslator()

    def get_hex_string(
        self,
    ) -> str:
        """receive encrypted hex string by smartmeter and return parts of the hex string as a dict"""
        encrypted_data = self.ser.read(size=282).hex()
        logging.debug(f"hex string(encrypted_data): {encrypted_data}")
        return encrypted_data

    def split_hex_string(self, encrypted_data: str) -> dict[str]:
        mbusstart = encrypted_data[0:8]
        frame_len = int("0x" + mbusstart[2:4], 16)
        system_titel = encrypted_data[22:38]
        frame_counter = encrypted_data[44:52]
        frame = encrypted_data[52 : 12 + frame_len * 2]
        if (
            mbusstart[0:2] == "68"
            and mbusstart[2:4] == mbusstart[4:6]
            and mbusstart[6:8] == "68"
        ):
            logging.info(f"Incomming Data ok")
            logging.debug(f"mbusstart: {mbusstart}")
            logging.debug(f"dataframe: {frame}")
            logging.debug(f"system_titel: {system_titel}")
            logging.debug(f"frame_counter: {frame_counter}")
            return {
                "mbusstart": mbusstart,
                "frame": frame,
                "system_titel": system_titel,
                "frame_counter": frame_counter,
            }
        else:
            logging.warning(f"Wrong M-Bus Start, restarting", exc_info=True)
            sleep(2.5)
            self.ser.flushOutput()
            self.ser.close()
            self.ser.open()
            return False

    def decrypt_apdu(self, frame, key, system_titel, frame_counter) -> str:
        """decrypt hex string and return decrypted string"""
        frame = unhexlify(frame)
        encryption_key = unhexlify(key)
        init_vector = unhexlify(system_titel + frame_counter)
        cipher = AES.new(encryption_key, AES.MODE_GCM, nonce=init_vector)
        return cipher.decrypt(frame).hex()

    def translate_dlms(self, decrypted_apdu: str) -> None:
        """translate decrypted response"""
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

        try:
            xml = self.translator.pduToXml(
                decrypted_apdu,
            )
            logging.debug(f"xml: {xml}")

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
            logging.exception(f"{err}")

        try:
            if len(momentan) == 2:
                found_lines.append(
                    {"key": "Momentanleistung", "value": momentan[0] - momentan[1]}
                )

            for element in found_lines:
                if element["key"] == "WirkenergieP":
                    self.data["WirkenergieP"] = element["value"]
                if element["key"] == "WirkenergieN":
                    self.data["WirkenergieN"] = element["value"]

                if element["key"] == "MomentanleistungP":
                    self.data["MomentanleistungP"] = element["value"]
                if element["key"] == "MomentanleistungN":
                    self.data["MomentanleistungN"] = element["value"]

                if element["key"] == "SpannungL1":
                    self.data["SpannungL1"] = element["value"] * 0.1
                if element["key"] == "SpannungL2":
                    self.data["SpannungL2"] = element["value"] * 0.1
                if element["key"] == "SpannungL3":
                    self.data["SpannungL3"] = element["value"] * 0.1

                if element["key"] == "StromL1":
                    self.data["StromL1"] = element["value"] * 0.01
                if element["key"] == "StromL2":
                    self.data["StromL2"] = element["value"] * 0.01
                if element["key"] == "StromL3":
                    self.data["StromL3"] = element["value"] * 0.01

                if element["key"] == "Leistungsfaktor":
                    self.data["Leistungsfaktor"] = element["value"] * 0.001

        except BaseException as err:
            logging.exception(f"{err}")

        finally:
            return self.data

    def run(self) -> None:
        """endless loop to gain data and store in the database"""
        self.ser = serial.Serial(
            port=self.config_yaml["port"],
            baudrate=self.config_yaml["baudrate"],
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
        )  # open serial port

        logging.info(f"Application started")
        while True:
            # read data
            encrypted_data = self.get_hex_string()
            encrypted_dict = self.split_hex_string(encrypted_data)
            if encrypted_dict == False:
                continue
            # decrypt data
            apdu = self.decrypt_apdu(
                encrypted_dict["frame"],
                self.config_env["evn_key"],
                encrypted_dict["system_titel"],
                encrypted_dict["frame_counter"],
            )
            logging.debug(f"decrypted apdu: {apdu}")
            if apdu[0:4] != "0f80":
                continue
            # extract data
            self.translate_dlms(apdu)

            if self.config_yaml["printValue"]:
                now = datetime.now()
                print(
                    "\n\t\t*** KUNDENSCHNITTSTELLE ***\n\nOBIS Code\tBezeichnung\t\t\t Wert"
                )
                print(now.strftime("%d.%m.%Y %H:%M:%S"))
                print(
                    "1.0.32.7.0.255\tSpannung L1 (V):\t\t "
                    + str(round(self.data["SpannungL1"], 2))
                )
                print(
                    "1.0.52.7.0.255\tSpannung L2 (V):\t\t "
                    + str(round(self.data["SpannungL2"], 2))
                )
                print(
                    "1.0.72.7.0.255\tSpannung L3 (V):\t\t "
                    + str(round(self.data["SpannungL3"], 2))
                )
                print(
                    "1.0.31.7.0.255\tStrom L1 (A):\t\t\t "
                    + str(round(self.data["StromL1"], 2))
                )
                print(
                    "1.0.51.7.0.255\tStrom L2 (A):\t\t\t "
                    + str(round(self.data["StromL2"], 2))
                )
                print(
                    "1.0.71.7.0.255\tStrom L3 (A):\t\t\t "
                    + str(round(self.data["StromL3"], 2))
                )
                print(
                    "1.0.1.7.0.255\tWirkleistung Bezug [W]: \t "
                    + str(self.data["MomentanleistungP"])
                )
                print(
                    "1.0.2.7.0.255\tWirkleistung Lieferung [W]:\t "
                    + str(self.data["MomentanleistungN"])
                )
                print(
                    "1.0.1.8.0.255\tWirkenergie Bezug [Wh]:\t "
                    + str(self.data["WirkenergieP"])
                )
                print(
                    "1.0.2.8.0.255\tWirkenergie Lieferung [Wh]:\t "
                    + str(self.data["WirkenergieN"])
                )
                print(
                    "-------------\tLeistungsfaktor:\t\t "
                    + str(self.data["Leistungsfaktor"])
                )
                print(
                    "-------------\tWirkleistunggesamt [w]:\t\t "
                    + str(
                        self.data["MomentanleistungP"] - self.data["MomentanleistungN"]
                    )
                )

            # save data to PostgreSQL
            if self.config_yaml["usePostgres"]:
                try:
                    data_id = self.client.insert_smartmeter(
                        self.data["WirkenergieP"],
                        self.data["WirkenergieN"],
                        self.data["MomentanleistungP"],
                        self.data["MomentanleistungN"],
                        self.data["SpannungL1"],
                        self.data["SpannungL2"],
                        self.data["SpannungL3"],
                        self.data["StromL1"],
                        self.data["StromL2"],
                        self.data["StromL3"],
                        self.data["Leistungsfaktor"],
                    )
                    # check if data was saved to the postgresQL Database
                    if data_id is None:
                        logging.exception(f"no Data added to postgresQL Smartmeter")
                        sys.exit(1)
                    else:
                        logging.info(
                            f"data_id: {data_id} was added to postgresQL Smartmeter"
                        )

                except BaseException as err:
                    logging.exception(f"{err}")

                # wait 29 seconds before restarting the loop.
                sleep(29)
