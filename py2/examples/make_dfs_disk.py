#!/usr/bin/env python

"""
Copyright (C) 2018 David Boddie <david@boddie.org.uk>

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

import sys
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
    
    elif len(sys.argv) < 4 or "-h" in sys.argv[1:]:
    
        error("Usage: %(script)s <disk name> <file>... <new SSD file>\n"
              "       %(script)s -h\n"
              "       %(script)s -v" % {"script": script})
    
    disk_name = sys.argv[1]
    files = sys.argv[2:-1]
    ssd_file = sys.argv[-1]
    out_files = []
    
    for name in files:
    
        inf_name = name + ".inf"
        if not os.path.isfile(inf_name):
            error("File '%s' is missing corresponding information file: %s\n" % (name, inf_name))
        
        try:
            line = open(inf_name).readline().strip()
            dfs_name, load, exec_, length = line.split()
        
        except IOError:
            error("Failed to read file: %s" % inf_name)
        
        except ValueError:
            error("Invalid format in file: %s" % inf_name)
        
        try:
            load = int(load, 16)
            exec_ = int(exec_, 16)
            length = int(length, 16)
        
        except ValueError:
            error("Invalid hexadecimal value used in file: %s" % inf_name)
        
        try:
            data = open(name, "rb").read()
        except IOError:
            error("Failed to read file: %s" % name)
        
        out_files.append((dfs_name, load, exec_, data))
    
    # Write the files to a disk image.
    disk = makedfs.Disk()
    disk.new()
    
    catalogue = disk.catalogue()
    catalogue.boot_option = 3
    
    disk_files = []
    for name, load, exec_, data in out_files:
    
        if "." not in name:
            name = "$." + name
        
        disk_files.append(makedfs.File(name, data, load, exec_, len(data)))
    
    catalogue.write(disk_name, disk_files)
    
    disk.file.seek(0, 0)
    disk_data = disk.file.read()
    open(ssd_file, "wb").write(disk_data)
    
    print "Written", ssd_file

    # Exit
    sys.exit()
