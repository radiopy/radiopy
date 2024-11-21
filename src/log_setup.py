import logging
import os
import sys

script_name = os.path.basename(sys.argv[0])
logging.basicConfig(level=logging.INFO,
                    format=f"%(asctime)s - {script_name}:%(name)s - %(levelname)s - %(message)s",
                    handlers=[logging.StreamHandler(), logging.FileHandler("./radiopy.log")])

# catch errors
def handle_exception(exc_type, exc_value, exc_traceback):
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = handle_exception
