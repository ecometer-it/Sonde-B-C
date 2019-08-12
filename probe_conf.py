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
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
#  https://github.com/docopt/docopt/blob/master/examples/arguments_example.py
#  https://realpython.com/blog/python/comparing-python-command-line-parsing-libraries-argparse-docopt-click/
#  http://docopt.org/
#  http://www.pyinstaller.org/
#  Install: 
#  sudo apt-get install python3-pip
#  sudo pip3 install pyserial | pip install pyserial
#  sudo pip3 install docopt | pip install docopt
# ----------------------------------------------------------------------
"""probe_conf by ecometer snc.
Usage:
    probe_conf.py [-v ...] [options] get_id
    probe_conf.py [-v ...] [options] get_config
    probe_conf.py [-v ...] [options] get_baud
    probe_conf.py [-v ...] [options] get_date
    probe_conf.py [-v ...] [options] set_id <newid>
    probe_conf.py [-v ...] [options] set_date <date> <time>
    probe_conf.py [-v ...] [options] set_date_gmt1
    probe_conf.py [-v ...] [options] set_baud <baud>
    probe_conf.py [-v ...] [options] set_log_format (hours|minutes)
    probe_conf.py [-v ...] [options] set_log_value <value>
    probe_conf.py [-v ...] [options] set_run (start|stop)
    probe_conf.py [-v ...] [options] set_status (on|off)
    probe_conf.py [-v ...] [options] switch_off
    probe_conf.py [-v ...] [options] get_data <sensors> (last|all)
    probe_conf.py (-h | --help)

Arguments:
    get_id          Get probe id
    get_config      Get probe configuration from device
    get_baud        Get probe baud rate
    get_date        Get probe date time
    set_id          Set probe id
    set_date        Set probe date and time, format <YYYY-MM-DD> <HH:MM>
    set_date_gmt1   Set probe date and time, format GMT+1
    set_baud        Set probe baud rate
    set_log_format  Set probe log time format to hours or minutes
    set_log_value   Set probe log time value
    set_run         Set probe running (start|stop)
    set_status      Set probe status (on|off)
    switch_off      Switch off probe
    get_data        Get probe data
                    # <sensors> number of sensors 3|5
                    # (last|all) download last data or all data

Options:
    -h --help       Show this screen.
    -v              Verbosity, more v, more verbose.
    -i, --id=<n>    Probe id [default: 0].
    -p, --port=<s>  Port [default: COM5].
    -b, --baud=<n>  Baudrate [default: 9600].
"""

""" Imports
"""
import sys
import os
import logging
import logging.handlers
import time
import re
import serial
from datetime import datetime, timedelta
from docopt import docopt
# ecometer modules
import probe_bc_8340


""" Logging
"""
def createLog(level):
    # path
    logpath = os.path.join(os.path.dirname(os.path.realpath(__file__)),'log')
    if not os.path.exists(logpath):
        os.makedirs(logpath)

    # logging custom level
    logging.VERBOSE = 5  # positive yet important
    logging.addLevelName(logging.VERBOSE, 'VERBOSE')      # new level
    logging.getLogger('').setLevel(logging.INFO)
    logging.Logger.verbose = lambda inst, msg, *args, **kwargs: inst.log(logging.VERBOSE, msg, *args, **kwargs)
    logging.verbose = lambda msg, *args, **kwargs: logging.log(logging.VERBOSE, msg, *args, **kwargs)

    # formatter
    formatter = logging.Formatter('%(asctime)s-%(levelname)s: %(message)s')

    # rotation
    logfilename = os.path.join(logpath, 'app.log')
    handler = logging.handlers.RotatingFileHandler(logfilename, maxBytes=1*1024*1024, backupCount=10)
    handler.setFormatter(formatter)
    logging.getLogger('').addHandler(handler)

    # console
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # formatter
    formatter_console = logging.Formatter('%(asctime)s-%(levelname)s: %(message)s')
    #formatter_console = logging.Formatter('%(message)s')
    console.setFormatter(formatter_console)
    logging.getLogger('').addHandler(console)

    # set level
    if level == 1:
        logging.getLogger('').setLevel(logging.DEBUG)
        console.setLevel(logging.DEBUG)
    if level == 2:
        logging.getLogger('').setLevel(logging.VERBOSE)
        console.setLevel(logging.VERBOSE)

    # https://docs.python.org/3.4/library/logging.handlers.html?highlight=backupcount
    # CRITICAL 50
    # ERROR    40
    # WARNING  30
    # INFO     20
    # DEBUG    10
    # VERBOSE   5
    # NOTSET    0


""" Clear screen
"""
def clearscreen(numlines=100):
    if os.name == "posix":
        # Unix/Linux/MacOS/BSD/etc
        os.system('clear')
    elif os.name in ("nt", "dos", "ce"):
        # DOS/Windows
        os.system('CLS')


""" Getters
    Functions to retrieve data from probe
"""

""" Get probe id
"""
def get_id(id):
    logging.debug("Get probe id")
    # weake probe
    if client.probe_wakeup(id):
        pid = client.get_probe_id(id)
        logging.info("Probe id: %s" % pid)


""" Get configuration
"""
def get_config(id):
    logging.debug("Get configuration")
    logging.info("Wait 10 seconds...")
    # weake probe
    if client.probe_wakeup(id):
        config = client.get_probe_configuration(id)
        logging.info("Configuration: %s" % config)


""" Get probe baud rate
"""
def get_baud(id):
    logging.debug("Get probe baud rate")
    # weake probe
    if client.probe_wakeup(id):
        bauds = client.get_probe_baud_rate(id)
        logging.info("Probe baud rate: %s" % bauds)


""" Get probe baud rate
"""
def get_date(id):
    logging.debug("Get probe date")
    # weake probe
    if client.probe_wakeup(id):
        bauds = client.get_probe_date(id)
        logging.info("Probe date: %s" % bauds)




""" Setters
    Functions to set parameters on probe
"""

""" Set id
"""
def set_id(id, newid):
    logging.debug("Set probe id")
    logging.debug("id: %s, newid: %s" % (id, newid))
    # weake probe
    if client.probe_wakeup(id):
        res = client.set_probe_id(id, newid)
        logging.info("Probe result: %s" % res)

    logging.debug("** Restart probe")

""" Set probe time
"""
def set_date_time(id, date, time):
    logging.debug("Set probe time")
    logging.debug("id: %s, date: %s, time: %s" % (id, date, time))
    # weake probe
    if client.probe_wakeup(id):
        res = client.set_probe_date_time(id, date, time)
        logging.info("Probe result: %s" % res)

""" Set log time format
"""
def set_log_time_format(id, format):
    logging.debug("Set log time to %s" % format)
    # weake probe
    if client.probe_wakeup(id):
        res = client.set_probe_log_time_format(id, format)
        logging.info("Probe result: %s" % res)

""" Set log time value (minutes | hours)
"""
def set_log_time_value(id, value):
    logging.debug("Set log time (minutes | hours) to %s" % value)
    # weake probe
    if client.probe_wakeup(id):
        res = client.set_probe_log_time(id, value)
        logging.info("Probe result: %s" % res)

""" Set serial bauds rate
"""
def set_baud(id, baud):
    logging.debug("Set serial bauds rate to %s" % baud)
    # weake probe
    if client.probe_wakeup(id):
        res = client.set_probe_baud_rate(id, baud)
        logging.info("Probe result: %s" % res)

""" Set probe running state
"""
def set_probe_running(id, status):
    logging.debug("Set probe running")
    # weake probe
    if client.probe_wakeup(id):
        res = client.set_probe_running(id, status)
        logging.info("Probe running: %s" % res)

""" Set probe status on/off
"""
def set_probe_status(id, status):
    logging.debug("Set probe status")
    # weake probe
    if client.probe_wakeup(id):
        res = client.set_probe_status(id, status)
        logging.info("Probe status: %s" % res)

""" Switch off probe
"""
def probe_switch_off(id):
    logging.debug("Switch off probe")
    # weake probe
    if client.probe_wakeup(id):
        res = client.probe_switch_off() # no id needed
        logging.info("Probe result: %s" % res)


""" Data
    Functions to get data
"""
def get_data(id, sensors, all):
    logging.debug("Get data from probe id %s, sensors %s, all %s" % (id, sensors, all))
    # weake probe
    if client.probe_wakeup(id):
        res = client.probe_download_data(id, sensors, all)
        logging.info("Probe result: %s" % res)




""" Main script
"""
if __name__ == '__main__':

    try:
        """ Arguments
        """
        args = docopt(__doc__)

        """ Clear
        """
        clearscreen()

        """ Logging
        """
        createLog(args['-v'])

        """ Start
        """
        now = datetime.now()
        logging.info("Starting program @ %s" % now.strftime("%Y-%m-%d %H:%M:%S"))
        logging.verbose("Arguments: %s" % args)

        """ Path
        """
        # application path
        app_path = os.path.dirname(os.path.realpath(__file__))
        # data path
        data_path = os.path.join(app_path, 'data')
        if not os.path.exists(data_path):
            os.mkdir(data_path)

        """ Config
        """
        conf = {
            'port'     : 'COM5', # default set as in docopt COM5 | /dev/ttyAMA0
            'baudrate' : 9600, # default set as in docopt
            'parity'   : serial.PARITY_NONE,
            'stopbits' : serial.STOPBITS_ONE,
            'bytesize' : serial.EIGHTBITS
        }

        # parse argumets
        if args['--port']:
            conf['port'] = args['--port']
        if args['--baud']:
            conf['baudrate'] = args['--baud']

        # log
        logging.verbose("Configuration: %s" % conf)


        """ Client
        """
        client = probe_bc_8340.Client(conf, data_path)
        if not client.serial_open():
            # log
            logging.info("Impossible to open serail port!")
        else:

            """ Arguments
            """
            logging.debug("Parse args")

            # getter
            if args['get_id']:
                id = args['--id'].zfill(2)
                get_id(id.zfill(2))

            elif args['get_config']:
                id = args['--id'].zfill(2)
                get_config(id)

            elif args['get_baud']:
                id = args['--id'].zfill(2)
                get_baud(id)

            elif args['get_date']:
                id = args['--id'].zfill(2)
                get_date(id)

            # setters
            elif args['set_id']:
                id = args['--id'].zfill(2)
                newid = int(args['<newid>'])
                set_id(id, newid)

            elif args['set_date']:
                id = args['--id'].zfill(2)
                date = args['<date>']
                time = args['<time>']
                set_date_time(id, date, time)

            elif args['set_date_gmt1']:
                id = args['--id'].zfill(2)
                now = datetime.utcnow() + timedelta(hours=1)
                # <YYYY-MM-DD> <HH:MM>
                date = now.strftime('%Y-%m-%d')
                time = now.strftime('%H:%M')
                set_date_time(id, date, time)

            elif args['set_log_format']:
                id = args['--id'].zfill(2)
                if args['hours']:
                    set_log_time_format(id, 'Hours')
                if args['minutes']:
                    set_log_time_format(id, 'Minutes')

            elif args['set_log_value']:
                id = args['--id'].zfill(2)
                value = int(args['<value>'])
                set_log_time_value(id, value)

            elif args['set_baud']:
                id = args['--id'].zfill(2)
                baud = int(args['<baud>'])
                set_baud(id, baud)

            elif args['set_run']:
                id = args['--id'].zfill(2)
                if args['start']:
                    set_probe_running(id, 'START')
                if args['stop']:
                    set_probe_running(id, 'STOP')

            elif args['set_status']:
                id = args['--id'].zfill(2)
                if args['on']:
                    set_probe_status(id, 'ON')
                if args['off']:
                    set_probe_status(id, 'OFF')

            elif args['switch_off']:
                id = args['--id'].zfill(2)
                probe_switch_off(id)

            # data
            elif args['get_data']:
                id = args['--id'].zfill(2)
                sensors =  args['<sensors>']
                last =  args['last']
                all =  args['all']
                get_data(id, sensors, all)

    # Handle invalid options
    except Exception as e:
        logging.critical("An exception was encountered: %s" % str(e))

    # clean up
    del client



""" SAMPLES
"""
# probe_conf.py -vv -p COM5 -b 2400 set_baud 9600
# probe_conf.py -vv -p COM5 -b 9600 get_id
# probe_conf.py -vv -p COM5 -b 9600 get_config
# probe_conf.py -vv -p COM5 -b 9600 set_id 2
# probe_conf.py -vv -p COM5 set_date_gmt1
# probe_conf.py -vv -p COM5 set_date 2017-09-01 15:36

""" first configuration
"""
# probe_conf.py -b 2400 get_config
# probe_conf.py -b 2400 set_baud 9600
# probe_conf.py get_id
# probe_conf.py set_id 5
# probe_conf.py set_date_gmt1
# probe_conf.py set_log_format hours
# probe_conf.py set_log_value 1
# probe_conf.py set_run start

""" data
"""
# probe_conf.py get_data 3 last
# probe_conf.py get_data 5 last
