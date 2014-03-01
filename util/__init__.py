import sys
import os
additional_path = os.path.realpath(os.path.join(sys.path[0], '..'))
if additional_path not in sys.path:
    print "additional_path:",additional_path
    sys.path.append(additional_path)

from wait_util import *
