############################################################################
# 
# Human Variome Database Portal.
#
# === License ===
#
# Last Author:   $Author: MelvinLuong $
# Last Revision: $Rev: 851 $
# Last Modified: $Date: 2014-06-18 13:52:54 +1000 (Wed, 18 Jun 2014) $ 
#
# === Description ===
# Imports data from designated configuration settings into the HVP node
#
################################################################################

# python modules
import ConfigParser
import glob
import logging, logging.handlers
import shutil
import os, os.path
from datetime import datetime

# HVP Modules
from Utils.HVP_Transaction import HVP_Transaction
from Utils.HVP_DataManager import HVP_DataManager

# get absolute path to where file is running from
dirname = os.path.split(os.path.abspath(__file__))[0]

import_log = dirname + '/Import.py.log'
import_conf = dirname + '/Import.py.cfg' 


# Check valid number of instances against the total number of instance records
def CheckValidInstances(validInstances, totalRecords):
    if validInstances == totalRecords:
        return True
    else:
        return False


def main():
    # Init log for whole process
    logger = logging.getLogger('hvp')
    log_handle = logging.FileHandler(import_log)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s - %(message)s')
    log_handle.setFormatter(formatter)
    log_handle.setLevel(logging.INFO)
    logger.addHandler(log_handle)
    handler = logging.handlers.RotatingFileHandler(import_log, maxBytes=4194304, backupCount=5)
    logger.addHandler(handler)
    
    # console version
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    
    logger.setLevel(logging.INFO)

    logger.info("########################################")
    logger.info("### HVP Importing process initiating ###")
    logger.info("########################################")
    logger.info("")
    logger.info("Time: %s" % datetime.now())
    logger.info("")
    

    # Get configurations
    config = ConfigParser.RawConfigParser()
    config.read(import_conf)
    monitor_dir = dirname + "/" + config.get('Conf', 'monitor_dir')
    complete_dir = dirname + "/" + config.get('Conf', 'complete_dir')
    diff_dir = dirname + "/" + config.get('Conf', 'diff_dir')

    #database
    hostname = config.get('Database', 'hostname')
    username = config.get('Database', 'username')
    password = config.get('Database', 'password')
    database = config.get('Database', 'database')
    
    #logger.info("%s, %s, %s, %s" % (hostname, username, password, database))

    logger.info("Processing directory: %s" % monitor_dir)
    files = glob.glob(monitor_dir + "/*.xml")
    logger.info("Found: %d files" % len(files))
    logger.info("")
    
    manager = HVP_DataManager(logger, hostname, username, password, database)
    
    for file in files:
        logger.info("Begin processing: %s" % file)
        
        trans = HVP_Transaction()
        try:
            # variant data
            trans.parse(file)
        except Exception, err:
            logger.error("\tError encounted for file %s" % file)
            logger.error("\t%s" % err)
            continue
        
        logger.info("\t%d out of %d valid records to process" % (len(trans.VariantInstances), trans.TotalRecords))
        
        # check all variant instances are valid
        allValidInstances = CheckValidInstances(len(trans.VariantInstances), trans.TotalRecords)
        
        # if transactions returns an error
        failed_import = manager.processTransaction(trans, diff_dir)
        if failed_import:
            logger.info("---- ERROR ----")
            logger.info("!!! Errors detected ")
            logger.info("!!! Check file: "+ file)
        elif not allValidInstances:
            invalid_records = str(trans.TotalRecords - len(trans.VariantInstances))
            logger.info("---- ERROR ----")
            logger.info("!!! " + invalid_records + " Invalid variants detected" )
            logger.info("!!! Check file: "+ file)
        else:
            move_name = "%s/%s" % (complete_dir, os.path.basename(file))
            shutil.move(file, move_name)
            logger.info("Moved file to %s" % move_name)
            logger.info("End processing: %s" % os.path.basename(file))

if __name__ == "__main__":
    main()
