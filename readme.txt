Prerequisite:
- Python 2.6+
- MySQLdb
- dateutil
- pyCrypto

VariantImporter Key files:
WebReceive.py - Starts a http server for receiving and decrypting files.
WebReceive.py.cfg - Configuration settings for the WebReceive.
Import.py - Script to import the decrypted xml data.
Import.py.cfg - Configuration settings for the Import.
import_cron - cron job sript to run the Import on a nightly routine

To Run WebReceive:
1. First edit the WebReceive.py.cfg file settings.

2. Run "Python WebRecieve" to start the server.

NB: To run in the background using nohup use the command "nohup python WebReceive.py &".

To Run importer:
1. Setup the configuration file "Import.py.cfg" with the correct directory names for outputs and keys.

2. Copy the receiver private key and the senders public key to the Keys directory.

3. Upon receiving a data subission the WebReceive will decrypt and send the raw xml to the output directory.

3. Run with "Python Import". Upon success, files will be moved from the "output" directory to the 
"complete" directory.

NB: To run Import on a automated nightly basis run the import_cron script using "crontab import_cront".