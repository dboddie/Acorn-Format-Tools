#!/usr/bin/env python

"""
ADFSlib.py, a library for reading ADFS disc images.

Copyright (c) 2003-2011, David Boddie <david@boddie.org.uk>

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
__date__ = "Sun 29th August 2010"
__version__ = "0.42"
__license__ = "GNU General Public License (version 3)"


import os, string, struct, time


INFORM = 0
WARNING = 1
ERROR = 2

# Find the number of centiseconds between 1900 and 1970.
between_epochs = ((365 * 70) + 17) * 24 * 360000L


class Utilities:

    # Little endian reading
    
    def _read_signed_word(self, s):
    
        return struct.unpack("<i", s)[0]
    
    def _read_unsigned_word(self, s):
    
        return struct.unpack("<I", s)[0]
    
    def _read_signed_byte(self, s):
    
        return struct.unpack("<b", s)[0]
    
    def _read_unsigned_byte(self, s):
    
        return struct.unpack("<B", s)[0]
    
    def _read_unsigned_half_word(self, s):
    
        return struct.unpack("<H", s)[0]
    
    def _read_signed_half_word(self, s):
    
        return struct.unpack("<h", s)[0]
    
    def _str2num(self, size, s):
    
        i = 0
        n = 0
        while i < size:
        
            n = n | (ord(s[i]) << (i*8))
            i = i + 1
        
        return n
    
    def _binary(self, size, n):
    
        new = ""
        while (n != 0) & (size > 0):
        
            if (n & 1)==1:
                new = "1" + new
            else:
                new = "0" + new
            
            n = n >> 1
            size = size - 1
        
        if size > 0:
            new = ("0"*size) + new
        
        return new
    
    def _safe(self, s, with_space = 0):
    
        new = ""
        if with_space == 1:
            lower = 31
        else:
            lower = 32
        
        for i in s:
        
            if ord(i) <= lower:
                break
            
            if ord(i) >= 128:
                c = ord(i)^128
                if c > 32:
                    new = new + chr(c)
            else:
                new = new + i
        
        return new
    
    def _plural(self, msg, values, words):
    
        """Returns a message which takes into account the plural form of
        words in the original message, assuming that the appropriate
        form for negative numbers of items is the same as that for
        more than one item.
        
        values is a list of numeric values referenced in the message.
        words is a list of sequences of words to substitute into the
        message. This takes the form
        
            [ word_to_use_for_zero_items,
              word_to_use_for_one_item,
              word_to_use_for_two_or_more_items ]
        
        The length of the values and words lists must be equal.
        """
        
        substitutions = []
        
        for i in range(0, len(values)):
        
            n = values[i]
            
            # Each number must be mapped to a value in the range [0, 2].
            if n > 1: n = 2
            elif n < 0: n = 2
            
            substitutions.append(values[i])
            substitutions.append(words[i][n])
        
        return msg % tuple(substitutions)
    
    def _create_directory(self, path, name = None):
    
        elements = []
        
        while not os.path.exists(path) and path != "":
        
            path, file = os.path.split(path)
            
            elements.insert(0, file)
        
        if path != "":
        
            elements.insert(0, path)
        
        if name is not None:
        
            elements.append(name)
        
        # Remove any empty list elements or those containing a $ character.
        elements = filter(lambda x: x != '' and x != "$", elements)
        
        try:
        
            built = ""
            
            for element in elements:
            
                built = os.path.join(built, element)
                
                if not os.path.exists(built):
                
                    # This element of the directory does not exist.
                    # Create a directory here.
                    os.mkdir(built)
                    print 'Created directory:', built
                
                elif not os.path.isdir(built):
                
                    # This element of the directory already exists
                    # but is not a directory.
                    print 'A file exists which prevents a ' + \
                        'directory from being created: %s' % built
                    
                    return ""
        
        except OSError:
        
            print 'Directory could not be created: %s' % \
                string.join(elements, os.sep)
            
            return ""
        
        # Success
        return built
    
    def _convert_name(self, old_name, convert_dict):
    
        # Use the conversion dictionary to convert any forbidden
        # characters to accepted local substitutes.
        name = ""
        
        for c in old_name:
        
            if c in convert_dict.keys():
            
                name = name + convert_dict[c]
            
            else:
            
                name = name + c
        
        if self.verify and old_name != name:
        
            self.verify_log.append(
                ( WARNING,
                  "Changed %s to %s" % (old_name, name) )
                )
        
        return name


class ADFS_exception(Exception):

    pass


class ADFSdirectory:

    """directory = ADFSdirectory(name, files)
    
    The directory created contains name and files attributes containing the
    directory name and the objects it contains.
    """
    
    def __init__(self, name, files):
    
        self.name = name
        self.files = files
    
    def __repr__(self):
    
        return '<%s instance, "%s", at %x>' % (self.__class__, self.name, id(self))


class ADFSfile:

    """file = ADFSfile(name, data, load_address, execution_address, length)
    """
    
    def __init__(self, name, data, load_address, execution_address, length):
    
        self.name = name
        self.data = data
        self.load_address = load_address
        self.execution_address = execution_address
        self.length = length
    
    def __repr__(self):
    
        return '<%s instance, "%s", at %x>' % (self.__class__, self.name, id(self))
    
    def has_filetype(self):
    
        """Returns True if the file's meta-data contains filetype information."""
        return self.load_address & 0xfff00000 == 0xfff00000
    
    def filetype(self):
    
        """Returns the meta-data containing the filetype information.
        
        Note that a filetype can be obtained for all files, though it may not
        necessarily be valid. Use has_filetype() to determine whether the file
        is likely to have a valid filetype."""
        
        return "%03x" % ((self.load_address >> 8) & 0xfff)
    
    def time_stamp(self):
    
        """Returns the time stamp for the file as a tuple of values containing
        the local time, or an empty tuple if the file does not have a time stamp."""
        
        # RISC OS time is given as a five byte block containing the
        # number of centiseconds since 1900 (presumably 1st January 1900).
        
        # Convert the time to the time elapsed since the Epoch (assuming
        # 1970 for this value).
        date_num = struct.unpack("<Q",
            struct.pack("<IBxxx", self.execution_address, self.load_address & 0xff))[0]
        
        centiseconds = date_num - between_epochs
        
        # Convert this to a value in seconds and return a time tuple.
        try:
            return time.localtime(centiseconds / 100.0)
        except ValueError:
            return ()


class ADFSmap(Utilities):

    def __getitem__(self, index):
    
        return self.disc_map[index]
    
    def has_key(self, key):
    
        return self.disc_map.has_key(key)


class ADFSnewMap(ADFSmap):

    dir_markers = ('Hugo', 'Nick')
    root_dir_address = 0x800
    
    def __init__(self, header, begin, end, sectors, sector_size, record):
    
        self.header = header
        self.begin = begin
        self.end = end
        self.sectors = sectors
        self.sector_size = sector_size
        self.record = record
        
        self.free_space = self._read_free_space()
        self.disc_map = self._read_disc_map()
    
    def _read_disc_map(self):
    
        # See ADFS/EMaps.htm, ADFS/EFormat.htm and ADFS/DiscMap.htm for details.
        
        ### TODO: This needs to take into account multiple zones.
        
        disc_map = {}
        
        a = self.begin
        
        current_piece = None
        current_start = 0
        
        next_zone = self.header + self.sector_size
        
        # Copy the free space map.
        free_space = self.free_space[:]
        
        while a < self.end:
        
            # The next entry to be read will occur one byte after this one
            # unless one of the following checks override this behaviour.
            next = a + 1
            
            if (a % self.sector_size) < 4:
            
                # In a zone header. Not the first zone header as this
                # was already skipped when we started reading.
                next = a + 4 - (a % self.sector_size)
                
                # Set the next zone offset.
                next_zone = next_zone + self.sector_size
                
                # Reset the current piece and starting offset.
                current_piece = None
                current_start = 0
            
            elif free_space != [] and a >= free_space[0][0]:
            
                # In the next free space entry. Go to the entry following
                # it and discard this free space entry.
                next = free_space[0][1]
                
                free_space.pop(0)
                
                # Reset the current piece and starting offset.
                current_piece = None
                current_start = 0
            
            elif current_piece is None and (next_zone - a) >= 2:
            
                # If there is enough space left in this zone to allow
                # further fragments then read the next two bytes.
                value = self._read_unsigned_half_word(self.sectors[a:a+2])
                
                entry = value & 0x7fff
                
                # See ADFS/EAddrs.htm document for restriction on
                # the disc address and hence the file number.
                # i.e.the top bit of the file number cannot be set.
                
                if entry >= 1:
                
                    # Defects (1), files or directories (greater than 1)
                    next = a + 2
                    
                    # Define a new entry.
                    #print "Begin:", hex(entry), hex(a)
                    
                    if not disc_map.has_key(entry):
                    
                        # Create a new map entry if none exists.
                        disc_map[entry] = []
                    
                    if (value & 0x8000) == 0:
                    
                        # Record the file number and start of this fragment.
                        current_piece = entry
                        current_start = a
                    
                    else:
                    
                        # For an immediately terminated fragment, add the
                        # extents of the block to the list of pieces found
                        # and implicitly finish reading this fragment
                        # (current_piece remains None).
                        
                        start_addr = self.find_address_from_map(
                            a, self.begin, entry
                            )
                        end_addr = self.find_address_from_map(
                            next, self.begin, entry
                            )
                        
                        if [start_addr, end_addr] not in disc_map[entry]:
                        
                            disc_map[entry].append((start_addr, end_addr))
                
                else:
                
                    # Search for a valid file number.
                    # Should probably stop looking in this zone.
                    next = a + 1
            
            elif current_piece is not None:
            
                # In a piece being read.
                
                value = ord(self.sectors[a])
                
                if value == 0:
                
                    # Still in the block.
                    next = a + 1
                
                elif value == 0x80:
                
                    # At the end of the block.
                    next = a + 1
                    
                    # For relevant entries add the block to the list of
                    # pieces found.
                    start_addr = self.find_address_from_map(
                        current_start, self.begin, current_piece
                        )
                    end_addr = self.find_address_from_map(
                        next, self.begin, current_piece
                        )
                    
                    if [start_addr, end_addr] not in disc_map[current_piece]:
                    
                        disc_map[current_piece].append(
                            (start_addr, end_addr)
                            )
                    
                    # Look for a new fragment.
                    current_piece = None
                
                else:
                
                    # The byte found was unexpected - backtrack to the
                    # byte after the start of this block and try again.
                    #print "Backtrack from %s to %s" % (hex(a), hex(current_start+1))
                    
                    next = current_start + 1
                    current_piece = None
            
            # Move to the next relevant byte.
            a = next
        
        return disc_map
    
    def _read_free_space(self):
    
        free_space = []
        
        a = self.header
        
        while a < self.end:
        
            # The next zone starts a sector after this one.
            next_zone = a + self.sector_size
            
            a = a + 1
            
            # Start by reading the offset in bits from the start of the header
            # of the first item of free space in the map.
            offset = self._read_unsigned_half_word(self.sectors[a:a+2])
            
            # The top bit is apparently always set, so mask it off and convert
            # the result into bytes. * Not sure if this is the case for
            # entries in the map. *
            next = ((offset & 0x7fff) >> 3)
            
            if next == 0:
            
                # No more free space in this zone. Look at the free
                # space field in the next zone.
                a = next_zone
                continue
            
            # Update the offset to point to the free space in this zone.
            a = a + next
            
            while a < next_zone:
            
                # Read the offset to the next free fragment in this zone.
                offset = self._read_unsigned_half_word(self.sectors[a:a+2])
                
                # Convert this to a byte offset.
                next = ((offset & 0x7fff) >> 3)
                
                # Find the end of the free space.
                b = a + 1
                
                while b < next_zone:
                
                    c = b + 1
                    
                    value = self._read_unsigned_byte(self.sectors[b])
                    
                    if (value & 0x80) != 0:
                    
                        break
                    
                    b = c
                
                # Record the offset into the map of this item of free space
                # and the offset of the byte after it ends.
                free_space.append((a, c))
                
                if next == 0:
                
                    break
                
                # Move to the next free space entry.
                a = a + next
            
            # Whether we are at the end of the zone or not, move to the
            # beginning of the next zone.
            a = next_zone
        
        # Return the free space list.
        return free_space
    
    def read_catalogue(self, base):
    
        head = base
        p = 0
        
        dir_seq = self.sectors[head + p]
        dir_start = self.sectors[head+p+1:head+p+5]
        if dir_start not in self.dir_markers:
        
            if self.verify:
            
                self.verify_log.append(
                    (WARNING, 'Not a directory: %s' % hex(head))
                    )
            
            return '', []
        
        p = p + 5
        
        files = []
        
        while ord(self.sectors[head+p]) != 0:
        
            old_name = self.sectors[head+p:head+p+10]
            top_set = 0
            counter = 1
            for i in old_name:
                if (ord(i) & 128) != 0:
                    top_set = counter
                counter = counter + 1
            
            name = self._safe(self.sectors[head+p:head+p+10])
            
            load = self._read_unsigned_word(self.sectors[head+p+10:head+p+14])
            exe = self._read_unsigned_word(self.sectors[head+p+14:head+p+18])
            length = self._read_unsigned_word(self.sectors[head+p+18:head+p+22])
            
            inddiscadd = self._read_new_address(
                self.sectors[head+p+22:head+p+25]
                )
            newdiratts = self._read_unsigned_byte(self.sectors[head+p+25])
            
            if inddiscadd == -1:
            
                if (newdiratts & 0x8) != 0:
                
                    if self.verify:
                    
                        self.verify_log.append(
                            (WARNING, "Couldn't find directory: %s" % name)
                            )
                        self.verify_log.append(
                            (WARNING, "    at: %x" % (head+p+22))
                            )
                        self.verify_log.append( (
                            WARNING, "    file details: %x" % \
                            self._str2num(3, self.sectors[head+p+22:head+p+25])
                            ) )
                        self.verify_log.append(
                            (WARNING, "    atts: %x" % newdiratts)
                            )
                
                elif length != 0:
                
                    if self.verify:
                    
                        self.verify_log.append(
                            (WARNING, "Couldn't find file: %s" % name)
                            )
                        self.verify_log.append(
                            (WARNING, "    at: %x" % (head+p+22))
                            )
                        self.verify_log.append( (
                            WARNING,
                            "    file details: %x" % \
                            self._str2num(3, self.sectors[head+p+22:head+p+25])
                            ) )
                        self.verify_log.append(
                            (WARNING, "    atts: %x" % newdiratts)
                            )
                
                else:
                
                    # Store a zero length file. This appears to be the
                    # standard behaviour for storing empty files.
                    files.append(ADFSfile(name, "", load, exe, length))
            
            else:
            
                if (newdiratts & 0x8) != 0:
                
                    # Remember that inddiscadd will be a sequence of
                    # pairs of addresses.
                    
                    for start, end in inddiscadd:
                    
                        # Try to interpret the data at the referenced address
                        # as a directory.
                        
                        lower_dir_name, lower_files = \
                            self.read_catalogue(start)
                        
                        # Store the directory name and file found therein.
                        files.append(ADFSdirectory(name, lower_files))
                
                else:
                
                    # Remember that inddiscadd will be a sequence of
                    # pairs of addresses.
                    
                    file = ""
                    remaining = length
                    
                    for start, end in inddiscadd:
                    
                        amount = min(remaining, end - start)
                        file = file + self.sectors[start : (start + amount)]
                        remaining = remaining - amount
                    
                    file_obj = ADFSfile(name, file, load, exe, length)
                    # Store the SIN (System Internal Number) for debugging.
                    file_obj.addr = self._str2num(3, self.sectors[head+p+22:head+p+25])
                    files.append(file_obj)
            
            p = p + 26
        
        
        # Go to tail of directory structure (0x800 -- 0xc00)
        
        tail = head + self.sector_size
        
        dir_end = self.sectors[tail+self.sector_size-5:tail+self.sector_size-1]
        
        if dir_end not in self.dir_markers:
        
            if self.verify:
            
                self.verify_log.append(
                    ( WARNING,
                      'Discrepancy in directory structure: [%x, %x]' % \
                      ( head, tail ) )
                    )
            
            return '', files
        
        dir_name = self._safe(
            self.sectors[tail+self.sector_size-16:tail+self.sector_size-6]
            )
        
        parent = \
            self.sectors[tail+self.sector_size-38:tail+self.sector_size-35]
        
        dir_title = \
            self.sectors[tail+self.sector_size-35:tail+self.sector_size-16]
        
        if head == self.root_dir_address:
            dir_name = '$'
        
        endseq = self.sectors[tail+self.sector_size-6]
        if endseq != dir_seq:
        
            if self.verify:
            
                self.verify_log.append(
                    ( WARNING,
                      'Broken directory: %s at [%x, %x]' % \
                      (dir_title, head, tail) )
                    )
            
            return dir_name, files
        
        return dir_name, files
    
    def _read_new_address(self, s):
    
        # From the three character string passed, determine the address on the
        # disc.
        value = self._str2num(3, s)
        
        # This is a SIN (System Internal Number)
        # The bottom 8 bits are the sector offset + 1
        offset = value & 0xff
        if offset != 0:
            address = (offset - 1) * self.sector_size
        else:
            address = 0
        
        # The top 16 bits are the file number
        file_no = value >> 8
        
        # The pieces of the object are returned as a list of pairs of
        # addresses.
        pieces = self._find_in_new_map(file_no)
        
        if pieces == []:
            return -1
        
        # Ensure that the first piece of data is read from the appropriate
        # point in the relevant sector.
        pieces = pieces[:]
        pieces[0] = (pieces[0][0] + address, pieces[0][1])
        
        return pieces
    
    def _find_in_new_map(self, file_no):
    
        try:
        
            return self.disc_map[file_no]
        
        except KeyError:
        
            return []
    
    def find_address_from_map(self, addr, begin, entry):
    
        return ((addr - begin) * self.sector_size)


class ADFSbigNewMap(ADFSnewMap):

    dir_markers = ('Nick',)
    root_dir_address = 0xc8800
    
    def find_address_from_map(self, addr, begin, entry):
    
        # I can't remember where the rationale for this calculation
        # came from or where the necessary information was obtained.
        # It probably came from one of the WSS files, such as
        # Formats.htm or Formats2.htm which imply that the F format
        # uses 512 byte sectors (see the 0x200 value below) and
        # indicate that F format uses 4 zones rather than 1.
        
        upper = (entry & 0x7f00) >> 8
        
        if upper > 1:
            upper = upper - 1
        if upper > 3:
            upper = 3
        
        return ((addr - begin) - (upper * 0xc8)) * 0x200


class ADFSoldMap(ADFSmap):

    def _read_free_space(self):
    
        # Currently unused
        
        base = 0
        free_space = []
        p = 0
        while self.sectors[base+p] != 0:
        
            free.append(self._str2num(3, self.sectors[base+p:base+p+3]))
        
        name = self.sectors[self.sector_size-9:self.sector_size-4]
        
        disc_size = self._str2num(
            3, self.sectors[self.sector_size-4:self.sector_size-1]
            )
        
        checksum0 = self._read_unsigned_byte(self.sectors[self.sector_size-1])
        
        base = self.sector_size
        
        p = 0
        while self.sectors[base+p] != 0:
        
            free.append(self._str2num(3, self.sectors[base+p:base+p+3]))
        
        name = name + \
            self.sectors[base+self.sector_size-10:base+self.sector_size-5]
        
        disc_id = self._str2num(
            2, self.sectors[base+self.sector_size-5:base+self.sector_size-3]
            )
        
        boot = self._read_unsigned_byte(self.sectors[base+self.sector_size-3])
        
        checksum1 = self._read_unsigned_byte(self.sectors[base+self.sector_size-1])
        
        return free_space


class ADFSdisc(Utilities):

    """disc = ADFSdisc(file_handle, verify = 0)
    
    Represents an ADFS disc image stored in the file with the specified file
    handle. The image is not verified by default; pass True or another
    non-False value to request automatic verification of the disc format.
    
    If the disc image specified cannot be read successfully, an ADFS_exception
    is raised.
    
    The disc's name is recorded in the disc_name attribute; its type is
    recorded in the disc_type attribute. To obtain a human-readable description
    of the disc format call the disc_format() method.
    
    Once an ADFSdisc instance has been created, it can be used to access the
    contents of the disc image. The files attribute contains a list of objects
    from the disc's catalogue, including both directories and files,
    represented by ADFSdirectory and ADFSfile instances respectively.
    
    The contents of the disc can be extracted to a directory structure in the
    user's filing system with the extract_files() method.
    
    For debugging purposes, the print_catalogue() method prints the contents of
    the disc's catalogue to the console. Similarly, the print_log() method
    prints the disc verification log and can be used to show any disc errors
    that have been found.
    """
    
    _format_names = {"ads": "ADFS S format",
                     "adm": "ADFS M format",
                     "adl": "ADFS L format",
                     "adD": "ADFS D format",
                     "adE": "ADFS E format",
                     "adEbig": "ADFS F format"}
    
    def __init__(self, adf, verify = 0):
    
        # Log problems if the verify flag is set.
        self.verify = verify
        self.verify_log = []
        
        # Check the properties using the length of the file
        adf.seek(0,2)
        length = adf.tell()
        adf.seek(0,0)
        
        if length == 163840:
            self.ntracks = 40
            self.nsectors = 16
            self.sector_size = 256
            interleave = 0
            self.disc_type = 'ads'
            self.dir_markers = ('Hugo',)
        
        elif length == 327680:
            self.ntracks = 80
            self.nsectors = 16
            self.sector_size = 256
            interleave = 0
            self.disc_type = 'adm'
            self.dir_markers = ('Hugo',)
        
        elif length == 655360:
            self.ntracks = 160
            self.nsectors = 16        # per track
            self.sector_size = 256    # in bytes
            # Most L format discs are interleaved, but at least one is
            # sequenced.
            interleave = 1
            self.disc_type = 'adl'
            self.dir_markers = ('Hugo',)
        
        elif length == 819200:
        
            self.ntracks = 80
            self.nsectors = 10
            self.sector_size = 1024
            interleave = 0
            self.dir_markers = ('Hugo', 'Nick')
            
            format = self._identify_format(adf)
            
            if format == 'D':
            
                self.disc_type = 'adD'
            
            elif format == 'E':
            
                self.disc_type = 'adE'
            
            else:
                raise ADFS_exception, \
                    'Please supply a .adf, .adl or .adD file.'
        
        elif length == 1638400:
        
            self.ntracks = 80
            self.nsectors = 20
            self.sector_size = 1024
            interleave = 0
            self.disc_type = 'adEbig'
            self.dir_markers = ('Nick',)
        
        else:
            raise ADFS_exception, 'Please supply a .adf, .adl or .adD file.'
        
        # Read tracks
        self.sectors = self._read_tracks(adf, interleave)
        
        # Close the ADF file
        adf.close()
        
        # Set the default disc name.
        self.disc_name = 'Untitled'
        
        # Read the files on the disc.
        
        if self.disc_type == 'adD':
        
            # Find the root directory name and all the files and directories
            # contained within it.
            self.root_name, self.files = self._read_old_catalogue(0x400)
        
        elif self.disc_type == 'adE':
        
            # Read the disc name and map
            self.disc_name = self._safe(self._read_disc_info(), with_space = 1)
            
            # Find the root directory name and all the files and directories
            # contained within it.
            self.root_name, self.files = self.disc_map.read_catalogue(2*self.sector_size)
        
        elif self.disc_type == 'adEbig':
        
            # Read the disc name and map
            self.disc_name = self._safe(self._read_disc_info(), with_space = 1)
            
            # Find the root directory name and all the files and directories
            # contained within it. The 
            self.root_name, self.files = self.disc_map.read_catalogue((self.ntracks * self.nsectors/2 + 2) * self.sector_size)
        
        else:
        
            # Find the root directory name and all the files and directories
            # contained within it.
            self.root_name, self.files = self._read_old_catalogue(2*self.sector_size)
    
    def _identify_format(self, adf):
    
        """Returns a string containing the disc format for the disc image
        accessed by the file object, adf. This method is used to determine the
        format for 800K disc images (either D or E format).
        """
        
        # Look for a valid disc record when determining whether the disc
        # image represents an 800K D or E format floppy disc. First, the
        # disc image needs to be read.
        
        # Read all the data in the image. This will be overwritten
        # when the image is read properly.
        self.sectors = adf.read()
        
        # This will be done again for E format and later discs.
        
        self.disc_record = record = self._read_disc_record(4)
        
        # Define a checklist of criteria to satisfy.
        checklist = \
        {
            "Length field matches image length": 0,
            "Expected sector size (1024 bytes)": 0,
            "Expected density (double)": 0,
            "Root directory at location given": 0
        }
        
        # Check the disc image length.
        
        # Seek to the end of the disc image.
        adf.seek(0, 2)
        
        if record["disc size"] == adf.tell():
        
            # The record (if is exists) does not provide a consistent value
            # for the length of the image file.
            checklist["Length field matches image length"] = 1
        
        # Check the sector size of the disc.
        
        if record["sector size"] == 1024:
        
            # These should be equal if the disc record is valid.
            checklist["Expected sector size (1024 bytes)"] = 1
        
        # Check the density of the disc.
        
        if record["density"] == "double":
        
            # This should be a double density disc if the disc record is valid.
            checklist["Expected density (double)"] = 1
        
        # Check the data at the root directory location.
        
        adf.seek((record["root dir"] * record["sector size"]) + 1, 0)
        word = adf.read(4)
        
        if word == "Hugo" or word == "Nick":
        
            # A valid directory identifier was found.
            checklist["Root directory at location given"] = 1
        
        if self.verify:
        
            self.verify_log.append(
                (INFORM, "Checklist for E format discs:")
                )
            
            for key, value in checklist.items():
            
                self.verify_log.append(
                    (INFORM, "%s: %s" % (key, ["no", "yes"][value]))
                    )
        
        # If all the tests pass then the disc is an E format disc.
        if reduce(lambda a, b: a + b, checklist.values(), 0) == \
            len(checklist.keys()):
        
            if self.verify: self.verify_log.append((INFORM, "E format disc"))
            return "E"
        
        # Since there may not be a valid disc record for earlier discs
        # then anything other than full marks can be interpreted as
        # an indication that the disc is a D format disc. However, we
        # can perform a final test to check this.
        
        # Simple test for D and E formats: look for Hugo at 0x401 for D format
        # and Nick at 0x801 for E format
        adf.seek(0x401)
        word1 = adf.read(4)
        adf.seek(0x801)
        word2 = adf.read(4)
        adf.seek(0)
        
        if word1 == 'Hugo':
        
            if self.verify:
            
                self.verify_log.append(
                    ( INFORM,
                      "Found directory in typical place for the root " + \
                      "directory of a D format disc." )
                    )
            
            return 'D'
        
        elif word1 == 'Nick':
        
            if self.verify:
            
                self.verify_log.append(
                    ( INFORM,
                      "Found E-style directory in typical place for the root " + \
                      "directory of a D format disc." )
                    )
            
            return 'D'
        
        elif word2 == 'Nick':
        
            if self.verify:
            
                self.verify_log.append(
                    ( INFORM,
                      "Found directory in typical place for the root " + \
                      "directory of an E format disc." )
                    )
            
            return 'E'
        
        else:
        
            if self.verify:
            
                self.verify_log.append(
                    ( ERROR,
                      "Failed to find any information which would help " + \
                      "determine the disc format." )
                    )
            
            return '?'
    
    def _read_disc_record(self, offset):
    
        """Reads the disc record for D and E format disc images and returns a
        dictionary describing the disc image.
        """
        
        # See ADFS/DiscRecord.htm for details.
        
        # Total sectors per track (sectors * heads)
        log2_sector_size = ord(self.sectors[offset])
        # Sectors per track
        nsectors = ord(self.sectors[offset + 1])
        # Heads per track
        heads = ord(self.sectors[offset + 2])
        
        density = ord(self.sectors[offset+3])
        
        if density == 1:
        
            density = 'single'        # Single density disc
            sector_size = 256
        
        elif density == 2:
        
            density = 'double'        # Double density disc
            sector_size = 512
        
        elif density == 3:
        
            density = 'quad'        # Quad density disc
            sector_size = 1024
        
        else:
        
            density = 'unknown'
        
        # Length of ID fields in the disc map
        idlen = self._read_unsigned_byte(self.sectors[offset + 4])
        # Number of bytes per map bit.
        bytes_per_bit = 2 ** self._read_unsigned_byte(self.sectors[offset + 5])
        # LowSector
        # StartUp
        # LinkBits
        # BitSize (size of ID field?)
        bit_size = self._read_unsigned_byte(self.sectors[offset + 6 : offset + 7])
        #print "Bit size: %s" % hex(bit_size)
        # RASkew
        # BootOpt
        # Zones
        zones = ord(self.sectors[offset + 9])
        # ZoneSpare
        # RootDir
        root = self._str2num(3, self.sectors[offset + 13 : offset + 16]) # was 15
        # Identify
        # SequenceSides
        # DoubleStep
        # DiscSize
        disc_size = self._read_unsigned_word(self.sectors[offset + 16 : offset + 20])
        # DiscId
        disc_id   = self._read_unsigned_half_word(self.sectors[offset + 20 : offset + 22])
        # DiscName
        disc_name = string.strip(self.sectors[offset + 22 : offset + 32])
        
        return {'sectors': nsectors, 'log2 sector size': log2_sector_size,
            'sector size': 2**log2_sector_size, 'heads': heads,
            'density': density,
            'disc size': disc_size, 'disc ID': disc_id,
            'disc name': disc_name, 'zones': zones, 'root dir': root }
    
    def _read_disc_info(self):
    
        checksum = ord(self.sectors[0])
        first_free = self._read_unsigned_half_word(self.sectors[1:3])
        
        if self.disc_type == 'adE':
        
            self.record = self._read_disc_record(4)
            
            self.sector_size = self.record["sector size"]
            
            self.map_header = 0
            self.map_start, self.map_end = 0x40, 0x400
            self.disc_map = ADFSnewMap(self.map_header, self.map_start,
                                       self.map_end, self.sectors,
                                       self.sector_size, self.record)
            
            return self.record['disc name']
        
        elif self.disc_type == 'adEbig':
        
            self.record = self._read_disc_record(0xc6804)
            
            self.sector_size = self.record["sector size"]
            
            self.map_header = 0xc6800
            self.map_start, self.map_end = 0xc6840, 0xc7800
            self.disc_map = ADFSbigNewMap(self.map_header, self.map_start,
                                          self.map_end, self.sectors,
                                          self.sector_size, self.record)
            
            return self.record['disc name']
        
        else:
            return 'Unknown'
    
    def _read_tracks(self, f, inter):
    
        t = ""
        
        f.seek(0, 0)
        
        if inter==0:
            try:
                for i in range(0, self.ntracks):
                
                    t = t + f.read(self.nsectors * self.sector_size)
            
            except IOError:
                print 'Less than %i tracks found.' % self.ntracks
                f.close()
                raise ADFS_exception, \
                    'Less than %i tracks found.' % self.ntracks
        
        else:
        
            # Tracks are interleaved (0 80 1 81 2 82 ... 79 159) so rearrange
            # them into the form (0 1 2 3 ... 159)
            
            try:
            
                for i in range(0, self.ntracks):
                
                    if i < (self.ntracks >> 1):
                        f.seek(i*2*self.nsectors*self.sector_size, 0)
                        t = t + f.read(self.nsectors*self.sector_size)
                    else:
                        j = i - (self.ntracks >> 1)
                        f.seek(((j*2)+1)*self.nsectors*self.sector_size, 0)
                        t = t + f.read(self.nsectors*self.sector_size)
            
            except IOError:
            
                print 'Less than %i tracks found.' % self.ntracks
                f.close()
                raise ADFS_exception, \
                    'Less than %i tracks found.' % self.ntracks
        
        return t
    
    def _read_old_catalogue(self, base):
    
        head = base
        p = 0
        
        dir_seq = self.sectors[head + p]
        dir_start = self.sectors[head+p+1:head+p+5]
        if dir_start not in self.dir_markers:
        
            if self.verify:
            
                self.verify_log.append(
                    (WARNING, 'Not a directory: %x' % head)
                    )
            
            return "", []
        
        p = p + 5
        
        files = []
        
        while ord(self.sectors[head+p]) != 0:
        
            old_name = self.sectors[head+p:head+p+10]
            top_set = 0
            counter = 1
            for i in old_name:
                if (ord(i) & 128) != 0:
                    top_set = counter
                counter = counter + 1
            
            name = self._safe(self.sectors[head+p:head+p+10])
            
            load = self._read_unsigned_word(self.sectors[head+p+10:head+p+14])
            exe = self._read_unsigned_word(self.sectors[head+p+14:head+p+18])
            length = self._read_unsigned_word(self.sectors[head+p+18:head+p+22])
            
            if self.disc_type == 'adD':
                inddiscadd = 256 * self._str2num(
                    3, self.sectors[head+p+22:head+p+25]
                    )
            else:
                inddiscadd = self.sector_size * self._str2num(
                    3, self.sectors[head+p+22:head+p+25]
                    )
            
            olddirobseq = self._read_unsigned_byte(self.sectors[head+p+25])
            
            if self.disc_type == 'adD':
            
                # Old format 800K discs.
                if (olddirobseq & 0x8) == 0x8:
                
                    # A directory has been found.
                    lower_dir_name, lower_files = \
                        self._read_old_catalogue(inddiscadd)
                        
                    files.append(ADFSdirectory(name, lower_files))
                
                else:
                
                    # A file has been found.
                    data = self.sectors[inddiscadd:inddiscadd+length]
                    files.append(ADFSfile(name, data, load, exe, length))
            
            else:
            
                # Old format < 800K discs.
                # [Needs more accurate check for directories.]
                if (load == 0 and exe == 0 and top_set > 2) or \
                    (top_set > 0 and length == (self.sector_size * 5)):
                
                    # A directory has been found.
                    lower_dir_name, lower_files = \
                        self._read_old_catalogue(inddiscadd)
                    
                    files.append(ADFSdirectory(name, lower_files))
                
                else:
                
                    # A file has been found.
                    data = self.sectors[inddiscadd:inddiscadd+length]
                    files.append(ADFSfile(name, data, load, exe, length))
            
            p = p + 26
        
        
        # Go to tail of directory structure (0x200 -- 0x700)
        
        if self.disc_type == 'adD':
            tail = head + self.sector_size    # 1024 bytes
        else:
            tail = head + (self.sector_size*4)    # 1024 bytes
        
        dir_end = self.sectors[tail+self.sector_size-5:tail+self.sector_size-1]
        if dir_end not in self.dir_markers:
        
            if self.verify:
            
                self.verify_log.append(
                    ( WARNING,
                      'Discrepancy in directory structure: [%x, %x] ' % \
                      ( head, tail ) )
                    )
                        
            return '', files
        
        # Read the directory name, its parent and any title given.
        if self.disc_type == 'adD':
        
            dir_name = self._safe(
                self.sectors[tail+self.sector_size-16:tail+self.sector_size-6]
                )
            
            parent = 256*self._str2num(
                3,
                self.sectors[tail+self.sector_size-38:tail+self.sector_size-35]
                )
            
            dir_title = \
                self.sectors[tail+self.sector_size-35:tail+self.sector_size-16]
        else:
        
            dir_name = self._safe(
                self.sectors[tail+self.sector_size-52:tail+self.sector_size-42]
                )
            
            parent = self.sector_size*self._str2num(
                3,
                self.sectors[tail+self.sector_size-42:tail+self.sector_size-39]
                )
            
            dir_title = self._safe(
                self.sectors[tail+self.sector_size-39:tail+self.sector_size-20]
                )
        
        if parent == head:
        
            # Use the directory title as the disc name.
            
            # Note that the title may contain spaces.
            self.disc_name = self._safe(dir_title, with_space = 1)
        
        endseq = self.sectors[tail+self.sector_size-6]
        if endseq != dir_seq:
        
            if self.verify:
            
                self.verify_log.append(
                    ( WARNING,
                      'Broken directory: %s at [%x, %x]' % \
                      (dir_title, head, tail) )
                    )
            
            return dir_name, files
        
        return dir_name, files
    
    def print_catalogue(self, files = None, path = "$", filetypes = 0):
    
        """Prints the contents of the disc catalogue to standard output.
        Usually, this method is called without specifying any of the keyword
        arguments, but these can be used to customise the output.
        
        If files is None, the contents of the entire disc will be shown.
        A subset of the list of files obtained from the instance's files
        attribute can be passed if only a subset of the catalogue needs to
        be displayed.
        
        The path parameter specifies the representation of the root directory
        in the output. By default, root directories are represented by the
        familiar "$" symbol.
        
        If filetypes is set to True or a non-False value, the file types of
        each file will be displayed; otherwise, load and execution addresses
        will be displayed instead.
        """
        
        if files is None:
        
            files = self.files
        
        if files == []:
        
            print path, "(empty)"
        
        for obj in files:
    
            name = obj.name
            if isinstance(obj, ADFSfile):
            
                if not filetypes:
                
                    # Load and execution addresses treated as valid.
                    print string.expandtabs(
                        "%s.%s\t%X\t%X\t%X" % (
                            path, name, obj.load_address,
                            obj.execution_address, obj.length
                            ), 16
                        )
                
                else:
                
                    # Load address treated as a filetype; load and execution
                    # addresses treated as a time stamp.
                    
                    time_stamp = obj.time_stamp()
                    if not time_stamp or not obj.has_filetype():
                    
                        print string.expandtabs(
                            "%s.%s\t%X\t%X\t%X" % (
                                path, name, obj.load_address,
                                obj.execution_address, obj.length
                                ), 16
                            )
                    else:
                        time_stamp = time.strftime("%H:%M:%S, %a %d %b %Y", time_stamp)
                        print string.expandtabs(
                            "%s.%s\t%s\t%s\t%X" % (
                                path, name, obj.filetype().upper(), time_stamp,
                                obj.length
                                ), 16
                            )
            
            else:
            
                self.print_catalogue(obj.files, path + "." + name, filetypes)
    
    def _extract_old_files(self, objects, path, filetypes = 0, separator = ",",
                           convert_dict = {}, with_time_stamps = False):
    
        new_path = self._create_directory(path)
        
        if new_path != "":
        
            path = new_path
        
        else:
        
            return
        
        for obj in objects:
        
            old_name = obj.name
            
            name = self._convert_name(old_name, convert_dict)
            
            if isinstance(obj, ADFSfile):
            
                # A file.
                
                if not filetypes:
                
                    # Load and execution addresses assumed to be valid.
                    
                    # Create the INF file
                    out_file = os.path.join(path, name)
                    inf_file = os.path.join(path, name) + separator + "inf"
                    
                    try:
                        out = open(out_file, "wb")
                        out.write(obj.data)
                        out.close()
                    except IOError:
                        print "Couldn't open the file: %s" % out_file
                    
                    try:
                        inf = open(inf_file, "w")
                        inf.write("$.%s\t%X\t%X\t%X" % (
                            name, obj.load_address, obj.execution_address,
                            obj.length
                            ))
                        inf.close()
                    except IOError:
                        print "Couldn't open the file: %s" % inf_file
                
                else:
                
                    # Interpret the load address as a filetype.
                    out_file = os.path.join(path, name) + separator + obj.filetype()
                    
                    try:
                        out = open(out_file, "wb")
                        out.write(obj.data)
                        out.close()
                    except IOError:
                        print "Couldn't open the file: %s" % out_file
            else:
            
                new_path = os.path.join(path, name)
                
                self._extract_old_files(
                    obj.files, new_path, filetypes, separator, convert_dict
                    )
    
    def _extract_new_files(self, objects, path, filetypes = 0, separator = ",",
                           convert_dict = {}, with_time_stamps = False):
    
        new_path = self._create_directory(path)
        
        if new_path != "":
        
            path = new_path
        
        else:
        
            return
        
        for obj in objects:
        
            old_name = obj.name
            
            # Use the conversion dictionary to convert any forbidden
            # characters to accepted local substitutes.
            name = self._convert_name(old_name, convert_dict)
            
            if isinstance(obj, ADFSfile):
            
                # A file.
                
                if not filetypes:
                
                    # Load and execution addresses assumed to be valid.
                    
                    # Create the INF file
                    out_file = path + os.sep + name
                    inf_file = path + os.sep + name + separator + "inf"
                    
                    try:
                        out = open(out_file, "wb")
                        out.write(obj.data)
                        out.close()
                    except IOError:
                        print "Couldn't open the file: %s" % out_file
                    
                    try:
                        inf = open(inf_file, "w")
                        inf.write("$.%s\t%X\t%X\t%X" % (
                            name, obj.load_address, obj.execution_address,
                            obj.length
                            ))
                        inf.close()
                    except IOError:
                        print "Couldn't open the file: %s" % inf_file
                else:
                
                    # Interpret the load address as a filetype.
                    out_file = path + os.sep + name + separator + obj.filetype()
                    
                    try:
                        out = open(out_file, "wb")
                        out.write(obj.data)
                        out.close()
                    except IOError:
                        print "Couldn't open the file: %s" % out_file
            else:
            
                new_path = os.path.join(path, name)
                
                self._extract_new_files(
                    obj.files, new_path, filetypes, separator, convert_dict
                    )
    
    def extract_files(self, out_path, files = None, filetypes = 0,
                      separator = ",", convert_dict = {},
                      with_time_stamps = False):
    
        """Extracts the files stored in the disc image into a directory
        structure stored on the path specified by out_path.
        
        The files parameter specified a list of ADFSfile or ADFSdirectory
        instances to extract to the target file system. This keyword argument
        can be omitted if all files and directories in the disc image are to
        be extracted.
        
        If the filetypes keyword argument is set to True, or another non-False
        value, file type suffixes are appended to each file created using the
        separator string supplied to join the file name to the file type.
        
        The convert_dict parameter can be used to specify a mapping between
        characters used in ADFS file names and those on the target file system.
        
        If with_time_stamps is set, each extracted file will be given the time
        stamp on the target file system that it has in the disc image.
        """
        
        if files is None:
        
            files = self.files
        
        if self.disc_type == 'adD':
        
            self._extract_old_files(
                files, out_path, filetypes, separator, convert_dict,
                with_time_stamps
                )
        
        elif self.disc_type == 'adE':
        
            self._extract_new_files(
                files, out_path, filetypes, separator, convert_dict,
                with_time_stamps
                )
        
        elif self.disc_type == 'adEbig':
        
            self._extract_new_files(
                files, out_path, filetypes, separator, convert_dict,
                with_time_stamps
                )
        
        else:
        
            self._extract_old_files(
                files, out_path, filetypes, separator, convert_dict,
                with_time_stamps
                )
    
    def print_log(self, verbose = 0):
    
        """Prints the disc verification log. Any purely informational messages
        are only printed if verbose is set to 1.
        """
        
        if hasattr(self, "disc_map") and self.disc_map.has_key(1):
        
            print self._plural(
                "%i mapped %s found.", [len(self.disc_map[1])],
                [("defects", "defect", "defects")]
                )
        
        # Count the information, warning and error messages in the log.
        informs = reduce(lambda a, b: a + (b[0] == INFORM), self.verify_log, 0)
        warnings = reduce(
            lambda a, b: a + (b[0] == WARNING), self.verify_log, 0
            )
        errors = reduce(lambda a, b: a + (b[0] == ERROR), self.verify_log, 0)
        
        if (warnings + errors) == 0:
        
            print "All objects located."
            if not verbose: return
        
        if self.verify_log != []:
        
            print
        
        for msgtype, line in self.verify_log:
        
            print line
    
    def disc_format(self):
    
        return self._format_names[self.disc_type]
