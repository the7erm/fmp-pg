#!/usr/bin/env python2

from __init__ import *
import glob
import netcast_fobj
import fobj
import os
from excemptions import CreationFailed

def clear_cache():
    history = fobj.recently_played(100)
    recent = []

    for h in history:
        if h['id_type'] == 'e':
            recent.append(h['id'])

    mask = os.path.join(cache_dir, "*")
    files = glob.glob(mask)
    for filename in files:
        filename = os.path.realpath(filename)
        try:
            nobj = netcast_fobj.Netcast_File(filename=filename, silent=True)
        except CreationFailed:
            continue

        if nobj.eid in recent:
            print "keeping (recently played):",filename
            continue

        if nobj.is_unlistened():
            print "keeping (unplayed):",filename
            continue
        
        if os.remove(filename):
            print "removed:",filename
        else:
            print "unable to remove:",filename

if __name__ == "__main__":
    clear_cache()
