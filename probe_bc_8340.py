#!/usr/bin/env python
# coding=utf8
# -*- coding: utf8 -*-
# vim: set fileencoding=utf8 :
# ----------------------------------------------------------------------
#  Copyright (c) 1995-2017, Ecometer s.n.c.
#  Author: Paolo Saudin.
#
#  Desc : bc-electronics instrument support functions
#  File : probe_bc_8340.py
#
#  Date : 2017-08-12
#
#  Install: sudo pip3 install pyserial | pip install pyserial
# ----------------------------------------------------------------------
""" http://www.bc-electronics.it/ita/home.php
    livello, temperatura, conducibilità, pH
    livello, temperatura, conducibilità, pH, redox
"""

""" Imports
"""
import sys
import os
import logging
import logging.config
import time
import re
import serial
from datetime import datetime
from serial import SerialException

if __name__ == '__main__':
    sys.exit(1)

#- ----------------------------------------------------------------------------
#- classes
#- ----------------------------------------------------------------------------
# main client class - comm port and baud rate
class Client:
    """ Constants
    """
    CR   = "\r"
    CRLF = "\r\n"
    LF   = "\n"
    TAB  = "\t"
    SEMICOLON = ";"

    """ Init
    """
    def __init__(self, conf, data_path):
        logging.getLogger('')
        logging.debug("Client init")

        self.conf = conf
        self.data_path = data_path
        self.ser = serial.Serial()

    def __del__(self):
        self.serial_close()
        logging.debug("Client delete")


    """ SERIAL STUFF
    """

    """ Get main gamma object and open serial port
    """
    def serial_open(self):
        logging.debug("Function serial_open()")

        if not self.ser or not self.ser.isOpen():
            try :
                logging.debug("Opening serial port [%s@%s]" % (self.conf['port'], self.conf['baudrate']))
                self.ser = serial.Serial(
                    port     = self.conf['port'],
                    baudrate = self.conf['baudrate'],
                    parity   = self.conf['parity'],
                    stopbits = self.conf['stopbits'],
                    bytesize = self.conf['bytesize'],
                    timeout  = 0 # non-blocking mode (return immediately on read)
               )
                #print self.ser.isOpen()
                # confirm which port was really used
                logging.verbose("Serial port %s" % (self.ser.portstr))
                return True

            except SerialException as e:
                logging.critical("An exception was encountered in serial_open(): %s" % str(e))
                return False

            except Exception as e:
                logging.critical("An exception was encountered in serial_open(): %s" % str(e))
                return False
        else:
            logging.warning("Serial port already opened")
            return True

    """ Close serial port and wipe out main object
    """
    def serial_close(self):
        logging.debug("Function serial_close()")

        if self.ser.isOpen():
            self.ser.close()
            self.ser = None
            logging.verbose("Serial port closed.")
        else:
            logging.warning("Serial port not opened")

        return True

    """ Read value from instrument
    """
    def serial_get_response(self, command):
        logging.verbose("Function serial_get_response()")
        logging.verbose("Command %s", command)
        try:
            # check if port is opened
            if not self.ser.isOpen():
                logging.warning("Serial port not opened")
                return ''

            # flush input buffer, discarding all its contents
            logging.verbose("Flush serial input")
            self.ser.flushInput()
            # flush output buffer, aborting current output
            # and discard all that is in buffer
            logging.verbose("Flush serial output")
            self.ser.flushOutput()

            # write data
            logging.verbose("Sending serial command TX[%s]" % str(command))
            command = command + self.CR
            if (sys.version_info > (3, 0)):
                # Python 3 code in this block
                self.ser.write(command.encode())
            else:
                # Python 2 code in this block
                self.ser.write(command)
                
            self.ser.flush()

            logging.verbose("Reading data ...")
            # timeout 1 seconds from now
            timeout = time.time() + 2
            response = ''
            regexpr = '(.*)'+self.CRLF
            while True:
                buffer_data = self.ser.read(1024)
                # data check
                if buffer_data:
                    if (sys.version_info > (3, 0)):
                        # Python 3 code in this block
                        response = response + buffer_data.decode('latin1')
                    else:
                        # Python 2 code in this block
                        response = response + buffer_data

                    # analyse data
                    matches = re.match(regexpr, response)
                    if matches:
                        response = matches.group(1)
                        logging.verbose("Response RX[%s]" % str(response))
                        return response

                # timeout check
                if time.time() > timeout:
                    logging.warning("Serial timeout")
                    return ''

        except Exception as e:
            logging.critical("An exception was encountered in serial_get_response(): %s" % str(e))
            return ''




    """ PROBE STUFF
    """

    """ Wake up probe
    """
    def probe_wakeup(self, id):
        logging.debug("Function probe_wakeup()")
        try:
            # get group values
            for _ in range(3):
                response = self.serial_get_response(id+'A')
                if response != '':
                    logging.verbose("Function probe_wakeup() - Exit")
                    return True
                    break

                time.sleep(0.1)

            logging.warning("Probe does not respond")
            return False

        except Exception as e:
            logging.critical("An exception was encountered in probe_wakeup(): %s" % str(e))
            return False


    """ Switch off probe
    """
    def probe_switch_off(self):
        logging.debug("Function probe_switch_off()")
        try:
            response = self.serial_get_response('00O')
            logging.debug("-> response %s" % response)
            response = self.serial_get_response('00I')
            logging.verbose("-->>-->> response %s" % response)

        except Exception as e:
            logging.critical("An exception was encountered in probe_switch_off(): %s" % str(e))
            return None



    """ PROBE COMMON FUNCTIONS
    """

    """ Get bcc code
    """
    def __get_bcc(self, record):
        logging.debug("Function __get_bcc() - record: %s" % record)
        try:
            bcc = 0
            for char in record:
                bcc = bcc ^ ord(char)

            logging.verbose("Bcc: %s" % bcc)
            # split into 2 nibbles
            high, low = bcc >> 4, bcc & 0x0F
            logging.verbose("High: %s, low: %s" % (high, low))
            #print(hex(bcc), hex(high), hex(low))
            #print('{:X}'.format(high), '{:X}'.format(low))
            # convert to hexadecimal, withot \x
            bcc = '{:X}'.format(high) + '{:X}'.format(low)
            logging.debug("Bcc: %s" % bcc)
            return bcc

        except Exception as e:
            logging.critical("An exception was encountered in __get_bcc(): %s" % str(e))
            return None


    """ Set new value up or down
    """
    def __set_probe_value_up_down(self, id, new_value, reg, cmd):
        logging.debug("Function __set_probe_value_up_down() - new_value: %s, reg: %s, cmd: %s" % (new_value, reg, cmd))
        try:
            i = 0
            for i in range(10): # max tries
                # send up or down command
                response = self.serial_get_response(id+cmd)
                logging.verbose("Probe response %s" % response)
                # check for match
                matches = re.match(reg, response)
                if matches:
                    current_value = matches.group(1)
                    logging.verbose("Probe value %s" % current_value)
                    # check for correct value - int
                    if int(current_value) == int(new_value):
                        logging.info("Value set to %s" % str(current_value))
                        # confirm and store new value setting
                        response = self.serial_get_response(id+'I')
                        logging.verbose("Probe response %s" % response)
                        return current_value
                        break;

            return False

        except Exception as e:
            logging.critical("An exception was encountered in __set_probe_value_up_down(): %s" % str(e))
            return False



    """ PROBE GETTERS
    """

    """ Get probe id
    """
    def get_probe_id(self, id):
        logging.debug("Function get_probe_date()")
        try:
            # find item
            for i in range(15):
                if i==0:
                    # enter calibration
                    response = self.serial_get_response(id+'E')
                else:
                    response = self.serial_get_response(id+'M')

                logging.debug("%02d response %s" % (i+1, response))
                reg = 'SA8340.+SA8340\sR\d\.\d\d\s+ID:\s(\d\d).+'
                matches = re.match(reg, response)
                if matches:
                    return matches.group(1)

                    # exit loop
                    break

            return None

        except Exception as e:
            logging.critical("An exception was encountered in get_probe_id(): %s" % str(e))
            return None

    """ Read main configuration
    """
    def get_probe_configuration(self, id):
        logging.debug("Function get_probe_configuration()")
        try:
            # config
            config = self.CRLF
            # find items
            for i in range(15):
                if i==0:
                    # enter calibration
                    response = self.serial_get_response(id+'E')
                else:
                    response = self.serial_get_response(id+'M')

                logging.debug("%02d response %s" % (i+1, response))
                config = config + response + self.CRLF

            return config

        except Exception as e:
            logging.critical("An exception was encountered in get_probe_configuration(): %s" % str(e))
            return None

    """ Get probe baud rate
    """
    def get_probe_baud_rate(self, id):
        logging.debug("Function get_probe_baud_rate()")
        try:
            # find item
            for i in range(15):
                if i==0:
                    # enter calibration
                    response = self.serial_get_response(id+'E')
                else:
                    response = self.serial_get_response(id+'M')

                logging.debug("-> %02d response %s" % (i+1, response))

                # SA8340- 00 SA8340 R2.63    ID: 00          51
                reg = 'SA8340.+TRANSMISSION\s+BAUD\sRATE.+(1200|2400|4800|9600|19200)..'
                matches = re.match(reg, response)
                if matches:
                    return matches.group(1)

                    # exit loop
                    break

        except Exception as e:
            logging.critical("An exception was encountered in get_probe_baud_rate(): %s" % str(e))
            return None

    """ Get probe date
    """
    def get_probe_date(self, id):
        logging.debug("Function get_probe_date()")
        try:
            # find item
            for i in range(15):
                if i==0:
                    # enter calibration
                    response = self.serial_get_response(id+'E')
                else:
                    response = self.serial_get_response(id+'M')

                logging.debug("-> %02d response %s" % (i+1, response))
                # SA8340- 00 TIME  22/03/17        12:07:58
                reg = 'SA8340.+TIME\s+(\d\d\/\d\d\/\d\d)\s+(\d\d:\d\d:\d\d).+'
                matches = re.match(reg, response)
                if matches:
                    return matches.group(1)+' '+matches.group(2)

                    # exit loop
                    break

        except Exception as e:
            logging.critical("An exception was encountered in get_probe_date(): %s" % str(e))
            return None





    """ PROBE SETTERS
    """

    """ Set probe id
    """
    def set_probe_id(self, id, newid):
        logging.debug("Function set_probe_id() - id: %s, new id: %s" % (id, newid))
        try:
            # find item
            logging.verbose('Looping in range')
            for i in range(15):
                if i==0:
                    # enter calibration
                    response = self.serial_get_response(id+'E')
                else:
                    response = self.serial_get_response(id+'M')

                logging.debug("-> %02d response %s" % (i+1, response))
                # SA8340- 00 SA8340 R2.63    ID: 00          51
                reg = 'SA8340.+SA8340\sR\d\.\d\d\s+ID:\s(\d\d).+'
                matches = re.match(reg, response)
                if matches:
                    # check if we need to increase or decrease the value
                    cur_id = int(matches.group(1))
                    if cur_id == newid:
                        logging.debug("Id is correct")
                        return True

                    # need to be changed
                    logging.debug("Start calibration sequense")
                    response = self.serial_get_response(id+'C')
                    logging.debug("-->> response %s" % response)
                    # reg expression
                    reg = 'SA8340.+SA8340\sR\d\.\d\d\s+CAL ID:\s(\d\d).+'
                    if cur_id < newid:
                        logging.debug("Id must be incremented")
                        res = self.__set_probe_value_up_down(id, newid, reg, 'U')
                    else:
                        logging.debug("Id must be decremented")
                        res = self.__set_probe_value_up_down(id, newid, reg, 'D')

                    # exit loop
                    return (res == newid)

        except Exception as e:
            logging.critical("An exception was encountered in set_probe_id(): %s" % str(e))
            return None

    """ Set probe time
    """
    def set_probe_date_time(self, id, date, time):
        logging.debug("Function set_probe_date_time() - id: %s, new value: %s %s" % (id, date, time))
        try:
            reg = '\d\d(\d\d)-(\d\d)-(\d\d)'
            matches = re.match(reg, date)
            if not matches:
                logging.warning("wrong date")
                return False
            year = matches.group(1)
            month = matches.group(2)
            day = matches.group(3)

            reg = '(\d\d):(\d\d)'
            matches = re.match(reg, time)
            if not matches:
                logging.warning("wrong time")
                return False
            hour = matches.group(1)
            minute = matches.group(2)
            logging.debug("Date %s %s %s %s %s" % (year, month, day, hour, minute))

            # find item
            for i in range(15):
                if i==0:
                    # enter calibration
                    response = self.serial_get_response(id+'E')
                else:
                    response = self.serial_get_response(id+'M')

                logging.verbose("-> %02d response %s" % (i+1, response))
                # SA8340- 00 SA8340 R2.63    ID: 00          51
                reg = 'SA8340.+TIME\s+(\d\d)\/(\d\d)\/(\d\d)\s+(\d\d):(\d\d):(\d\d).+'
                # Full match  0-45    `SA8340- 00 TIME  01/09/17        15:58:29  29`
                # Group 1.    17-19   `01`
                # Group 2.    20-22   `09`
                # Group 3.    23-25   `17`
                # Group 4.    33-35   `15`
                # Group 5.    36-38   `58`
                # Group 6.    39-41   `29`
                matches = re.match(reg, response)
                if matches:
                    logging.debug("Probe time %s" % response)
                    # check if we need to increase or decrease the value
                    cur_day = matches.group(1)
                    if cur_day == day:
                        logging.debug("Day is correct")

                    cur_month = matches.group(2)
                    if cur_month == month:
                        logging.debug("Month is correct")

                    cur_year = matches.group(3)
                    if cur_year == year:
                        logging.debug("Year is correct")

                    cur_hour = matches.group(4)
                    if cur_hour == hour:
                        logging.debug("Hour is correct")

                    cur_minute = matches.group(5)
                    if cur_minute == minute:
                        logging.debug("Minute is correct")

                    # need to be changed
                    logging.debug("Start calibration sequense")
                    response = self.serial_get_response(id+'C')
                    logging.debug("-->> response %s" % response)

                    # set day
                    logging.debug("Set day")
                    reg = 'SA8340.+CAL\sTIME\s+DAY\s+(\d\d).+'
                    if cur_day < day:
                        logging.debug("Day must be incremented")
                        res = self.__set_probe_value_up_down(id, day, reg, 'U')
                    elif cur_day > day:
                        logging.debug("Day must be decremented")
                        res = self.__set_probe_value_up_down(id, day, reg, 'D')
                    else:
                        logging.debug("Next bit of date")
                        response = self.serial_get_response(id+'I')
                        logging.debug("-->> response %s" % response)

                    # set month
                    logging.debug("Set month")
                    reg = 'SA8340.+CAL\sTIME\s+MON\.\s+(\d\d).+'
                    if cur_month < month:
                        logging.debug("Day must be incremented")
                        res = self.__set_probe_value_up_down(id, month, reg, 'U')
                    elif cur_month > month:
                        logging.debug("Day must be decremented")
                        res = self.__set_probe_value_up_down(id, month, reg, 'D')
                    else:
                        logging.debug("Next bit of date")
                        response = self.serial_get_response(id+'I')
                        logging.debug("-->> response %s" % response)

                    # set year
                    logging.debug("Set year")
                    reg = 'SA8340.+CAL\sTIME\s+YEAR\s+(\d\d).+'
                    if cur_year < year:
                        logging.debug("Day must be incremented")
                        res = self.__set_probe_value_up_down(id, year, reg, 'U')
                    elif cur_year > year:
                        logging.debug("Day must be decremented")
                        res = self.__set_probe_value_up_down(id, year, reg, 'D')
                    else:
                        logging.debug("Next bit of date")
                        response = self.serial_get_response(id+'I')
                        logging.debug("-->> response %s" % response)

                    # set hour
                    logging.debug("Set hour")
                    reg = 'SA8340.+CAL\sTIME\s+HOUR\s+(\d\d).+'
                    if cur_hour < hour:
                        logging.debug("Hour must be incremented")
                        res = self.__set_probe_value_up_down(id, hour, reg, 'U')
                    elif cur_hour > hour:
                        logging.debug("Hour must be decremented")
                        res = self.__set_probe_value_up_down(id, hour, reg, 'D')
                    else:
                        logging.debug("Next bit of date")
                        response = self.serial_get_response(id+'I')
                        logging.debug("-->> response %s" % response)

                    # set minute
                    logging.debug("Set minute")
                    reg = 'SA8340.+CAL\sTIME\s+MIN\.\s+(\d\d).+'
                    if cur_minute < minute:
                        logging.debug("Minute must be incremented")
                        res = self.__set_probe_value_up_down(id, minute, reg, 'U')
                    elif cur_minute > minute:
                        logging.debug("Minute must be decremented")
                        res = self.__set_probe_value_up_down(id, minute, reg, 'D')
                    else:
                        logging.debug("End setting date time")
                        response = self.serial_get_response(id+'I')
                        logging.debug("-->> response %s" % response)

                    # exit loop
                    return True
                    break

        except Exception as e:
            logging.critical("An exception was encountered in set_probe_id(): %s" % str(e))
            return None

    """ Set probe log time format Minutes|Hours
    """
    def set_probe_log_time_format(self, id, format):
        logging.debug("Function set_probe_log_time_format()")
        try:
            # find item
            for i in range(15):
                if i == 0:
                    response = self.serial_get_response(id+'E')
                else:
                    response = self.serial_get_response(id+'M')

                logging.debug("-> %02d response %s" % (i+1, response))
                # analyse data
                # SA8340- 00 LOG ON TIME 59m START           61
                # SA8340- 00 LOG ON TIME 24h START           6E
                # SA8340- 00 LOG ON TIME 24h STOP   17h 14/0755
                reg1 = 'SA8340.+LOG\sON\sTIME.+(START|STOP).+'
                if re.match(reg1, response):
                    logging.debug("Start calibration sequense")
                    response = self.serial_get_response(id+'C')
                    logging.debug("->-> response %s" % (response))
                    if re.match('SA8340.+CAL\sLOG:\s+ON\sTIME.+', response):
                        response = self.serial_get_response(id+'I')
                        logging.debug("->->-> response %s" % (response))
                        # SA8340- 00 CAL LOG: T.INT   Minutes        54
                        # SA8340- 00 CAL LOG: T.INT   Hours          5A
                        reg2 = 'SA8340.+CAL\s+LOG:\s+T\.INT\s+(Minutes|Hours).+'
                        matches = re.match(reg2, response)
                        if matches:
                            # check if we need to increase or decrease the value
                            if matches.group(1) == 'Hours': # 'Hours' | 'Minutes'
                                if format == 'Hours':
                                    logging.info("Log format is correct - Hours")
                                    return True

                                logging.info("Setting MINUTES")
                                response = self.serial_get_response(id+'D')
                                logging.debug("->->->-> response %s" % (response))
                                # SA8340- 00 CAL LOG: T.INT   Hours          5A
                                response = self.serial_get_response(id+'I')
                                return True

                            else:
                                if format == 'Minutes':
                                    logging.info("Log format is correct - Minutes")
                                    return True

                                logging.info("Setting HOURS")
                                response = self.serial_get_response(id+'U')
                                logging.debug("->->->-> response %s" % (response))
                                # SA8340- 00 CAL LOG: T.INT   Hours          5A
                                response = self.serial_get_response(id+'I')
                                return True

                            # exit loop
                            break

        except Exception as e:
            logging.critical("An exception was encountered in set_probe_log_time_format(): %s" % str(e))
            return None

    """ Set probe log time
    """
    def set_probe_log_time(self, id, value):
        logging.debug("Function set_probe_log_time() - value: %s" % str(value))
        try:
            # find item
            for i in range(15):
                if i == 0:
                    response = self.serial_get_response(id+'E')
                else:
                    response = self.serial_get_response(id+'M')
                logging.debug("-> %02d response %s" % (i+1, response))
                # analyse data
                # SA8340- 00 LOG ON TIME 59m START           61
                reg = 'SA8340.+LOG\sON\sTIME\s+(\d+)(m|h)\s(START|STOP).+'
                matches = re.match(reg, response)
                if matches:
                    # check if we need to increase or decrease the value
                    cur_value = int(matches.group(1))
                    if cur_value == value:
                        logging.info("Minutes|Hours are correct")
                        return True

                    # 00A
                    # SA8340- 00 5.1 23/03/17 14:05:37   0.007m      23.56øC     0.000mS    11.067pH   22/03/17DB
                    # 00E
                    # SA8340- 00 LOG ON TIME 59m START           61
                    # 00C
                    # SA8340- 00 CAL LOG:        ON TIME         34
                    # 00I
                    # SA8340- 00 CAL LOG: T.INT   Minutes        54
                    # 00I
                    # SA8340- 00 CAL LOG: T.INT   59m            68
                    # 00D
                    # SA8340- 00 CAL LOG: T.INT   59m            68
                    # 00D
                    # SA8340- 00 CAL LOG: T.INT   58m            69

                    # need to be changed
                    logging.debug("Start calibration sequense")
                    response = self.serial_get_response(id+'C')
                    # SA8340- 00 CAL LOG:        ON TIME         34
                    logging.debug("-->> response %s" % response)
                    if re.match('SA8340.+CAL\sLOG:\s+ON\sTIME.+', response):

                        response = self.serial_get_response(id+'I')
                        # SA8340- 00 CAL LOG: T.INT   Minutes        54
                        logging.debug("-->> response %s" % response)
                        if re.match('SA8340.+CAL\sLOG:\s+T.INT\s+(Minutes|Hours).+', response):

                            response = self.serial_get_response(id+'I')
                            # SA8340- 00 CAL LOG: T.INT   59m            68
                            logging.debug("-->> response %s" % response)
                            reg = 'SA8340.+CAL\sLOG:\s+T.INT\s+(\d+)(m|h).+'
                            if re.match(reg, response):
                                if int(cur_value) < int(value):
                                    logging.debug("Minutes|Hours must be incremented")
                                    res = self.__set_probe_value_up_down(id, value, reg, 'U')
                                else:
                                    logging.debug("Minutes|Hours must be decremented")
                                    res = self.__set_probe_value_up_down(id, value, reg, 'D')

                                # exit loop
                                return (int(res) == int(value))

        except Exception as e:
            logging.critical("An exception was encountered in set_probe_log_time(): %s" % str(e))
            return None

    """ Set probe serial baud rate
    """
    def set_probe_baud_rate(self, id, baud):
        logging.debug("Function set_probe_baud_rate() - baud: %s" % baud)
        try:
            # find item
            for i in range(15):
                if i==0:
                    # enter calibration
                    response = self.serial_get_response(id+'E')
                else:
                    response = self.serial_get_response(id+'M')

                logging.debug("-> %02d response %s" % (i+1, response))
                # analyse data
                # SA8340- 00 TRANSMISSION    BAUD RATE:  24002A
                reg = 'SA8340.+TRANSMISSION\s+BAUD\sRATE.+(1200|2400|4800|9600|19200)..'
                matches = re.match(reg, response)
                if matches:
                    # check if we need to increase or decrease the value
                    cur_baud = matches.group(1)
                    logging.info("Baud rate %s" % cur_baud)

                    if int(cur_baud) == int(baud):
                        logging.info("Baud rate OK")
                        return True

                    # need to be changed
                    logging.debug("Start calibration sequense")
                    response = self.serial_get_response(id+'C')
                    logging.debug("-->> response %s" % response)
                    reg = 'SA8340.+CAL\sTRANSMISSIONBAUD RATE:\s+(\d+)..'
                    if int(cur_baud) < int(baud):
                        logging.debug("Baud must be incremented")
                        res = self.__set_probe_value_up_down(id, baud, reg, 'U')
                    else:
                        logging.debug("Baud must be decremented")
                        res = self.__set_probe_value_up_down(id, baud, reg, 'D')

                    # exit loop
                    return (res == baud)

        except Exception as e:
            logging.critical("An exception was encountered in set_probe_baud_rate(): %s" % str(e))
            return None

    """ Set probe running start stop
    """
    def set_probe_running(self, id, status):
        logging.debug("Function set_probe_running() - status: %s" % status)
        try:
            # find item
            for i in range(15):
                if i==0:
                    # enter calibration
                    response = self.serial_get_response(id+'E')
                else:
                    response = self.serial_get_response(id+'M')

                logging.debug("-> %02d response %s" % (i+1, response))
                # analyse data
                # SA8340- 00     POWER ON                    4E
                reg = 'SA8340.+LOG\sON\sTIME.+(START|STOP).+'
                matches = re.match(reg, response)
                if matches:
                    # check if we need to increase or decrease the value
                    cur_status = matches.group(1)
                    logging.info("Status %s" % cur_status)

                    if cur_status == status:
                        logging.info("Running OK")
                        return True

                    if cur_status == 'START':
                        if status == 'START':
                            logging.info("Log format is correct - START")
                            return True

                        logging.info("Status turning OFF")
                        response = self.serial_get_response(id+'D')
                        logging.debug("-->> response %s" % response)
                        response = self.serial_get_response(id+'I')
                        logging.debug("-->> response %s" % response)

                    elif cur_status == 'STOP':
                        if status == 'STOP':
                            logging.info("Log format is correct - STOP")
                            return True
                        logging.info("Status turning ON")
                        response = self.serial_get_response(id+'U')
                        logging.debug("-->> response %s" % response)
                        response = self.serial_get_response(id+'I')
                        logging.debug("-->> response %s" % response)

                    return True
                    # exit loop
                    break

        except Exception as e:
            logging.critical("An exception was encountered in set_probe_status(): %s" % str(e))
            return None

    """ Set probe status on off
    """
    def set_probe_status(self, id, status):
        logging.debug("Function set_probe_status() - status: %s" % status)
        try:
            # find item
            for i in range(15):
                if i==0:
                    # enter calibration
                    response = self.serial_get_response(id+'E')
                else:
                    response = self.serial_get_response(id+'M')

                logging.debug("-> %02d response %s" % (i+1, response))
                # analyse data
                # SA8340- 00     POWER ON                    4E
                reg = 'SA8340.+POWER\s(ON|OFF)\s+.+'
                matches = re.match(reg, response)
                if matches:
                    # check if we need to increase or decrease the value
                    cur_status = matches.group(1)
                    logging.info("Status %s" % cur_status)

                    if cur_status == status:
                        logging.info("Status OK")
                        return True

                    if cur_status == 'ON':
                        logging.info("Status turning OFF")
                        response = self.serial_get_response(id+'D')
                        logging.debug("-->> response %s" % response)

                    elif cur_status == 'OFF':
                        logging.info("Status turning ON")
                        response = self.serial_get_response(id+'U')
                        logging.debug("-->> response %s" % response)

                    response = self.serial_get_response(id+'I')
                    # SA8340- 00     POWER OFF       **WAIT**    2B
                    logging.debug("-->> response %s" % response)

                    # exit loop
                    break

        except Exception as e:
            logging.critical("An exception was encountered in set_probe_status(): %s" % str(e))
            return None



    """ Get data from probe
    """
    def probe_download_data(self, id, sensors, all):
        logging.debug("Function probe_download_data()")
        try:
            # enable data transfer
            response = self.serial_get_response(id+'T')
            logging.debug("Response %s" % response)
            if not re.match('READY', response):
                logging.warning("Wrong response from T command")
                return False

            # get numbers of records
            logging.verbose("Get numbers of records")
            response = self.serial_get_response(id+'N')
            logging.debug("Response %s" % response)
            reg = '\s+(\d+)'
            matches = re.match(reg, response)
            if matches:
                records_count = int(matches.group(1))
            else:
                records_count = 0

            # A annulla
            # G la sonda scarica tutti i dati
            # L la sonda scarica i nuovi dati
            #records_count = 1360

            # check fo no records,send A
            if records_count == 0:
                # acquisizione continua
                response = self.serial_get_response(id+'A')
                logging.debug("response %s" % response)
                logging.warning("no records found!")
                return True

            # log
            logging.info("Record count %s" % records_count)

            # select download type
            logging.verbose("Select download type (last|all)")
            if all:
                logging.info("Downloading all data")
                response = self.serial_get_response(id+'G')
                logging.debug("Response %s" % response)
                if not re.match('G', response):
                    logging.warning("Wrong response from G command")
                    return False
            else:
                logging.info("Downloading last data")
                response = self.serial_get_response(id+'L')
                logging.debug("Response %s" % response)
                if not re.match('L', response):
                    logging.warning("Wrong response from L command")
                    return False

            # confirm command
            logging.verbose("Confirm command")
            response = self.serial_get_response(id+'I')

            # take care of max
            if records_count > 1360:
                records_count = 1360

            # select reg expression by sensors
            if int(sensors) == 5:
                # livello, temperatura, conducibilità, pH, redox
                reg = '(SA8340-\s(\d\d)\s(-?\d*(.\d+)?)\s(\d\d)\/(\d\d)\/(\d\d)\s(\d\d):(\d\d):(\d\d)\s+(-?\d*(.\d+)?).+?\s+(-?\d*(.\d+)?).+?\s+(-?\d*(.\d+)?).+?\s+(-?\d*(.\d+)?).+?\s+(-?\d*(.\d+)?).+?\s+\d\d\/\d\d\/\d\d)(..)'
                # Group 1.    0-101   `SA8340- 00 4.5 05/09/17 03:52:00  -0.005m      25.27øC     0.001mS     0.280pH     429.1mV   05/09/17`
                # Group 2.    8-10    `00`
                # Group 3.    11-14   `4.5`
                # Group 4.    12-14   `.5`
                # Group 5.    15-17   `05`
                # Group 6.    18-20   `09`
                # Group 7.    21-23   `17`
                # Group 8.    24-26   `03`
                # Group 9.    27-29   `52`
                # Group 10.   30-32   `00`
                # Group 11.   34-40   `-0.005`
                # Group 12.   36-40   `.005`
                # Group 13.   47-52   `25.27`
                # Group 14.   49-52   `.27`
                # Group 15.   59-64   `0.001`
                # Group 16.   60-64   `.001`
                # Group 17.   71-76   `0.280`
                # Group 18.   72-76   `.280`
                # Group 19.   83-88   `429.1`
                # Group 20.   86-88   `.1`
                # Group 21.   101-103 `F1`

            elif int(sensors) == 4:
                # livello, temperatura, conducibilità, pH
                reg = '(SA8340-\s(\d\d)\s(-?\d*(.\d+)?)\s(\d\d)\/(\d\d)\/(\d\d)\s(\d\d):(\d\d):(\d\d)\s+(-?\d*(.\d+)?).+?\s+(-?\d*(.\d+)?).+?\s+(-?\d*(.\d+)?).+?\s+(-?\d*(.\d+)?).+?\s+\d\d\/\d\d\/\d\d)(..)'
                # Full match    0-91    `SA8340- 20 4.3 27/06/18 11:50:00   0.002m      24.27øC    -0.001mS    -2.200pH   27/06/18CE`
                # Group 1.  0-89    `SA8340- 20 4.3 27/06/18 11:50:00   0.002m      24.27øC    -0.001mS    -2.200pH   27/06/18`
                # Group 2.  8-10    `20`
                # Group 3.  11-14   `4.3`
                # Group 4.  12-14   `.3`
                # Group 5.  15-17   `27`
                # Group 6.  18-20   `06`
                # Group 7.  21-23   `18`
                # Group 8.  24-26   `11`
                # Group 9.  27-29   `50`
                # Group 10. 30-32   `00`
                # Group 11. 35-40   `0.002`
                # Group 12. 36-40   `.002`
                # Group 13. 47-52   `24.27`
                # Group 14. 49-52   `.27`
                # Group 15. 58-64   `-0.001`
                # Group 16. 60-64   `.001`
                # Group 17. 70-76   `-2.200`
                # Group 18. 72-76   `.200`
                # Group 19. 89-91   `CE`

            else: # 3
                # livello, temperatura, conducibilità, pH
                reg = '(SA8340-\s(\d\d)\s(-?\d*(.\d+)?)\s(\d\d)\/(\d\d)\/(\d\d)\s(\d\d):(\d\d):(\d\d)\s+(-?\d*(.\d+)?).+?\s+(-?\d*(.\d+)?).+?\s+(-?\d*(.\d+)?).+?\s+(-?\d*(.\d+)?).+?\s+\d\d\/\d\d\/\d\d)(..)'
                # Group 1.    0-89    `SA8340- 05 4.5 14/09/17 12:34:38   0.000m      24.72øC     0.000mS     7.000pH   14/09/17`
                # Group 2.    8-10    `05`
                # Group 3.    11-14   `4.5`
                # Group 4.    12-14   `.5`
                # Group 5.    15-17   `14`
                # Group 6.    18-20   `09`
                # Group 7.    21-23   `17`
                # Group 8.    24-26   `12`
                # Group 9.    27-29   `34`
                # Group 10.   30-32   `38`
                # Group 11.   35-40   `0.000`
                # Group 12.   36-40   `.000`
                # Group 13.   47-52   `24.72`
                # Group 14.   49-52   `.72`
                # Group 15.   59-64   `0.000`
                # Group 16.   60-64   `.000`
                # Group 17.   71-76   `7.000`
                # Group 18.   72-76   `.000`
                # Group 19.   89-91   `C1`

            # get all data
            records = ''
            cmd = 'N' # next record
            error_count = 0
            loop_count = 0
            while loop_count < records_count + 1:
                logging.debug("-> %02d getting record" % loop_count)

                response = self.serial_get_response(id+cmd)
                logging.debug("response %s" % response)
                matches = re.match(reg, response)
                if matches:
                    record = matches.group(1)
                    logging.verbose("record %s" % record)
                    # select matches by sensors
                    if int(sensors) == 5:
                        bcc = matches.group(21)

                    elif int(sensors) == 4:
                        bcc = matches.group(19)

                    else:
                        bcc = matches.group(19)

                    # compare bcc code
                    if bcc != self.__get_bcc(record):
                        # bcc wrong
                        logging.warning('Bcc code does not much')
                        # set next call command
                        cmd = 'P' # send record again
                        # increment errors counter
                        error_count += 1
                        if error_count > 10:
                            logging.error('Too many errors, stop downloading.')
                            # end
                            break
                    else:
                        # bcc ok, valid data
                        logging.verbose('Bcc code is ok')

                        # get date time
                        date_time = '20'+matches.group(7)+'-'+matches.group(6)+'-'+matches.group(5)
                        date_time += ' '+matches.group(8)+':'+matches.group(9)+':'+matches.group(10)

                        # get values
                        values = []
                        # 5 sensors probe only
                        if int(sensors) == 5:
                            values = [matches.group(11)]
                            values.append( matches.group(13) );
                            values.append( matches.group(15) );
                            values.append( matches.group(17) );
                            values.append( matches.group(19) );
                        elif int(sensors) == 4:
                            values = [matches.group(11)]
                            values.append( matches.group(13) );
                            values.append( matches.group(15) );
                            values.append( matches.group(17) );
                        else:
                            values = [matches.group(11)]
                            values.append( matches.group(13) );
                            values.append( matches.group(15) );

                        # build record, id + date + values
                        rec = id + self.SEMICOLON + date_time + self.SEMICOLON + self.SEMICOLON.join(values)
                        logging.verbose('Record <%s>' % rec)
                        # test record
                        if records == '':
                            # empty no cr
                            records = rec
                        else:
                            records += self.CR + rec

                    # increment record count
                    loop_count += 1
                    # set next call command
                    cmd = 'N' # next record

                elif re.match('STOP', response):
                    logging.verbose("Select download type for resetting pointer counter (last|all)")
                    if all:
                        # no reset probe
                        logging.info("Pointer reset not required")
                        response = self.serial_get_response(id+'A')
                        logging.debug("Response %s" % response)
                    else:
                        logging.info("Reset pointer")
                        response = self.serial_get_response(id+'Z')
                        logging.debug("Response %s" % response)

                    # end
                    break

                else:
                    # end
                    logging.warning("Record does not match regular expression, check probe type")
                    break

            # acquisizione continua
            response = self.serial_get_response(id+'A')

            # check for valid data - records lenght: 38 for 3 params probe
            logging.verbose("Records lenght: %s" % len(records))
            if (len(records) == 0 ):
                # end
                logging.warning("No data downloaded!")
                return False

            # date time & measure time for db
            now = datetime.now()
            # build filename with id
            fileName = os.path.join(self.data_path, "SondaID-"+id+"_"+now.strftime('%Y%m%d-%H%M%S')+".dat")
            with open(fileName, 'a') as the_file:
                the_file.write(records)

            # return ok
            return True

        except Exception as e:
            logging.critical("An exception was encountered in probe_download_data(): %s" % str(e))
            return False


#
# download data
#
# 00A -> invio dati
# 00T -> funzione di scarico


#
# calibration
#
# 01 -> SA8340- 00 LOG ON TIME 59m START           61
# 02 -> SA8340- 00 REC INST.  1354 REC UTIL. 44433 23
# 03 -> SA8340- 00 MAIN  B.    V                   21
# 04 -> SA8340- 00 MAIN  B. 5.1V OK                2F
# 05 -> SA8340- 00 TIME  22/03/17        13:38:52  2E
# 06 -> SA8340- 00 LEVEL  0.007m                   02
# 07 -> SA8340- 00 TEMP.  25.90øC                  89
# 08 -> SA8340- 00 COND. -0.001mS  T.REF:20 TC:2.1007
# 09 -> SA8340- 00 pH     8.714pH  A:-0.22pH S: 98%09
# 10 -> SA8340- 00 RT CONT.:   10 s                66
# 11 -> SA8340- 00 TIMEOUT ON STARTPROFILE: 10m    17
# 12 -> SA8340- 00     POWER ON                    4E
# 13 -> SA8340- 00 SA8340 R2.63    ID: 00          51
# 14 -> SA8340- 00 TRANSMISSION    BAUD RATE:  960023


# SA8340- 00 LOG ON TIME  1h START           79
# SA8340- 00 REC INST.  1354 REC UTIL.     5 22
# SA8340- 00 MAIN  B.    V                   21
# SA8340- 00 MAIN  B. 5.1V OK                2F
# SA8340- 00 TIME  28/03/17        13:03:06  2D
# SA8340- 00 LEVEL  0.005m                   00
# SA8340- 00 TEMP.  27.12øC                  81
# SA8340- 00 COND. -0.001mS  T.REF:20 TC:2.1007
# SA8340- 00 pH    11.998pH  A:-0.22pH S: 98%1B
# SA8340- 00 RT CONT.:   10 s                66
# SA8340- 00 TIMEOUT ON STARTPROFILE: 10m    17
# SA8340- 00     POWER ON                    4E
# SA8340- 00 SA8340 R2.63    ID: 00          51
# SA8340- 00 TRANSMISSION    BAUD RATE:  960023


# SA8340- 00 5.1 29/03/17 14:03:00   0.002m      27.54øC    -0.001mS     6.612pH   28/03/17C4
# SA8340- 00 5.1 29/03/17 15:03:00   0.002m      27.70øC    -0.001mS     6.751pH   28/03/17C5
# SA8340- 00 5.1 29/03/17 16:03:00   0.002m      27.33øC    -0.001mS     6.420pH   28/03/17C4
# SA8340- 00 5.1 29/03/17 17:03:00   0.005m      26.62øC    -0.001mS     6.445pH   28/03/17C4
# SA8340- 00 5.1 29/03/17 18:03:00   0.000m      25.88øC     0.000mS     6.438pH   28/03/17CF
# SA8340- 00 5.1 29/03/17 19:03:00   0.005m      25.17øC     0.000mS     6.440pH   28/03/17C2
# SA8340- 00 5.1 29/03/17 20:03:00   0.000m      24.52øC     0.000mS     6.432pH   28/03/17C8
# SA8340- 00 5.1 29/03/17 21:03:00   0.002m      23.94øC     0.000mS     6.401pH   28/03/17C6
# SA8340- 00 5.1 29/03/17 22:03:00   0.002m      23.39øC     0.000mS     6.395pH   28/03/17C8
# SA8340- 00 5.1 29/03/17 23:03:00   0.002m      22.89øC     0.000mS     6.382pH   28/03/17C5
# SA8340- 00 5.1 30/03/17 00:03:00   0.005m      22.43øC     0.000mS     6.363pH   28/03/17C2
# SA8340- 00 5.1 30/03/17 01:03:00   0.002m      21.97øC     0.000mS     6.348pH   28/03/17C7
# SA8340- 00 5.1 30/03/17 02:03:00   0.000m      21.53øC     0.001mS     6.329pH   28/03/17C8
# SA8340- 00 5.1 30/03/17 03:03:00   0.002m      21.14øC     0.001mS     6.321pH   28/03/17C0
# SA8340- 00 5.1 30/03/17 04:03:00   0.000m      20.76øC     0.001mS     6.311pH   28/03/17C3
# SA8340- 00 5.1 30/03/17 05:03:00   0.002m      20.44øC     0.002mS     6.303pH   28/03/17C1
# SA8340- 00 5.1 30/03/17 06:03:00   0.000m      20.35øC     0.002mS     7.055pH   28/03/17C7
# SA8340- 00 5.1 30/03/17 07:03:00   0.002m      22.78øC     0.000mS     6.749pH   28/03/17C6
