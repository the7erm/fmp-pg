import os
import hashlib

def calculate_file_fingerprint(filename):
    print "filename:",filename
    if not os.path.isfile(filename):
        return "NOT FILE"
    if not os.access(filename, os.R_OK):
        return "NOT READABLE"

    fp = open(filename, 'r')
    main = hashlib.sha512()
    front = hashlib.sha512()
    middle = hashlib.sha512()
    end = hashlib.sha512()
    size = os.path.getsize(filename)
    fingerprint_size = 128 * 1024
    data = fp.read(fingerprint_size)
    front.update(data)
    main.update(data)
    seek = int(size / 2)
    fp.seek(seek)
    data = fp.read(fingerprint_size)
    middle.update(data)
    main.update(data)
    seek = size - fingerprint_size
    if seek < 0:
        seek = 0
    fp.seek(seek)
    data = fp.read(fingerprint_size)
    end.update(data)
    main.update(data)
    main_fingerprint = main.hexdigest()
    front_fingerprint = front.hexdigest()
    middle_fingerprint = middle.hexdigest()
    end_fingerprint = end.hexdigest()
    fp.close()
    print "main fingerprint:", main_fingerprint
    print "front fingerprint:", front_fingerprint
    print "middle fingerprint:", middle_fingerprint
    print "end fingerprint:", end_fingerprint
    return main_fingerprint, front_fingerprint, middle_fingerprint, end_fingerprint
