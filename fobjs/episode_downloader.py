
import urllib2
import time
import sys
import os
from gi.repository import GObject

class Downloader(GObject.GObject):
    __gsignals__ = {
        'download-status': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, 
                            (GObject.TYPE_PYOBJECT,)),
        'download-done': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, 
                          (GObject.TYPE_PYOBJECT,)),
    }
    def __init__(self):
        GObject.GObject.__init__(self)
        self.files = []
        self.downloading = False
        GObject.timeout_add(3000, self.check_download_cue)

    def check_download_cue(self):
        if not self.files or self.downloading:
            return True

        while self.files:
            self.downloading = self.files.pop(0)
            self.download(self.downloading['url'], self.downloading['dst'])

        self.downloading = False
        return True

    def append(self, url, dst):
        if os.path.exists(dst):
            return 

        self.files.append({"url":url, "dst":dst})

    def download(self, url, dst):
        if os.path.exists(dst):
            return

        tmp_dst = dst+".tmp"
        if os.path.exists(tmp_dst):
            size = os.path.getsize(tmp_dst)
            time.sleep(1)
            if (size != os.path.getsize(tmp_dst)):
                return

        basename = os.path.basename(dst)
        file_name = tmp_dst

        try:
            u = urllib2.urlopen(url)
        except urllib2.HTTPError, e:
            print "UNABLE TO DOWNLOAD:",url
            print "urllib2.HTTPError:",e
            return
        f = open(tmp_dst, 'wb')
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        print "Downloading: %s Bytes: %s" % (tmp_dst, file_size)

        file_size_dl = 0
        block_sz = 8192
        last_update = int(time.time())
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
        self.emit("download-status", "%s\n%s" % (basename, status))
        bytes_sec = 0
        while True:
            buff = u.read(block_sz)
            if not buff:
                break

            file_size_dl += len(buff)
            bytes_sec += len(buff)
            f.write(buff)
            time_time = int(time.time())

            if time_time != last_update:
                self.print_status(file_size_dl, file_size, bytes_sec, basename)
                last_update = time_time
                bytes_sec = 0

        f.close()
        os.rename(tmp_dst, dst)
        status = self.print_status(file_size_dl, file_size, bytes_sec, 
                                   basename, clear=False)
        
        self.emit("download-done", "Done downloading:%s\n%s" % (
            basename, status))

    def print_status(self, file_size_dl, file_size, bytes_sec, basename, 
                     clear=True):
        percent = (file_size_dl * 100.0) / file_size
        status = r"%10d  [%3.2f%%] %s/sec" % (
            file_size_dl, 
            percent,
            sizeof_fmt(bytes_sec)
        )
        self.emit("download-status", "%s\n%s" % (basename, status))
        if clear:
            status = status + chr(8)*(len(status)+1)
        print status,
        sys.stdout.flush()
        return status


def sizeof_fmt(num):
    for x in ['bytes','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%3.2f %s" % (num, x)
        num /= 1024.0


downloader = Downloader()

