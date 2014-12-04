# A very basic wrapper for sending that encrypts, zips and posts data to HVP server

from HVP_Encryption import Encrypt

import os
import requests
import zipfile
from optparse import OptionParser


def main():
    parser = OptionParser()
    parser.add_option("--public", dest="public", help="Filename of public key of destination", default="hvp.public")
    parser.add_option("--private", dest="private", help="Filename of private key of source)", default="client1.private")
    parser.add_option("--input", dest="input", help="Filename of input file to encrypt")
    parser.add_option("--destURL", dest="destURL", help="URL with port number of WebReceiver", default="http://localhost:8088")
    parser.add_option("--org", dest="org", help="Name of organisation. This is used to match the key to use on the other end", default="client1")
    parser.add_option("-d", "--dontclean", dest="dontclean", action="store_true", help="Set to don't clean temp files")
    options, args = parser.parse_args()

    if options.public is None or options.private is None or options.input is None or options.destURL is None:
        print "You need to have all --public (filename) --private (filename) --input (filename) --deskURL (url & port) --org (name) values"
        print "Example"
        print "python SendWrapper.py --public dest.public --private src.private --input content.txt --destURL http://localhost:8088 --org client1"
        return

    TMP_FILE = "tmp.enc.txt"
    SESSION_FILE = TMP_FILE + ".session"
    SIG_FILE = TMP_FILE + ".sig"
    ORG_FILE = options.org + ".org"
    ZIP_FILE = "tmp.zip"
        
    # Encrypt
    Encrypt(options.public, options.private, options.input, TMP_FILE)

    # Make Organisation file
    org_file = open(ORG_FILE, 'w')
    org_file.write('')
    org_file.close();
    
    # Make zip
    zip = zipfile.ZipFile(ZIP_FILE, 'w')
    zip.write(TMP_FILE)
    zip.write(SESSION_FILE)
    zip.write(SIG_FILE)
    zip.write(ORG_FILE)
    zip.close()
    
    # Send file
    zipHandle = open(ZIP_FILE, 'rb')
    data = {'file': zipHandle}
    r = requests.post(options.destURL, files=data)
    print r.text
    zipHandle.close()
    
    # Clean up
    if options.dontclean != True:
        os.remove(TMP_FILE)
        os.remove(SESSION_FILE)
        os.remove(SIG_FILE)
        os.remove(ORG_FILE)
        os.remove(ZIP_FILE)
        
        
if __name__ == "__main__":
    main()
