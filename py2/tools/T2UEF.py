#! /usr/bin/python
"""
T2UEF.py - Convert Slogger T2 files to UEF format archives.

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

def number(size, n):

    # Little endian writing

    s = ""

    while size > 0:
        i = n % 256
        s = s + chr(i)
#        n = n / 256
        n = n >> 8
        size = size - 1

    return s


def chunk(f, n, data):

    # Chunk ID
    f.write(number(2, n))
    # Chunk length
    f.write(number(4, len(data)))
    # Data
    f.write(data)


def decode(s):

    new = ""

    for i in s:
        new = new + chr(ord(i)^90)

    return new


def read_block(in_f):

    block = ""
    gap = 0

    # Read the alignment character
    align = in_f.read(1)

    if not align:
        return "", 0

    block = block + chr(ord(align)^90)

    # Read the name

    while 1:
        c = in_f.read(1)
        if not c:
            return block, 0

        c = chr(ord(c)^90)

        block = block + c

        if ord(c) == 0:
            break


    # Load address
    block = block + decode(in_f.read(4))

    # Execution address
    block = block + decode(in_f.read(4))

    # Block number
    block = block + decode(in_f.read(2))

    block_number = ord(block[-2])+(ord(block[-1]) << 8)
    if block_number == 0:
        gap = 1

    # Block length
    block = block + decode(in_f.read(2))

    block_length = ord(block[-2])+(ord(block[-1]) << 8)

    # Block flag
    block = block + decode(in_f.read(1))

    # Next address
    block = block + decode(in_f.read(2))

    block = block + decode(in_f.read(2))

    # Header CRC
    block = block + decode(in_f.read(2))

    if block_length==0:
        return block, 0
    
    block = block + decode(in_f.read(block_length))

    # Block CRC
    block = block + decode(in_f.read(2))

    return block, gap


if __name__ == "__main__":

    syntax = "[-c] <Tape file> <UEF file>"
    version = "0.15c (Tue 15th April 2003)"
    
    syntax_obj = cmdsyntax.Syntax(syntax)
    
    matches, failed = syntax_obj.get_args(sys.argv[1:], return_failed = 1)
    
    if matches == [] and cmdsyntax.use_GUI() != None:
    
        form = cmdsyntax.Form("T2UEF", syntax_obj, failed[0])
        
        matches = form.get_args()
    
    # Take the first match.
    if len(matches) > 0:
    
        match = matches[0]
    
    else:
    
        match = None
    
    if match == {} or match is None:
    
        sys.stderr.write("Syntax: T2UEF.py %s\n\n" % syntax)
        sys.stderr.write("T2UEF version %s\n\n" % version)
        sys.stderr.write("Take the files stored in the T2* file given and store them in the UEF file\n")
        sys.stderr.write("specified as tape files.\n\n")
        sys.stderr.write("If the -c flag is specified then the UEF file will be compressed in the form\n")
        sys.stderr.write("understood by gzip.\n\n")
        sys.exit(1)
    
    # Determine whether the file needs to be compressed
    
    compress = match.has_key("c")
    
    # Read the input and output file names.
    
    t2_file = match["Tape file"]
    uef_file = match["UEF file"]
    
    try:
        t2 = open(t2_file, "rb")
    except:
        sys.stderr.write("Failed to open the tape file: %s\n" % t2_file)
        sys.exit(1)
    
    # Create the UEF file
    
    try:
        if compress:
            uef = gzip.open(uef_file, "wb")
        else:
            uef = open(uef_file, "wb")
    except:
        sys.stderr.write("Failed to open the UEF file: %s\n" % uef_file)
        sys.exit(1)
    
    # Write the UEF file header
    
    uef.write("UEF File!\000")
    
    # Minor and major version numbers
    
    uef.write(number(1, 6) + number(1, 0))
    
    # Begin writing chunks
    
    # Creator chunk
    
    we_are = "T2UEF "+version+"\000"
    if (len(we_are) % 4) != 0:
        we_are = we_are + ("\000"*(4-(len(we_are) % 4)))
    
    # Write this program's details
    chunk(uef, 0, we_are)
    
    # Platform chunk
    chunk(uef, 5, number(1, 1))    # Electron with any keyboard layout
    
    # Specify tape chunks
    chunk(uef, 0x110, number(2,0x05dc))
    chunk(uef, 0x100, number(1,0xdc))
    
    # Decode the T2* file
    t2.seek(5, 1)        # Move to byte 5 in the file
    
    # chunk(uef, 0x110, number(2,0x05dc))
    
    while 1:
        # Read block details
        block, gap = read_block(t2)
    
        if block == "":
            break
    
        # If this is the first block in a file then put in a long gap before it
        # - the preceding program may need time to complete running before it
        # attempts to load the next one
    
        if gap == 1:
            chunk(uef, 0x110, number(2,0x05dc))
        else:
            chunk(uef, 0x110, number(2,0x0258))
    
        # Write the block to the UEF file
        chunk(uef, 0x100, block)
    
    # Write some finishing bytes to the file
    chunk(uef, 0x110, number(2,0x0258))
    chunk(uef, 0x112, number(2,0x0258))
    
    # Close the T2* and UEF files
    t2.close()
    uef.close()
    
    # Exit
    sys.exit()
