from distutils.core import setup
import py2exe, os, sys

sys.argv.append("py2exe")

setup(
    options = {'py2exe': {'bundle_files': 1, 'compressed': True}},
    windows = [{'script': 'chat.pyw'}],
    zipfile = None
)
