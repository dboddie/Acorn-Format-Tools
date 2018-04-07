#! /usr/bin/env python

"""
Copyright (c) 2000-2010, David Boddie

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


import os, string, sys
import ADFSlib

try:

    import cmdsyntax
    use_getopt = 0

except ImportError:

    import getopt
    use_getopt = 1


__version__ = "0.42 (Sun 29th August 2010)"

default_convert_dict = {"/": "."}


def read_cmdsyntax_input(argv, syntax):

    syntax_obj = cmdsyntax.Syntax(syntax)
    
    matches, failed = syntax_obj.get_args(argv[1:], return_failed = 1)
    
    if len(matches) != 1 and cmdsyntax.use_GUI() != None:
    
        form = cmdsyntax.Form("ADF2INF", syntax_obj, failed[0])
        
        matches = form.get_args()
    
    # Take the first match, if possible.
    if len(matches) > 0:
    
        match = matches[0]
    
    else:
    
        match = None
    
    return match


def read_getopt_input(argv):

    opts, args = getopt.getopt(argv[1:], "ldts:c:vh")
    
    match = {}
    
    opt_dict = {"-l": "list", "-d": "create-directory", "-t": "file-types", "-s": "separator",
                "-v": "verify", "-c": "convert", "-h": "help"}
    arg_list = ["ADF file", "destination path"]
    
    # Read the options specified.
    
    for opt, value in opts:
    
        if opt_dict.has_key(opt):
        
            match[opt_dict[opt]] = value or '1'
        
        else:
        
            return None
    
    # Read the remaining arguments.
    
    if match.has_key("help"):
    
        return None
    
    elif match.has_key("list"):
    
        if len(args) != 1:
        
            # For list operations, there should be one remaining argument.
            return None
    
    elif match.has_key("verify"):
    
        if len(args) != 1:
        
            # For verify operations, there should be one remaining argument.
            return None
    
    elif len(args) != 2:
    
        # For all other operations, there should be two remaining arguments.
        return None
    
    i = 0
    for arg in args:
    
        match[arg_list[i]] = arg
        i = i + 1
    
    if match == {}: match = None
    
    return match


if __name__ == "__main__":
    
    if use_getopt == 0:
    
        syntax = """
        \r( (-l | --list) [-t | --file-types] <ADF file> ) |
        \r
        \r( [-d | --create-directory]
        \r  [ (-t | --file-types) [(-s separator) | --separator=character] ]
        \r  [(-c convert) | --convert=characters]
        \r  [-m | --time-stamps]
        \r  <ADF file> <destination path> ) |
        \r
        \r( (-v | --verify) <ADF file> ) |
        \r
        \r(-h | --help)
        """
        
        match = read_cmdsyntax_input(sys.argv, syntax)
    
    else:
    
        syntax = "[-l] [-d] [-t] [-s separator] [-v] [-c characters] [-m] " + \
                 "<ADF file> <destination path>"
        match = read_getopt_input(sys.argv)
    
    if match == {} or match is None or \
        match.has_key("h") or match.has_key("help"):
    
        print "Syntax: ADF2INF.py " + syntax
        print
        print 'ADF2INF version ' + __version__
        print 'ADFSlib version ' + ADFSlib.__version__
        print
        print 'Take the files stored in the directory given and store them as files with'
        print 'corresponding INF files.'
        print
        print 'If the -l flag is specified then the catalogue of the disc will be printed.'
        print
        print "The -d flag specifies that a directory should be created using the disc's"
        print 'name into which the contents of the disc will be written.'
        print
        print "The -t flag causes the load and execution addresses of files to be"
        print "interpreted as file type information for files created on RISC OS."
        print "A separator used to append a suffix onto the file is optional and"
        print "defaults to the standard period character; e.g. myfile.fff"
        print
        print "The -s flag is used to specify the character which joins the file"
        print "name to the file type. This can only be specified when extracting"
        print "files from a disc image."
        print
        print "The -v flag causes the disc image to be checked for simple defects and"
        print "determines whether there are files and directories which cannot be"
        print "correctly located by this tool, whether due to a corrupted disc image"
        print "or a bug in the image decoding techniques used."
        print
        print "The -c flag allows the user to define a conversion dictionary for the"
        print "characters found in ADFS filenames. The format of the string used to"
        print "define this dictionary is a comma separated list of character pairs:"
        print
        print "    <src1><dest1>[,<src2><dest2>]..."
        print
        print "If no conversion dictionary is specified then a default dictionary will"
        print "be used. This is currently defined as"
        print
        print "    %s" % repr(default_convert_dict)
        print
        print "The -m flag determines whether the files extracted from the disc"
        print "image should retain their time stamps on the target system."
        print
        sys.exit()
    
    
    # Determine whether the file is to be listed
    
    listing = match.has_key("l") or match.has_key("list")
    use_name = match.has_key("d") or match.has_key("create-directory")
    filetypes = match.has_key("t") or match.has_key("file-types")
    use_separator = match.has_key("s") or match.has_key("separator")
    verify = match.has_key("v") or match.has_key("verify")
    convert = match.has_key("c") or match.has_key("convert")
    with_time_stamps = match.has_key("m") or match.has_key("time-stamps")
    
    adf_file = match["ADF file"]
    
    out_path = match.get("destination path", None)
    
    separator = match.get("separator", ",")
    
    if sys.platform == 'RISCOS':
        suffix = '/'
    else:
        suffix = '.'
    
    if filetypes == 0 or (filetypes != 0 and use_separator == 0):

        # Use the standard suffix separator for the current platform if
        # none is specified.    
        separator = suffix
    
    
    # Try to open the ADFS disc image file.
    
    try:
        adf = open(adf_file, "rb")
    except IOError:
        print "Couldn't open the ADF file: %s" % adf_file
        print
        sys.exit()
    
    
    if listing == 0 and verify == 0:
    
        try:
        
            # Create an ADFSdisc instance using this file.
            adfsdisc = ADFSlib.ADFSdisc(adf)
        
        except ADFSlib.ADFS_exception:
        
            print "Unrecognised disc image: %s" % adf_file
            sys.exit()
    
    elif listing != 0:
    
        try:
        
            # Create an ADFSdisc instance using this file.
            adfsdisc = ADFSlib.ADFSdisc(adf, verify = 1)
        
        except ADFSlib.ADFS_exception:
        
            print "Unrecognised disc image: %s" % adf_file
            sys.exit()
    
    else:
    
        # Verifying
        
        print "Verifying..."
        print
        
        try:
        
            # Create an ADFSdisc instance using this file.
            adfsdisc = ADFSlib.ADFSdisc(adf, verify = 1)
        
        except ADFSlib.ADFS_exception:
        
            print "Unrecognised disc image: %s" % adf_file
            sys.exit()
        
        adfsdisc.print_log(verbose = 1)
        
        # Exit
        sys.exit()
    
    
    if listing != 0:
    
        # Print catalogue
        print 'Contents of', adfsdisc.disc_name,':'
        print
        
        adfsdisc.print_catalogue(adfsdisc.files, adfsdisc.root_name, filetypes)
        
        print
        
        adfsdisc.print_log()
        
        # Exit
        sys.exit()
    
    
    # Make sure that the disc is put in a directory corresponding to the disc
    # name where applicable.
    
    if use_name != 0:
    
        # Place the output files on this new path.
        out_path = os.path.join(out_path, adfsdisc.disc_name)
    
    # If a list of conversions was specified then create a dictionary to
    # pass to the disc object's extraction method.
    if match.has_key("convert"):
    
        convert_dict = {}
        
        pairs = string.split(match["convert"])
        
        try:
        
            for pair in pairs:
            
                convert_dict[pair[0]] = pair[1]
        
        except IndexError:
        
            print "Insufficient characters in character conversion list."
            sys.exit()
    
    else:
    
        # Use a default conversion dictionary.
        convert_dict = default_convert_dict
    
    # Extract the files
    adfsdisc.extract_files(
        out_path, adfsdisc.files, filetypes, separator, convert_dict,
        with_time_stamps
        )
    
    # Exit
    sys.exit()
