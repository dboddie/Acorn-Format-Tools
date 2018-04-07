#!/usr/bin/env python

"""
INF2UEF.py - Convert INF format files to UEF format using an index or the NEXT 
             parameters in the .inf files.

Copyright (c) 2000-2010, David Boddie <david@boddie.org.uk>

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

import gzip, os, string, sys
import cmdsyntax

def find_in_list(l, s):

    try:
        i = l.index(s)
    except ValueError:
        return -1
    
    return i


def number(size, n):

    # Little endian writing

    s = ""

    while size > 0:
        i = n % 256
        s = s + chr(i)
        n = n >> 8
        size = size - 1

    return s


def hex2num(s):

    n = 0

    for i in range(0,len(s)):

        a = ord(s[len(s)-i-1])
        if (a >= 48) & (a <= 57):
            n = n | ((a-48) << (i*4))
        elif (a >= 65) & (a <= 70):
            n = n | ((a-65+10) << (i*4))
        elif (a >= 97) & (a <= 102):
            n = n | ((a-97+10) << (i*4))
        else:
            sys.stderr.write("Bad hex: %s\n\n" % s)
            sys.exit(1)

    return n


def chunk(f, n, data):

    # Chunk ID
    f.write(number(2, n))
    # Chunk length
    f.write(number(4, len(data)))
    # Data
    f.write(data)


def rol(n, c):

    n = n << 1

    if (n & 256) != 0:
        carry = 1
        n = n & 255
    else:
        carry = 0

    n = n | c

    return n, carry


def crc(s):

    high = 0
    low = 0

    for i in s:

        high = high ^ ord(i)

        for j in range(0,8):

            a, carry = rol(high, 0)

            if carry == 1:
                high = high ^ 8
                low = low ^ 16

            low, carry = rol(low, carry)
            high, carry = rol(high, carry)

    return high | (low << 8)


def read_block(f, name, load, exe, length, n):

    block = f.read(256)

    # Write the alignment character
    out = "*"+name[:10]+"\000"

    # Load address
    out = out + number(4, load)

    # Execution address
    out = out + number(4, exe)

    # Block number
    out = out + number(2, n)

    # Block length
    out = out + number(2, len(block))

    # Block flag (last block)
    if f.tell() == length:
        out = out + number(1, 128)
        last = 1
    else:
        if len(block) == 256:
            out = out + number(1, 0)
            last = 0
        else:
            out = out + number(1, 128) # shouldn't be needed 
            last = 1 

    # Next address
    out = out + number(2, 0)

    # Unknown
    out = out + number(2, 0)

    # Header CRC
    out = out + number(2, crc(out[1:]))

    out = out + block

    # Block CRC
    out = out + number(2, crc(block))

    return out, last


if __name__ == "__main__":

    syntax = "[-c] <Directory> <UEF file>"
    version = "0.16c (Tue 15th April 2003)"
    
    syntax_obj = cmdsyntax.Syntax(syntax)
    
    matches, failed = syntax_obj.get_args(sys.argv[1:], return_failed = 1)
    
    if matches == [] and cmdsyntax.use_GUI() != None:
    
        form = cmdsyntax.Form("INF2UEF", syntax_obj, failed[0])
        
        matches = form.get_args()
    
    # Take the first match.
    if len(matches) > 0:
    
        match = matches[0]
    
    else:
    
        match = None
    
    if match == {} or match is None:
    
        sys.stderr.write("Syntax: INF2UEF.py %s\n\n" % syntax)
        sys.stderr.write("INF2UEF version %s\n\n" % version)
        sys.stderr.write("Take the files indexed in the directory given using the index.txt file and store\n")
        sys.stderr.write("them in the UEF file specified as tape files.\n\n")
        sys.stderr.write("If the -c flag is specified then the UEF file will be compressed in the form\n")
        sys.stderr.write("understood by gzip.\n\n")
        sys.exit(1)
    
    if sys.platform == "RISCOS":
        suffix = "/"
    else:
        suffix = "."
    
    # Determine whether the file needs to be compressed
    
    in_dir = match["Directory"]
    uef_file = match["UEF file"]
    
    if match.has_key("-c"):
    
        compress = 1
    else:
        compress = 0
    
    
    # See if there is an index file
    
    index_file = in_dir + os.sep + "index" + suffix + "txt"
    
    try:
        # Examine the index file
        lines = string.split(open(index_file, "r").read(), "\012")
    
        index = []
        real_names = []
        for i in lines:
    
            if i == "":
                break
    
            details = string.split(i)
            index.append(details[0])
            real_names.append(details[-1])
    
        no_index = 0
    except:
        no_index = 1
    
    # If there is no index then look at all the .inf files and determine the order
    # in which they are to be stored in the UEF file
    if no_index == 1:
    
        # List all the files
        files = os.listdir(in_dir)
    
        # Keep all the .inf files
        infs = []
        for i in files:
            if string.lower(i[-4:]) == (suffix+"inf"):
                infs.append(i)
    
        # Find the file which follows each file and the real name of the file
        nexts = []
        names = []
        for i in infs:
            # Read the .inf file
            details = string.split(open(in_dir+os.sep+i, "r").readline())
    
            # First entry may be the name of the file assuming $.name
            # or similar
            if string.find(details[0], ".") != -1:
                # Add the real name to the list of names
                names.append(details[0])
                details = details[1:]
            else:
                # Add the file name to the list of names
                names.append("$."+i)
    
            # Next two entries should be the load and execution addresses
            details = details[2:]
    
            if len(details) >= 2:
                # Next file should be the last two entries in the list
                if string.upper(details[-2]) == "NEXT":
                    # Next file
                    nexts.append(details[-1])
                elif string.upper(details[-1][:5]) == "NEXT=":
                    # Next file
                    nexts.append(details[-1][5:])
                else:
                    # No next file
                    nexts.append("")
    
            elif len(details) == 1:
                # Not enough entries for there to be a NEXT <file> entry
                # Add to the end of the list (could be the last file)
                if string.upper(details[-1][:5]) == "NEXT=":
                    # Next file
                    nexts.append(details[-1][5:])
                else:
                    nexts.append("")
            else:
                nexts.append("")
    
        # Determine the order of files
        index = []
        real_names = []
    
        # Insert files before the ones they specify as next files
        # Look through the .inf file list and real name list
        for i in range(0,len(infs)):
    
            # Determine which files precedes this one
            which = find_in_list(nexts, names[i])
            if which == -1:
                # No files precede this one
                index.insert(0, infs[i][:-4])
                real_names.insert(0, names[i])
            else:
                # Find the preceding file in the new
                # real names list
                which = find_in_list(real_names, names[which])
    
                if which != -1:
                    # File is there, so add this one after it
                    index.insert(which+1, infs[i][:-4])
                    real_names.insert(which+1, names[i])
                else:
                    # File is not (yet) present
    
                    # Determine whether there is a file following
                    # this one
                    if nexts[i] != "":
    
                        # Is the file in the new list?
                        which = find_in_list(real_names, nexts[i])
            
                        if which != -1:
                            # Insert this file before the file in question
                            index.insert(which, infs[i][:-4])
                            real_names.insert(which, names[i])
                        else:
                            # File isn't in the new list
                            index.append(infs[i][:-4])
                            real_names.append(names[i])
    
                    else:
                        # No files follow this one
                        index.append(infs[i][:-4])
                        real_names.append(names[i])
    
    
    
    # Create the UEF file
    
    try:
        if compress == 1:
            uef = gzip.open(uef_file, "wb")
        else:
            uef = open(uef_file, "wb")
    except:
        sys.stderr.write("Couldn't open the UEF file, %s\n" % uef_file)
        sys.exit(1)
    
    # Write the UEF file header
    
    uef.write("UEF File!\000")
    
    # Minor and major version numbers
    
    uef.write(number(1, 6) + number(1, 0))
    
    # Begin writing chunks
    
    # Creator chunk
    
    we_are = "INF2UEF "+version+"\000"
    if (len(we_are) % 4) != 0:
        we_are = we_are + ("\000"*(4-(len(we_are) % 4)))
    
    # Write this program's details
    chunk(uef, 0, we_are)
    
    
    # Platform chunk
    
    chunk(uef, 5, number(1, 1))    # Electron with any keyboard layout
    
    
    # Specify tape chunks
    
    chunk(uef, 0x110, number(2,0x05dc))
    chunk(uef, 0x100, number(1,0xdc))
    
    
    # Read the index
    
    for i in range(0,len(index)):
    
        file_name = index[i]
        real_name = real_names[i]
        if real_name[:2] == "$.":
            real_name = real_name[2:]
    
        details = []
        try:
            details = string.split(open(in_dir + os.sep + file_name + suffix + "inf", "r").readline())
        except IOError:
            try:
                details = string.split(open(in_dir + os.sep + file_name + suffix + "INF", "r").readline())
            except IOError:
                sys.stderr.write("Couldn't find file,\n", file_name+suffix+"inf", "or", file_name+suffix+"INF")
    
        if details != []:
            try:
                in_file = open(in_dir + os.sep + file_name, "rb")
                in_file.seek(0, 2)
                length = in_file.tell()
                in_file.seek(0, 0)
    
                if string.find(details[0], ".") != -1:
                    load, exe = details[1], details[2]
                else:
                    load, exe = details[0], details[1]
    
    #            if (details[0] == file_name) | (details[0] == "$."+file_name):
    #                load, exe = details[1], details[2]
    #            else:
    #                load, exe = details[0], details[1]
        
                try:
                    load = hex2num(load)
                    exe = hex2num(exe)
                except:
                    sys.stderr.write("Problem with file: %s\n" % (in_dir + os.sep + file_name))
                    sys.stderr.write("Information file may be incorrect.\n")
                    sys.exit(1)
        
                # Reset the block number to zero
                n = 0
        
                # Long gap
                gap = 1
            
                # Write block details
                while 1:
                    block, last = read_block(in_file, real_name, load, exe, length, n)
            
                    if gap == 1:
                        chunk(uef, 0x110, number(2,0x05dc))
                        gap = 0
                    else:
                        chunk(uef, 0x110, number(2,0x0258))
    
                    # Write the block to the UEF file
                    chunk(uef, 0x100, block)
        
                    if last == 1:
                        break
        
                    # Increment the block number
                    n = n + 1
        
                # Close the file
                in_file.close()
        
            except IOError:
                sys.stderr.write("Couldn't find file,\n", file_name)
    
    
    
    # Write some finishing bytes to the file
    chunk(uef, 0x110, number(2,0x0258))
    chunk(uef, 0x112, number(2,0x0258))
    
    
    # Close the UEF file
    uef.close()
    
    # Exit
    sys.exit()
