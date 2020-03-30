#!/usr/bin/env python

"""
Copyright (C) 2019 David Boddie <david@boddie.org.uk>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os, sys
import makedfs

version = "1.0"

def error(message):

    sys.stderr.write(message + "\n")
    sys.exit(1)

if __name__ == "__main__":

    script = sys.argv[0]
    
    if sys.argv[1:] == ["-v"]:
    
        print "%s version %s\n" % (os.path.split(script)[1], version)
        sys.exit()
    
    elif len(sys.argv) < 3 or "-h" in sys.argv[1:]:
    
        error("Usage: %(script)s <DFS image file> <directory>\n"
              "       %(script)s -h\n"
              "       %(script)s -v" % {"script": script})
    
    ssd_file = sys.argv[1]
    out_dir = sys.argv[2]
    
    # Open the disk image.
    disk = makedfs.Disk()
    disk.open(open(ssd_file, 'rb'))
    
    catalogue = disk.catalogue()
    title, files = catalogue.read()
    
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    
    for file in files:
        if file.name.startswith("$."):
            name = file.name[2:]
        else:
            name = file.name
        
        print "Writing", name
        open(os.path.join(out_dir, name), 'wb').write(file.data)
    
    print "Written", out_dir

    # Exit
    sys.exit()
