# pycrypto required
# If windows, you need to download binary build of pycrypto (google for it) something like voidspace
# http://www.voidspace.org.uk/python/modules.shtml

from Crypto.Hash import MD5
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto import Random

import base64
import os
from optparse import OptionParser


BLOCK_SIZE = 32 # AES must be 32
PADDING = ' '
# one-liner to sufficiently pad the text to be encrypted
pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING
# one-liners to encrypt/encode and decrypt/decode a string
# encrypt with AES, encode with base64
EncodeAES = lambda c, s: base64.b64encode(c.encrypt(pad(s)))
DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(PADDING)


def readfile(filename):
    f = open(filename, 'rb')
    result = f.read()
    f.close()
    return result   
    
def make_key():
    rng = Random.new().read
    RSAkey = RSA.generate(1024, rng)
    return RSAkey
    
def save_key(key, filename):
    f = open(filename, 'wb')
    f.write(key.exportKey())
    f.flush()
    f.close()
    
def make_encryption(msg, key_src, pub_dest):
    # Algorithm
    # 1. src signs the hash (ensure that src is really who they are)
    # 2a. Make a temp session key
    # 2b. Encrypt message using symetrical algoritm using session key (because it is faster)
    # 3. encrypt session key with dest public (ensure only destination is allowed to get session key and therefore message)
    
    
    # 1. src signs the hash
    hash = MD5.new(msg).digest()
    rng = Random.new().read
    signature = key_src.sign(hash, rng)
    
    # 2a. Make a temp session key by randomly creating a 32 char long string
    import random, string
    var = ''.join(random.choice(string.ascii_uppercase) for x in range(BLOCK_SIZE))
    session_key = var.zfill(BLOCK_SIZE) # fills it up to 32 bytes
    cipher = AES.new(session_key)
    
    # 2b. Encrypt using session key
    encoded_msg = EncodeAES(cipher, msg)
    
    # 3. Encrypt session key with dest public
    encoded_key = pub_dest.encrypt(session_key, rng)
    
    return signature, encoded_msg, encoded_key
    
def make_decryption(pub_src, key_dest, signature, encoded_msg, encoded_key):
    # Algorithm
    # 1. Get session key back using dest private key
    # 2. Get message back with session key
    # 3a. Get hash of message
    # 3b. Verify hash against sig (Success means both parties are who they are)

    # 1. Get session key back
    session_key = key_dest.decrypt(encoded_key)
    
    # 2. Get message back with session key
    cipher = AES.new(session_key)
    decoded_msg = DecodeAES(cipher, encoded_msg)
    
    # 3a. Get hash of message
    hash = MD5.new(decoded_msg).digest()

    # 3b. Verify hash against sig
    success = pub_src.verify(hash, signature)
    
    return decoded_msg, success

def Encrypt(public_file, private_file, input_file, output_file):
    publicContents = readfile(public_file)
    privateContents = readfile(private_file)
    
    pub_key = RSA.importKey(publicContents)
    pri_key = RSA.importKey(privateContents)
    
    msg = readfile(input_file)
    
    signature, encoded_msg, encoded_key = make_encryption(msg, pri_key, pub_key)
    
    print "Writing %s" % output_file
    f_msg = open(output_file, 'wb')
    f_msg.write(encoded_msg)
    f_msg.close()
    
    print "Writing %s.session" % output_file
    f_session = open(output_file + '.session', 'wb')
    f_session.write(encoded_key[0]) # Returned as a () array of one element string
    f_session.close()
    
    print "Writing %s.sig" % output_file
    f_sig = open(output_file + '.sig', 'wb')
    f_sig.write(str(signature[0])) # Returned as a () array of one element long
    f_sig.close()
    
def Decrypt(public_file, private_file, input_file, output_file):
    publicContents = readfile(public_file)
    privateContents = readfile(private_file)
    
    pub_key = RSA.importKey(publicContents)
    pri_key = RSA.importKey(privateContents)

    encoded_msg = readfile(input_file)
    sessionContents = readfile(input_file + '.session')
    encoded_key = (sessionContents,)
    sigContents = readfile(input_file + '.sig')
    signature = (long(sigContents),)
    
    decoded_msg, success = make_decryption(pub_key, pri_key, signature, encoded_msg, encoded_key)

    if success == 1:
        f = open(output_file, 'w')
        f.write(decoded_msg)
        f.close()
    else:
        raise Exception("Error in decrypting!")
    
    
def main():
    parser = OptionParser()
    parser.add_option("-c", "--createkey", action="store_true", dest="createkey", help="Set to create key mode")
    parser.add_option("--keyname", dest="keyname", help="Create key mode only: The prefix name of keys. (name).public and (name).private are made")
    parser.add_option("-e", "--encrypt", action="store_true", dest="encrypt", help="Set to encryption mode")
    parser.add_option("-d", "--decrypt", action="store_true", dest="decrypt", help="Set to decryption mode")
    parser.add_option("--public", dest="public", help="Encryption/Decryption mode only: Filename of public key (dest / src)")
    parser.add_option("--private", dest="private", help="Encryption/Decryption mode only: Filename of private key (src / dest)")
    parser.add_option("--input", dest="input", help="Encryption/Decryption mode only: Filename of input file to encrypt/decrypt")
    parser.add_option("--output", dest="output", help="Encryption/Decryption mode only: Filename of output file to encrypt/decrypt")
    options, args = parser.parse_args()

    if options.createkey == True:
        print "Create key mode"
        if options.keyname is None:
            print "Create key mode: Use --keyname to specify the file prefix to save"
            return
        prefix = options.keyname
        key = make_key()
        save_key(key, prefix + '.private')
        save_key(key, prefix + '.public')
    elif options.encrypt == True:
        print "Encrypt mode"
        if options.public is None or options.private is None or options.input is None or options.output is None:
            print "Encrypt mode: you need to have all --public (filename) --private (filename) --input (filename) --output (filename) values"
            print "Encrypt mode: Public is the destination key, Private is the source key"
            print ""
            print "Example"
            print "python HVP_Encrypt.py -e --public dest.public --private src.private --input content.txt --output safe.txt"
            return
        
        Encrypt(options.public, options.private, options.input, options.output)
    elif options.decrypt == True:
        print "Decrypt mode"
        if options.public is None or options.private is None or options.input is None or options.output is None:
            print "Decrypt mode: you need to have all --public (filename) --private (filename) --input (filename) --output (filename) values"
            print "Decrypt mode: Public is the source key, Private is the destination key"
            print ""
            print "Example"
            print "python HVP_Encrypt.py -d --public src.public --private dest.private --input safe.txt --output output.txt"
            return
        
        Decrypt(options.public, options.private, options.input, options.output)
    else:
        print "Run with -h for help"
        
    
    
if __name__ == "__main__":
    main()
    
    
