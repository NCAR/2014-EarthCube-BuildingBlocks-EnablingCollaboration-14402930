#-*- coding: utf-8 -*- 
import logging
import os
from datetime import datetime

# logs
APP_LOG_DIR = "../log/" 
APP_LOG     = APP_LOG_DIR + datetime.strftime(datetime.today(),"%Y%m%d_%H%M%S.log")

# directories
HTM_OUTPUT_DIR      = "../data/output/nsfrawhtm/"
JSON_OUTPUT_DIR     = "../data/output/nsfjson/"
GRANTID_INPUT_DIR   = "../data/input/"

# files
JSON_OUTPUT_FILE    = JSON_OUTPUT_DIR + "grant_data.json"
INPUT_GRANTID_FILE  = GRANTID_INPUT_DIR + "input_grantids.txt"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# create a file handler
if not os.path.isdir(APP_LOG_DIR):
    os.makedirs(APP_LOG_DIR)

handler = logging.FileHandler(APP_LOG)
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)
