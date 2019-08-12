#!/usr/bin/python3
# -*- coding: utf-8 -*-
# https://github.com/docopt/docopt/blob/master/examples/arguments_example.py
# https://realpython.com/blog/python/comparing-python-command-line-parsing-libraries-argparse-docopt-click/
# http://docopt.org/
# sudo apt-get install python3-pip
# sudo pip3 install docopt
#
# http://www.pyinstaller.org/
#
"""probe_net by ecometer snc.

Usage:
    probe_net.py [-v ...] [options] get_data <sensors> (last|all)
    probe_net.py [-v ...] [options] get_net_data
    probe_net.py (-h | --help)

Arguments:
    get_data        Get probe data
                    # <sensors> number of sensors 3|5
                    # (last|all) download last data or all data
    get_net_data    Get all network probes data

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
import subprocess
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
    logfilename = os.path.join(logpath, 'probe_net.log')
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


""" Data
    Functions to get data
"""
def get_data(id, sensors, all):
    logging.info("Get data from probe id %s, sensors %s, all %s" % (id, sensors, all))
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
            if args['get_data']:
                id = args['--id'].zfill(2)
                sensors =  args['<sensors>']
                last =  args['last']
                all =  args['all']
                get_data(id, sensors, all)

            elif args['get_net_data']:
                # get sensor last data
                # -- S20 -> ID18 {3} > OK
                get_data(str(18).zfill(2), 3, False)

                # -- S26 -> ID24 {5} > OK
                get_data(str(24).zfill(2), 5, False)

                # -- S26bis -> ID25 {5} > OK
                get_data(str(25).zfill(2), 5, False)

                # -- S08 -> ID5 {3}
                #get_data(5, 3, False)

                # -- S13 -> ID10 {5}
                #get_data(10, 5, False)

                # execute external perl script
                logging.info("Executing external perl script...")
                pipe = subprocess.Popen(["perl", "c:/SmartDMS/Sonde_BC8340/probe_import.pl"], stdout=subprocess.PIPE)

    # Handle invalid options
    except Exception as e:
        logging.critical("An exception was encountered: %s" % str(e))

    # clean up
    del client


""" SAMPLES
"""
# probe_net.py get_data 3 last
# probe_net.py get_data 5 last
# probe_net.py get_net_data