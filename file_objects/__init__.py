
import os
import sys
additional_path = os.path.realpath(os.path.join(sys.path[0], '..'))
if additional_path not in sys.path:
    print "before:", sys.path
    print "additional_path:",additional_path
    sys.path.append(additional_path)
    print "after:", sys.path

from init.__init__ import *
import fobj
import local
import location
import netcast
import generic
