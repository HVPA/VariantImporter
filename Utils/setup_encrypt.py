# This is for the generation of the encryption binary

from distutils.core import setup
import py2exe

setup(
    console=['HVP_Encryption.py'],
    options = {'py2exe': {'bundle_files': 1, 'compressed': True}},
    zipfile = None
)
