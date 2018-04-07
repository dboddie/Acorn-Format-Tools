#! /usr/bin/python

"""
T2INF.py - Convert Slogger T2* files to files on a disc.

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

import sys, string, os
import cmdsyntax

def read_block(in_f):

    global eof
    
    # Read the alignment character
    align = in_f.read(1)

    if not align:
        eof = 1
        return ("", 0, 0, "", 0)

    align = ord(align)^90

    if align == 0x2b:
        eof = 1
        return ("", 0, 0, "", 0)

    # Default file attributes
    name = ""
    load = 0
    exec_addr = 0
    
    while 1:
        c = in_f.read(1)
        if not c:
            eof = 1
            return (name, 0, 0, "", 0)

        c = chr(ord(c)^90)

        if ord(c) == 0:
            break

        name = name + c


    load = (ord(in_f.read(1))^90)+((ord(in_f.read(1))^90) << 8)+((ord(in_f.read(1))^90) << 16)+((ord(in_f.read(1))^90) << 24)

    exec_addr = (ord(in_f.read(1))^90)+((ord(in_f.read(1))^90) << 8)+((ord(in_f.read(1))^90) << 16)+((ord(in_f.read(1))^90) << 24)

    block_number = (ord(in_f.read(1))^90)+((ord(in_f.read(1))^90) << 8)

    if verbose == 1:
        if block_number == 0:
            print
            print name,
        print string.upper(hex(block_number)[2:]),

    block_length = (ord(in_f.read(1))^90)+((ord(in_f.read(1))^90) << 8)

    if block_length==0:
        return (name, load, exec_addr, "", block_number)
    
    block_flag = ord(in_f.read(1))

    next_addr = (ord(in_f.read(1))^90)+((ord(in_f.read(1))^90) << 8)

    header_crc = (ord(in_f.read(1))^90)+((ord(in_f.read(1))^90) << 8)

    in_f.seek(2, 1)

    if list_files == 0:
        block = ""
        for i in range(0,block_length):
            byte = ord(in_f.read(1)) ^ 90
            block = block + chr(byte)
    else:
        in_f.seek(block_length, 1)
        block = ""
    
    block_crc = (ord(in_f.read(1))^90)+((ord(in_f.read(1))^90) << 8)
    
    return (name, load, exec_addr, block, block_number)


def get_leafname(path):

    pos = string.rfind(path, os.sep)
    if pos != -1:
        return path[pos+1:]
    else:
        return path


if __name__ == "__main__":

    version = "0.14c (Fri 3rd May 2002)"
    syntax = "(-l [-v] <tape file>) | ([-name <stem>] [-v] <tape file> <destination path>)"
    
    style = cmdsyntax.Style()
    style.expand_single = 0
    style.allow_single_long = 1
    
    if style.verify() == 0:
    
        sys.stderr.write("Internal problem: syntax style is inconsistent.\n")
        sys.exit(1)
    
    # Create a syntax object.
    syntax_obj = cmdsyntax.Syntax(syntax, style)
    
    matches, failed = syntax_obj.get_args(sys.argv[1:], style = style, return_failed = 1)
    
    if matches == [] and cmdsyntax.use_GUI() != None:
    
        form = cmdsyntax.Form("T2UEF", syntax_obj, failed[0])
        
        matches = form.get_args()
    
    # Take the first match.
    if len(matches) > 0:
    
        match = matches[0]
    
    else:
    
        match = None
    
    # If there are no macthes then print the help text.
    if match == {} or match is None:
    
        sys.stderr.write("Syntax: T2INF.py %s\n\n" % syntax)
        sys.stderr.write("T2INF version %s\n\n" % version)
        sys.stderr.write("This program attempts to decode a tape file, <tape file>, produced by the\n")
        sys.stderr.write("Slogger T2 series of ROMs for the Acorn Electron microcomputer and save the\n")
        sys.stderr.write("files contained to the directory given by <destination path>.\n")
        sys.stderr.write("The load and execution addresses, and the file lengths are written to .inf\n")
        sys.stderr.write("files corresponding to each file extracted.\n\n" )
        sys.stderr.write("The options perform the following functions:\n\n")
        sys.stderr.write("-l              Lists the names of the files as they are extracted.\n")
        sys.stderr.write("-name <stem>    Writes files without names in the format <stem><number>\n")
        sys.stderr.write("                with <number> starting at 1.\n")
        sys.stderr.write("-v              Verbose output.\n\n")
        sys.exit(1)
    
    # Determine the platform on which the program is running
    
    sep = os.sep
    
    if sys.platform == "RISCOS":
        suffix = "/"
    elif sys.platform == "DOS":
        suffix = "."
    else:
        suffix = "."
    
    # List files
    if match.has_key("l"):
        list_files = 1
    else:
        list_files = 0
        out_path = match["destination path"]
    
    # Verbose output
    if match.has_key("v"):
        verbose = 1
    else:
        verbose = 0
    
    # Stem for unknown filenames
    if match.has_key("name"):
    
        stem = match["stem"]
    else:
        stem = "noname"
    
    # Read the input file name.
    in_file = match["tape file"]
    
    
    # Open the input file
    try:
        in_f = open(in_file, "rb")
    except IOError:
        sys.stderr.write('The input file could not be found: %s\n' % in_file)
        sys.exit(1)
    
    if list_files == 0:
    
        # Get the leafname of the output path
        leafname = get_leafname(out_path)
    
        # See if the output directory exists
        try:
            os.listdir(out_path)
        except:
            try:
                os.mkdir(out_path)
                print "Created directory "+out_path
            except:
                sys.stderr.write('Directory already exists: %s\n' % leafname)
                sys.exit(1)
    
    in_f.seek(5, 1)        # Move to byte 5 in the T2 file
    
    eof = 0                # End of file flag
    out_file = ""          # Currently open file as specified in the block
    write_file = ""        # Write the file using this name
    file_length = 0        # File length
    first_file = 1
    
    # List of files already created
    created = []
    
    # Unnamed file counter
    n = 1
    
    while 1:
        # Read block details
        try:
            name, load, exec_addr, block, block_number = read_block(in_f)
        except IOError:
            sys.stderr.write("Unexpected end of file\n")
            sys.exit(1)
    
        if list_files == 0:
            # Not listing the filenames
    
            if eof == 1:
                # Close the current output file
                out.close()
        
                # Write the file length information to the relevant file
                inf.write(string.upper(hex(file_length)[2:]+"\n"))
                inf.close()
                break
        
        #    # Either force new file or name in block is not the current name used
        #    if (write_file=="") | (name != out_file):
        #
        #        # New file, so close the last one (if there was one)
        #        if write_file != "":
        #            # Close the current output file
        #            out.close()
        #
        #            # Write the file length information to the relevant file
        #            inf.write(string.upper(hex(file_length)[2:]+"\n"))
        #            inf.close()
        
            # New file (block number is zero) or no previous file
            if (block_number == 0) | (first_file == 1):
        
                # Set the new name of the file
                out_file = name
                write_file = name
        
                # Open the new file with the new name
        
                if (write_file in created):
                    write_file = write_file+"-"+str(n)
                    n = n + 1
        
                if (write_file == ""):
                    write_file = stem+str(n)
                    n = n + 1
        
                # New file, so close the last one (if there was one)
                if first_file == 0:
                    # Close the previous output file
                    out.close()
        
                    # Write the file length information and the NEXT parameter
                    # to the previous .inf file
                    inf.write(string.upper(hex(file_length)[2:]+"\tNEXT $."+write_file+"\n"))
                    inf.close()
                else:
                    first_file = 0
    
                # Reset the file length
                file_length = 0
    
                try:
                    out = open(out_path + sep + write_file, "wb")
                except IOError:
                    # Couldn't open the file
                    write_file = stem+str(n)
                    n = n + 1
                    try:
                        out = open(out_path + sep + write_file, "wb")
                    except IOError:
                        sys.stderr.write('Failed to open the file: %s\n' % (
                                out_path + sep + write_file))
                        sys.exit(1)
        
                # Add file to the list of created files
                created.append(write_file)
        
                try:
                    # Open information file
                    inf = open(out_path + sep + write_file + suffix + "inf", "w")
                except IOError:
                    sys.stderr.write('Failed to open the information file: %s\n' % (
                            out_path + sep + write_file + suffix + "inf"))
                    sys.exit(1)
        
                # Write the load and execution information to the relevant file
                inf.write( "$." + write_file + "\t" + string.upper(hex(load)[2:])+\
                           "\t" + string.upper(hex(exec_addr)[2:]) + "\t" )
        
    
            if block != "":
        
                # Write the block to the relevant file
                out.write(block)
        
                file_length = file_length + len(block)
        else:
            # Listing the filenames
            if eof == 1:
                break
    
            if (verbose == 0) & (block_number == 0):
                print name
    
    
    
    # Close the input file
    in_f.close()
    
    # Exit
    sys.exit()
