################################################################################
# 
# Human Variome Database Portal.
#
# === License ===
#
# Last Author:   $Author: AlanLo $
# Last Revision: $Rev: 670 $
# Last Modified: $Date: 2013-09-05 14:57:10 +1000 (Thu, 05 Sep 2013) $ 
#
# === Description ===
# Receives file uploads via HTTP
#
#
################################################################################

import string,cgi,time
import os, os.path
import zipfile
import ConfigParser
import shutil

from os import curdir, sep
from datetime import datetime
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from Utils.HVP_Encryption import Decrypt
from Utils.HVP_Transaction import HVP_Transaction

class XmlReceiveServer(BaseHTTPRequestHandler): 

    def do_POST(self):
        config = ConfigParser.RawConfigParser()
        config.read('WebReceive.py.cfg')
        temp_dir = config.get('Conf', 'temp_dir')
        public_key_dir = config.get('Conf', 'public_key_dir')
        private_key = config.get('Conf', 'private_key')
        output_dir = config.get('Conf', 'output_dir')
       
        success = False
    
        global rootnode
        try:
            ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
            if ctype == 'multipart/form-data':
                query=cgi.parse_multipart(self.rfile, pdict)
            self.send_response(200)
            
            self.end_headers()
            upfilecontent = query.get('file')
            
            now_string = str(datetime.utcnow()).replace('-', '').replace(' ', '').replace(':', '').replace('.', '')
            filename = temp_dir + now_string + '.zip'
            print "File: %s received" % filename

            f = open(filename, 'wb')
            f.write(upfilecontent[0])
            f.close()
            
            # Unzip the file
            encrypted_file = ''
            organisation_file = ''
            zip = zipfile.ZipFile(filename, 'r')
            for name in zip.namelist():
                fullname = "%s/%s/%s" % (temp_dir, now_string, name)
                if os.path.splitext(name)[1] == '.txt':
                    encrypted_file = fullname
                elif os.path.splitext(name)[1] == '.org':
                    organisation_file = name
                dirname = os.path.dirname(fullname)
                if os.path.exists(dirname) == False:
                    os.makedirs(os.path.dirname(fullname)) # ensure path exists
                f = open(fullname, 'wb')
                f.write(zip.read(name))
                f.close()
            zip.close()
            
            org_hash = os.path.splitext(os.path.basename(organisation_file))[0]            
            public_key = "keys/%s.public" % org_hash
            if os.path.exists(public_key) == False:
                raise Exception("Key does not exist %s" % public_key)
            output_file = "%s/%s_%s.xml" % (output_dir, org_hash, now_string)
            Decrypt(public_key, private_key, encrypted_file, output_file)
            
            # Testing encrypting and decrypting of a lab site
            first_line = ''
            with open(output_file, 'r') as f:
                first_line = f.readline()
            
            if first_line == 'Test HVP Connectivity':
                os.remove(filename) # Remove uploaded zip file
                shutil.rmtree("%s/%s" % (temp_dir, now_string)) # Clean temp files
                os.remove(output_file) # remove the test file from output
                self.wfile.write("<HTML>TEST POST SUCCESSFUL.</HTML>");
                return
                
            trans = HVP_Transaction()
            try:
                trans.parse(output_file)
                success = True
            except Exception, err:
                print "Failed to parse! %s" % filename
                print err

            os.remove(filename) # Remove uploaded zip file
            shutil.rmtree("%s/%s" % (temp_dir, now_string)) # Clean temp files
                
        except Exception, instance:
            print instance
            pass

        if success == True:
            self.wfile.write("<HTML>POST OK.</HTML>");
        else:
            self.wfile.write("<HTML>POST FAILED!</HTML>");

def main():

    try:
        server = HTTPServer(('', 8088), XmlReceiveServer)
        print 'started httpserver...'
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'
        server.socket.close()

if __name__ == '__main__':
    main()

