#!/usr/bin/env python

"""
Copyright (C) 2015 David Boddie <david@boddie.org.uk>

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

__author__ = "David Boddie <david@boddie.org.uk>"
__date__ = "2016-12-12"
__version__ = "0.2"
__license__ = "GNU General Public License (version 3 or later)"

import sys
from tools import makedfs, UEFfile

if __name__ == "__main__":

    if not 3 <= len(sys.argv) <= 4:
        sys.stderr.write("Usage: %s <ssd file> <uef file> [file0,...]\n" % sys.argv[0])
        sys.stderr.write("Usage: %s -l <ssd file>\n" % sys.argv[0])
        sys.exit(1)
    
    if sys.argv[1] == "-l":
        print_catalogue = True
        ssd_file = sys.argv[2]
    else:
        print_catalogue = False
        ssd_file = sys.argv[1]
        uef_file = sys.argv[2]
    
    cat = makedfs.Catalogue(open(ssd_file))
    if ssd_file.endswith(".dsd"):
        cat.interleaved = True
    
    title, disk_files = cat.read()
    
    if print_catalogue:
        max_length = 0
        for file in disk_files:
            max_length = max(max_length, len(repr(file.name)))
        
        print repr(title)
        for file in disk_files:
            spacing = " " * (max_length - len(repr(file.name)))
            print repr(file.name), spacing + "%08x %08x %x" % (
                file.load_address, file.execution_address, file.length)
        
        sys.exit()
    
    if len(sys.argv) == 4:
        names = sys.argv[3].split(",")
    else:
        names = []
        for file in disk_files:
            names.append(file.name)
    
    index = {}
    for file in disk_files:
        index[file.name] = file
    
    files = []
    for name in names:
        try:
            file = index[name]
        except KeyError:
            sys.stderr.write("File '%s' not found in the disk catalogue.\n" % name)
            sys.exit(1)
        
        if "$." in name:
            name = name.split(".")[-1]
        info = (name, file.load_address, file.execution_address, file.data)
        files.append(info)
    
    u = UEFfile.UEFfile(creator = "SSD2UEF.py " + __version__)
    u.minor = 6
    u.target_machine = "Electron"
    u.import_files(0, files, gap = True)
    
    u.write(uef_file, write_emulator_info = False)
    sys.exit()
