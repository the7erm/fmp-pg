
import os
import sys
additional_path = os.path.realpath(os.path.join(sys.path[0], '..'))
if additional_path not in sys.path:
    sys.path.append(additional_path)

from init.__init__ import *
