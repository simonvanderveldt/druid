""" Contains all crow device related functionality """
import logging
import time

import serial
from serial.tools import list_ports


logger = logging.getLogger(__name__)

class Crow():
    """ Crow device, takes care of connecting and communicating with crow """
    def __init__(self):
        self.__serial = None

    @property
    def _serial(self):
        """ Lazy loaded serial connection to crow """
        if not self.__serial:
            for item in list_ports.comports():
                logger.debug("Trying serial port %s - device %s", item[0], item[2])
                if "USB VID:PID=0483:5740" in item[2]:
                    port = item[0]
                    logger.info("Found crow on serial port %s", port)
                    try:
                        self.__serial = serial.Serial(port, 115200, timeout=0.1)
                        break
                    except serial.SerialException as err:
                        raise ConnectionError(f"Can't open serial port {port}, {err}")
            else:
                raise FileNotFoundError("Can't find crow")
        return self.__serial

    def close(self):
        """ Close the serial connection """
        self._serial.close()

    def read(self):
        """ Read output from crow """
        output = self._serial.read(10000) or None
        if output:
            return output.decode("ascii").split("\n\r")
        return None

    def write(self, data):
        """ Write string to crow """
        self._serial.write(data.encode())

    def print(self):
        """ Request crow to print the currently loaded script """
        logger.info("Asking crow to print the current script")
        self.write("^^p")
        return self.read()

    def upload(self, data):
        """ Send a script to crow and write it to memory """
        logger.info("Uploading to crow")
        self.write("^^s")
        time.sleep(0.2) # wait for allocation
        for line in data:
            self.write(line)
            time.sleep(0.002) # fix os x crash?
        time.sleep(0.1) # wait for upload to complete
        self.write("^^w")

    def execute(self, data):
        """ Send a script to crow and execute it """
        logger.info("Running script on crow")
        self.write("^^s")
        time.sleep(0.2) # wait for allocation
        for line in data:
            self.write(line)
            time.sleep(0.002) # fix os x crash?
        time.sleep(0.01)
        self.write("^^e")
