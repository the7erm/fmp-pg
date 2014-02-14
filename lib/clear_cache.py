#!/usr/bin/env python2

from __init__ import *
import glob
import netcast_fobj
import fobj
import os
from excemptions import CreationFailed

def clear_cache():
    history = fobj.recently_played(10)
    recent = []

    for h in history:
        if h['id_type'] == 'e':
            recent.append(h['id'])

    mask = cache_dir+"/*"
    files = glob.glob(mask)
    for f in files:
        f = os.path.realpath(f)
        try:
            nobj = netcast_fobj.Netcast_File(filename=f, silent=True)
        except CreationFailed:
            continue

        if nobj.is_unlistened():
            print "keeping (unplayed):",f
            continue

        if nobj.eid in recent:
            print "keeping (recently played):",f
            continue

        
        if os.remove(f):
            print "removed:",f
        else:
            print "unable to remove:",f

if __name__ == "__main__":
    clear_cache()
