import string, time
import os, os.path
import sys
import zipfile
import shutil
import ConfigParser

from os import curdir, sep
from datetime import datetime


from Utils.HVP_Encryption import Decrypt

from pprint import pformat

#IS_DEBUG = True
IS_DEBUG = False

def application(environ, start_response):

    if environ['REQUEST_METHOD'] == 'GET':
        output = do_GET(environ, start_response);
    elif environ['REQUEST_METHOD'] == 'POST':
        output = do_POST(environ, start_response);
    else:
        start_response('405 Invalid Method')
        return
        
    # send results
    output_len = sum(len(line) for line in output)
    start_response('200 OK', [('Content-type', 'text/html'),
                              ('Content-Length', str(output_len))])
    return output



def do_GET(environ, start_response):
    output = ['Waiting to receive...']

    if IS_DEBUG:
        output.append('<pre>')
        output.append(pformat(environ))
        output.append('</pre>')

        output.append('<pre>')
        output.append(pformat(sys.path))
        output.append('</pre>')

    return output

def do_POST(environ, start_reponse):
    path = os.path.dirname(os.path.realpath(__file__))

    success = False

    try:
        # Get settings
        config = ConfigParser.RawConfigParser()
        config.read(os.path.join(path,'WebReceive.py.cfg'))
        # Fetch the parameters. Check if they exist. If not assume it needs relative path for now
        temp_dir = config.get('Conf', 'temp_dir')
        if os.path.exists(temp_dir) == False:
            temp_dir = os.path.join(path, temp_dir)
        public_key_dir = config.get('Conf', 'public_key_dir')
        if os.path.exists(public_key_dir) == False:
            public_key_dir = os.path.join(path, public_key_dir)
        private_key = config.get('Conf', 'private_key')
        if os.path.exists(private_key) == False:
            private_key = os.path.join(path, private_key)
        output_dir = config.get('Conf', 'output_dir')
        if os.path.exists(output_dir) == False:
            output_dir = os.path.join(path, output_dir)


        # Save the uploaded file
        upfilecontent = environ['wsgi.input'].read()
        now_string = str(datetime.utcnow()).replace('-', '').replace(' ', '').replace(':', '').replace('.', '')
        filename = os.path.join(path, temp_dir, now_string + '.zip')
        f = open(filename, 'wb')
        f.write(upfilecontent)
        f.close()

        # Unzip the file
        encrypted_file = ''
        organisation_file = ''
        zip = zipfile.ZipFile(filename, 'r')
        for name in zip.namelist():
            fullname = os.path.join(path, temp_dir, now_string, name)
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

        # Decrypt processing...
        org_hash = os.path.splitext(os.path.basename(organisation_file))[0]
        public_key = os.path.join(path, "keys/", org_hash + ".public")
        if os.path.exists(public_key) == False:
            raise Exception("Key does not exist %s" % public_key)
        output_file = os.path.join(path, output_dir, "%s_%s.xml" % (org_hash, now_string))
        Decrypt(public_key, private_key, encrypted_file, output_file)

        # Testing encrypting and decrypting of a lab site
        first_line = ''
        with open(output_file, 'r') as f:
            first_line = f.readline()

        if first_line == 'Test HVP Connectivity':
            os.remove(output_file) # remove the test file from output
            output = '<HTML>TEST POST SUCCESSFUL.</HTML>'
            success = True
        else:
            trans = HVP_Transaction()
            try:
                trans.parse(output_file)
                success = True
            except Exception, err:
                success = False
                raise err

        # Clean up
        os.remove(filename) # Remove uploaded zip file
        shutil.rmtree("%s/%s" % (temp_dir, now_string)) # Clean temp files


    except Exception, ex:
        print ex

    # If it failed, set the output to fail by overwriting the variable
    if success == False:
        output = ['<HTML>POST FAILED!</HTML>']

    return output

