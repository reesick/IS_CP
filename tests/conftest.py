import os
import tempfile
os.environ['IMAGESHIELD_DATA']=tempfile.mkdtemp(prefix='imageshield-tests-')
os.environ['IMAGESHIELD_PERSISTENT_ML']='false'
