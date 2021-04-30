import os.path
import sys
import json
import logging
import zipfile
import datetime
import time
import gc


def config_logger(name: str = __name__, level: int = logging.DEBUG):
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logger.propagate = False
        logger.setLevel(level)
        f_str = '%(asctime)s,%(msecs)3d %(levelname)-7s %(filename)s %(funcName)s(%(lineno)s) %(message)s'
        log_formatter = logging.Formatter(f_str, datefmt='%H:%M:%S')
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        logger.addHandler(console_handler)
    return logger


LOGGER = config_logger()
self = object()
self.log_file_name = None
self.outFolder = ".\\data\\"
self.lockFile = None
self.locked = False
self.shot = 0
self.logFile = None
self.zipFile = None



def get_log_folder(self):
    ydf = datetime.datetime.today().strftime('%Y')
    mdf = datetime.datetime.today().strftime('%Y-%m')
    ddf = datetime.datetime.today().strftime('%Y-%m-%d')
    folder = os.path.join(ydf, mdf, ddf)
    return folder


def lock_dir(self, folder):
    self.lockFile = open(os.path.join(folder, "lock.lock"), 'w+')
    self.locked = True
    LOGGER.log(logging.DEBUG, "Directory %s locked", folder)


def open_log_file(self, folder=''):
    self.logFileName = os.path.join(folder, self.get_log_file_name())
    logf = open(self.logFileName, 'a')
    return logf


def get_log_file_name(self):
    logfn = datetime.datetime.today().strftime('%Y-%m-%d.log')
    return logfn


def date_time_stamp(self):
    return datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')


def time_stamp(self):
    return datetime.datetime.today().strftime('%H:%M:%S')


def unlock_dir(self):
    if self.lockFile is not None:
        self.lockFile.close()
        os.remove(self.lockFile.name)
    self.locked = False
    LOGGER.log(logging.DEBUG, "Directory unlocked")


if len(sys.argv) < 2:
    LOGGER.log(logging.WARNING, "No log file name")
    exit()
self.logFile = sys.argv[1]

# defile and start timer task

