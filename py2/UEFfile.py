#!/usr/bin/env python

"""
UEFfile.py - Handle UEF archives.

Copyright (c) 2001-2013, David Boddie <david@boddie.org.uk>

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

import exceptions, sys, string, os, gzip, types

class UEFfile_error(exceptions.Exception):

    pass

# Determine the platform on which the program is running

sep = os.sep

if sys.platform == 'RISCOS':
    suffix = '/'
else:
    suffix = '.'

version = '0.21'
date = '2013-03-03'
    
    
class UEFfile:
    """instance = UEFfile(filename, creator)

    Create an instance of a UEF container using an existing file.
    If filename is not defined then create a new UEF container.
    The creator parameter can be used to override the default
    creator string.

    """

    def __init__(self, filename = None, creator = 'UEFfile '+version):
        """Create a new instance of the UEFfile class."""

        if filename == None:

            # There are no chunks initially
            self.chunks = []
            # There are no file positions defined
            self.files = []

            # Emulator associated with this UEF file
            self.emulator = 'Unspecified'
            # Originator/creator of the UEF file
            self.creator = creator
            # Target machine
            self.target_machine = ''
            # Keyboard layout
            self.keyboard_layout = ''
            # Features
            self.features = ''

            # UEF file format version
            self.minor = 9
            self.major = 0

            # List of files
            self.contents = []
        else:
            # Read in the chunks from the file

            # Open the input file
            try:
                in_f = open(filename, 'rb')
            except IOError:
                raise UEFfile_error, 'The input file, '+filename+' could not be found.'

            # Is it gzipped?
            if in_f.read(10) != 'UEF File!\000':
            
                in_f.close()
                in_f = gzip.open(filename, 'rb')
            
                try:
                    if in_f.read(10) != 'UEF File!\000':
                        in_f.close()
                        raise UEFfile_error, 'The input file, '+filename+' is not a UEF file.'
                except:
                    in_f.close()
                    raise UEFfile_error, 'The input file, '+filename+' could not be read.'
            
            # Read version self.number of the file format
            self.minor = self.str2num(1, in_f.read(1))
            self.major = self.str2num(1, in_f.read(1))

            # Decode the UEF file
            
            # List of chunks
            self.chunks = []
            
            # Read chunks
            
            while 1:
            
                # Read chunk ID
                chunk_id = in_f.read(2)
                if not chunk_id:
                    break
            
                chunk_id = self.str2num(2, chunk_id)
            
                length = self.str2num(4, in_f.read(4))
            
                if length != 0:
                    self.chunks.append((chunk_id, in_f.read(length)))
                else:
                    self.chunks.append((chunk_id, ''))

            # Close the input file
            in_f.close()

            # UEF file information (placed in "creator", "target_machine",
            # "keyboard_layout", "emulator" and "features" attributes).
            self.read_uef_details()

            # Read file contents (placed in the list attribute "contents").
            self.read_contents()


    def write(self, filename, write_creator_info = True,
              write_machine_info = True, write_emulator_info = True):
        """
        Write a UEF file containing all the information stored in an
        instance of UEFfile to the file with the specified filename.

        By default, information about the file's creator, target machine and
        emulator is written to the file. These can be omitted by calling this
        method with individual arguments set to False.
        """

        # Open the UEF file for writing
        try:
            uef = gzip.open(filename, 'wb')
        except IOError:
            raise UEFfile_error, "Couldn't open %s for writing." % filename
    
        # Write the UEF file header
        self.write_uef_header(uef)

        if write_creator_info:
            # Write the UEF creator chunk to the file
            self.write_uef_creator(uef)

        if write_machine_info:
            # Write the machine information
            self.write_machine_info(uef)

        if write_emulator_info:
            # Write the emulator information
            self.write_emulator_info(uef)
    
        # Write the chunks to the file
        self.write_chunks(uef)
    
        # Close the file
        uef.close()


    def number(self, size, n):
        """Convert a number to a little endian string of bytes for writing to a binary file."""

        # Little endian writing

        s = ""

        while size > 0:
            i = n % 256
            s = s + chr(i)
            n = n >> 8
            size = size - 1

        return s


    def str2num(self, size, s):
        """Convert a string of ASCII characters to an integer."""

        i = 0
        n = 0
        while i < size:

            n = n | (ord(s[i]) << (i*8))
            i = i + 1

        return n

                
    def hex2num(self, s):
        """Convert a string of hexadecimal digits to an integer."""

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
                return None

        return n


    # CRC calculation routines (begin)

    def rol(self, n, c):

        n = n << 1

        if (n & 256) != 0:
            carry = 1
            n = n & 255
        else:
            carry = 0

        n = n | c

        return n, carry


    def crc(self, s):

        high = 0
        low = 0

        for i in s:

            high = high ^ ord(i)

            for j in range(0,8):

                a, carry = self.rol(high, 0)

                if carry == 1:
                    high = high ^ 8
                    low = low ^ 16

                low, carry = self.rol(low, carry)
                high, carry = self.rol(high, carry)

        return high | (low << 8)

    # CRC calculation routines (end)

    def read_contents(self):
        """Find the positions of files in the list of chunks"""
        
        # List of files
        self.contents = []
        
        current_file = {}
        
        position = 0
        
        while 1:
        
            position = self.find_next_block(position)
        
            if position == None:
        
                # No more blocks, so store the details of the last file in
                # the contents list
                if current_file != {}:
                    self.contents.append(current_file)
                break
        
            else:
        
                # Read the block information
                name, load, exec_addr, data, block_number, last = self.read_block(self.chunks[position])
        
                if current_file == {}:
        
                    # No current file, so store details
                    current_file = {'name': name, 'load': load, 'exec': exec_addr, 'blocks': block_number, 'data': data}
        
                    # Locate the first non-block chunk before the block
                    # and store the position of the file
                    current_file['position'] = self.find_file_start(position)
                    # This may also be the position of the last chunk related to
                    # this file in the archive
                    current_file['last position'] = position
                else:
        
                    # Current file exists
                    if block_number == 0:
        
                        # New file, so write the previous one to the
                        # contents list, but before doing so, find the next
                        # non-block chunk and mark that as the last chunk in
                        # the file
        
                        if current_file != {}:
                            self.contents.append(current_file)
        
                        # Store details of this new file
                        current_file = {'name': name, 'load': load, 'exec': exec_addr, 'blocks': block_number, 'data': data}
        
                        # Locate the first non-block chunk before the block
                        # and store the position of the file
                        current_file['position'] = self.find_file_start(position)
                        # This may also be the position of the last chunk related to
                        # this file in the archive
                        current_file['last position'] = position
                    else:
                        # Not a new file, so update the number of
                        # blocks and append the block data to the
                        # data entry
                        current_file['blocks'] = block_number
                        current_file['data'] = current_file['data'] + data
        
                        # Update the last position information to mark the end of the file
                        current_file['last position'] = position
        
            # Increase the position
            position = position + 1

            # We now have a contents list which tells us
            # 1) the names of files in the archive
            # 2) the load and execution addresses of them
            # 3) the number of blocks they contain
            # 4) their data, and from this their length
            # 5) their start position (chunk number) in the archive


    def chunk(self, f, n, data):
        """Write a chunk to the file specified by the open file object, chunk number and data supplied."""

        # Chunk ID
        f.write(self.number(2, n))
        # Chunk length
        f.write(self.number(4, len(data)))
        # Data
        f.write(data)


    def read_block(self, chunk):
        """Read a data block from a tape chunk and return the program name, load and execution addresses,
        block data, block number and whether the block is supposedly the last in the file."""

        # Chunk number and data
        chunk_id = chunk[0]
        data = chunk[1]

        # For the implicit tape data chunk, just read the block as a series
        # of bytes, as before
        if chunk_id == 0x100:

            block = data

        else:   # 0x102

            if self.major == 0 and self.minor < 9:

                # For UEF file versions earlier than 0.9, the number of
                # excess bits to be ignored at the end of the stream is
                # set to zero implicitly
                ignore = 0
                bit_ptr = 0
            else:
                # For later versions, the number of excess bits is
                # specified in the first byte of the stream
                ignore = data[0]
                bit_ptr = 8

            # Convert the data to the implicit format
            block = []
            write_ptr = 0

            after_end = (len(data)*8) - ignore
            if after_end % 10 != 0:

                # Ensure that the number of bits to be read is a
                # multiple of ten
                after_end = after_end - (after_end % 10)

            while bit_ptr < after_end:

                # Skip start bit
                bit_ptr = bit_ptr + 1

                # Read eight bits of data
                bit_offset = bit_ptr % 8
                if bit_offset == 0:
                    # Write the byte to the block
                    block[write_ptr] = data[bit_ptr >> 3]
                else:
                    # Read the byte containing the first bits
                    b1 = data[bit_ptr >> 3]
                    # Read the byte containing the rest
                    b2 = data[(bit_ptr >> 3) + 1]

                    # Construct a byte of data
                    # Shift the first byte right by the bit offset
                    # in that byte
                    b1 = b1 >> bit_offset

                    # Shift the rest of the bits from the second
                    # byte to the left and ensure that the result
                    # fits in a byte
                    b2 = (b2 << (8 - bit_offset)) & 0xff

                    # OR the two bytes together and write it to
                    # the block
                    block[write_ptr] = b1 | b2

                # Increment the block pointer
                write_ptr = write_ptr + 1

                # Move the data pointer on eight bits and skip the
                # stop bit
                bit_ptr = bit_ptr + 9

        # Read the block
        name = ''
        a = 1
        while 1:
            c = block[a]
            if ord(c) != 0:     # was > 32:
                name = name + c
            a = a + 1
            if ord(c) == 0:
                break

        load = self.str2num(4, block[a:a+4])
        exec_addr = self.str2num(4, block[a+4:a+8])
        block_number = self.str2num(2, block[a+8:a+10])
        last = self.str2num(1, block[a+12])

        if last & 0x80 != 0:
            last = 1
        else:
            last = 0

        # Try to cope with UEFs that contain junk data at the end of blocks.
        rest = block[a+19:][:258]
        in_crc = crc(rest[:-2])
        if in_crc != str2num(2, rest[-2:]):
            print "Warning: block %x of file %s has mismatching CRC." % (
                block_number, repr(name))

        data = rest[:-2]

        return (name, load, exec_addr, data, block_number, last)


    def write_block(self, block, name, load, exe, n, last = 0, flags = 0):
    
        """Write data to a string as a file data block in preparation to be written
        as chunk data to a UEF file."""

        # Write the alignment character
        out = "*"+name[:10]+"\000"

        # Load address
        out = out + self.number(4, load)

        # Execution address
        out = out + self.number(4, exe)

        # Block number
        out = out + self.number(2, n)

        # Block length
        out = out + self.number(2, len(block))

        # Block flag (last block)
        if flags:
            out = out + self.number(1, flags)
        elif last:
            out = out + self.number(1, 128)
        else:
            out = out + self.number(1, 0)

        # Next address
        out = out + self.number(4, 0)

        # Header CRC
        out = out + self.number(2, self.crc(out[1:]))

        out = out + block

        # Block CRC
        out = out + self.number(2, self.crc(block))

        return out


    def get_leafname(self, path):
        """Get the leafname of the specified file."""

        pos = string.rfind(path, os.sep)
        if pos != -1:
            return path[pos+1:]
        else:
            return path


    def find_next_chunk(self, pos, IDs):
        """position, chunk = find_next_chunk(start, IDs)
        Search through the list of chunks from the start position given
        for the next chunk with an ID in the list of IDs supplied.
        Return its position in the list of chunks and its details."""

        while pos < len(self.chunks):

            if self.chunks[pos][0] in IDs:

                # Found a chunk with ID in the list
                return pos, self.chunks[pos]

            # Otherwise continue looking
            pos = pos + 1

        return None, None


    def find_next_block(self, pos):
        """Find the next file block in the list of chunks."""

        while pos < len(self.chunks):

            pos, chunk = self.find_next_chunk(pos, [0x100, 0x102])

            if pos == None:

                return None
            else:
                if len(chunk[1]) > 1:

                    # Found a block, return this position
                    return pos

            # Otherwise continue looking
            pos = pos + 1

        return None


    def find_file_start(self, pos):
        """Find a chunk before the one specified which is not a file block."""

        pos = pos - 1
        while pos > 0:

            if self.chunks[pos][0] != 0x100 and self.chunks[pos][0] != 0x102:

                # This is not a block
                return pos

            else:
                pos = pos - 1

        return pos


    def find_file_end(self, pos):
        """Find a chunk after the one specified which is not a file block."""

        pos = pos + 1
        while pos < len(self.chunks)-1:

            if self.chunks[pos][0] != 0x100 and self.chunks[pos][0] != 0x102:

                # This is not a block
                return pos

            else:
                pos = pos + 1

        return pos


    def read_uef_details(self):
        """Return details about the UEF file and its contents."""

        # Find the creator chunk
        pos, chunk = self.find_next_chunk(0, [0x0])

        if pos == None:

            self.creator = 'Unknown'

        elif chunk[1] == '':

            self.creator = 'Unknown'
        else:
            self.creator = chunk[1]

        # Delete the creator chunk
        if pos != None:
            del self.chunks[pos]

        # Find the target machine chunk
        pos, chunk = self.find_next_chunk(0, [0x5])

        if pos == None:

            self.target_machine = 'Unknown'
            self.keyboard_layout = 'Unknown'
        else:

            machines = ('BBC Model A', 'Electron', 'BBC Model B', 'BBC Master')
            keyboards = ('Any layout', 'Physical layout', 'Remapped')

            machine = ord(chunk[1][0]) & 0x0f
            keyboard = (ord(chunk[1][0]) & 0xf0) >> 4

            if machine < len(machines):
                self.target_machine = machines[machine]
            else:
                self.target_machine = 'Unknown'

            if keyboard < len(keyboards):
                self.keyboard_layout = keyboards[keyboard]
            else:
                self.keyboard_layout = 'Unknown'

            # Delete the target machine chunk
            del self.chunks[pos]

        # Find the emulator chunk
        pos, chunk = self.find_next_chunk(0, [0xff00])

        if pos == None:

            self.emulator = 'Unspecified'

        elif chunk[1] == '':

            self.emulator = 'Unknown'
        else:
            self.emulator = chunk[1]

        # Delete the emulator chunk
        if pos != None:
            del self.chunks[pos]

        # Remove trailing null bytes
        while len(self.creator) > 0 and self.creator[-1] == '\000':

            self.creator = self.creator[:-1]

        while len(self.emulator) > 0 and self.emulator[-1] == '\000':

            self.emulator = self.emulator[:-1]

        self.features = ''
        if self.find_next_chunk(0, [0x1])[0] != None:
            self.features = self.features + '\n' + 'Instructions'
        if self.find_next_chunk(0, [0x2])[0] != None:
            self.features = self.features + '\n' + 'Credits'
        if self.find_next_chunk(0, [0x3])[0] != None:
            self.features = self.features + '\n' + 'Inlay'


    def write_uef_header(self, file):
        """Write the UEF file header and version number to a file."""

        # Write the UEF file header
        file.write('UEF File!\000')

        # Minor and major version numbers
        file.write(self.number(1, self.minor) + self.number(1, self.major))


    def write_uef_creator(self, file):
        """Write a creator chunk to a file."""

        origin = self.creator + '\000'

        if (len(origin) % 4) != 0:
            origin = origin + ('\000'*(4-(len(origin) % 4)))

        # Write the creator chunk
        self.chunk(file, 0, origin)


    def write_machine_info(self, file):
        """Write the target machine and keyboard layout information to a file."""

        machines = {'BBC Model A': 0, 'Electron': 1, 'BBC Model B': 2, 'BBC Master':3}
        keyboards = {'any': 0, 'physical': 1, 'logical': 2}

        if machines.has_key(self.target_machine):

            machine = machines[self.target_machine]
        else:
            machine = 0

        if keyboards.has_key(self.keyboard_layout):

            keyboard = keyboards[keyboard_layout]
        else:
            keyboard = 0

        self.chunk(file, 5, self.number(1, machine | (keyboard << 4) ))


    def write_emulator_info(self, file):
        """Write an emulator chunk to a file."""

        emulator = self.emulator + '\000'

        if (len(emulator) % 4) != 0:
            emulator = emulator + ('\000'*(4-(len(emulator) % 4)))

        # Write the creator chunk
        self.chunk(file, 0xff00, emulator)


    def write_chunks(self, file):
        """Write all the chunks in the list to a file. Saves having loops in other functions to do this."""

        for c in self.chunks:

            self.chunk(file, c[0], c[1])


    def create_chunks(self, name, load, exe, data):
        """Create suitable chunks, and insert them into
        the list of chunks."""

        # Reset the block number to zero
        block_number = 0

        # Long gap
        gap = 1

        new_chunks = []
    
        # Write block details
        while True:
        
            last = (len(data) <= 256)
            block = self.write_block(data[:256], name, load, exe, block_number,
                                     last)

            # Remove the leading 256 bytes as they have been encoded
            data = data[256:]

            if gap == 1:
                new_chunks.append((0x110, self.number(2,0x05dc)))
                gap = 0
            else:
                new_chunks.append((0x110, self.number(2,0x0258)))

            # Write the block to the list of new chunks
            new_chunks.append((0x100, block))

            if last:
                break

            # Increment the block number
            block_number = block_number + 1

        # Return the list of new chunks
        return new_chunks


    def import_files(self, file_position, info, gap = False):
        """
        Import a file, or series of files, into the UEF file at the specified
        file position in the list of contents. Each file will be preceded by
        a gap, if enabled.
        
        file_position is a positive integer or zero

        To insert one file, info can be a sequence:

            info = (name, load, exe, data) where
            name is the file's name.
            load is the load address of the file.
            exe is the execution address.
            data is the contents of the file.

        For more than one file, info must be a sequence of info sequences.
        """

        if file_position < 0:

            raise UEFfile_error, 'Position must be zero or greater.'

        # Find the chunk position which corresponds to the file_position
        if self.contents != []:

            # There are files already present
            if file_position >= len(self.contents):

                # Position the new files after the end of the last file
                position = self.contents[-1]['last position'] + 1

            else:

                # Position the new files before the end of the file
                # specified
                position = self.contents[file_position]['position']
        else:
            # There are no files present in the archive, so put them after
            # all the other chunks
            position = len(self.chunks)

        # Examine the info sequence passed
        if len(info) == 0:
            return

        if type(info[0]) == types.StringType:

            # Assume that the info sequence contains name, load, exe, data
            info = [info]

        # Read the file details for each file and create chunks to add
        # to the list of chunks
        inserted_chunks = []

        for name, load, exe, data in info:

            if gap:
                inserted_chunks += [(0x112, "\xdc\x05"),
                                    (0x110, "\xdc\x05"),
                                    (0x100, "\xdc")]
            
            inserted_chunks += self.create_chunks(name, load, exe, data)

        # Insert the chunks in the list at the specified position
        self.chunks = self.chunks[:position] + inserted_chunks + self.chunks[position:]

        # Update the contents list
        self.read_contents()


    def chunk_number(self, name):
        """
        Returns the relevant chunk number for the name given.
        """

        # Use a convention for determining the chunk number to be used:
        # Certain names are converted to chunk numbers. These are listed
        # in the encode_as dictionary.

        encode_as = {'creator': 0x0, 'originator': 0x0, 'instructions': 0x1, 'manual': 0x1,
                 'credits': 0x2, 'inlay': 0x3, 'target': 0x5, 'machine': 0x5,
                 'multi': 0x6, 'multiplexing': 0x6, 'palette': 0x7,
                 'tone': 0x110, 'dummy': 0x111, 'gap': 0x112, 'baud': 0x113,
                 'position': 0x120,
                 'discinfo': 0x200, 'discside': 0x201, 'rom': 0x300,
                 '6502': 0x400, 'ula': 0x401, 'wd1770': 0x402, 'memory': 0x410,
                 'emulator': 0xff00}

        # Attempt to convert name into a chunk number
        try:
            return encode_as[string.lower(name)]

        except KeyError:
            raise UEFfile_error, "Couldn't find suitable chunk number for %s" % name


    def export_files(self, file_positions):
        """
        Given a file's location of the list of contents, returns its name,
        load and execution addresses, and the data contained in the file.
        If positions is an integer then return a tuple

            info = (name, load, exe, data)

        If positions is a list then return a list of info tuples.
        """

        if type(file_positions) == types.IntType:

            file_positions = [file_positions]

        info = []

        for file_position in file_positions:

            # Find the chunk position which corresponds to the file position
            if file_position < 0 or file_position >= len(self.contents):

                raise UEFfile_error, 'File position %i does not correspond to an actual file.' % file_position
            else:
                # Find the start and end positions
                name = self.contents[file_position]['name']
                load = self.contents[file_position]['load']
                exe  = self.contents[file_position]['exec']

            info.append( (name, load, exe, self.contents[file_position]['data']) )

        if len(info) == 1:
            info = info[0]

        return info


    def chunk_name(self, number):
        """
        Returns the relevant chunk name for the number given.
        """

        decode_as = {0x0: 'creator', 0x1: 'manual', 0x2: 'credits', 0x3: 'inlay',
                 0x5: 'machine', 0x6: 'multiplexing', 0x7: 'palette',
                 0x110: 'tone', 0x111: 'dummy', 0x112: 'gap', 0x113: 'baud',
                 0x120: 'position',
                 0x200: 'discinfo', 0x201: 'discside', 0x300: 'rom',
                 0x400: '6502', 0x401: 'ula', 0x402: 'wd1770', 0x410: 'memory',
                 0xff00: 'emulator'}

        try:
            return decode_as[number]
        except KeyError:
            raise UEFfile_error, "Couldn't find name for chunk number %i." % number


    def remove_files(self, file_positions):
        """
        Removes files at the positions in the list of contents.
        positions is either an integer or a list of integers.
        """
        
        if type(file_positions) == types.IntType:

            file_positions = [file_positions]

        positions = []
        for file_position in file_positions:
    
            # Find the chunk position which corresponds to the file position
            if file_position < 0 or file_position >= len(self.contents):
        
                print 'File position %i does not correspond to an actual file.' % file_position
    
            else:
                # Add the chunk positions within each file to the list of positions
                positions = positions + range(self.contents[file_position]['position'],
                                  self.contents[file_position]['last position'] + 1)
    
        # Create a new list of chunks without those in the positions list
        new_chunks = []
        for c in range(0, len(self.chunks)): 
    
            if c not in positions:
                new_chunks.append(self.chunks[c])

        # Overwrite the chunks list with this new list
        self.chunks = new_chunks

        # Create a new contents list
        self.read_contents()        


    def printable(self, s):

        new = ''
        for i in s:

            if ord(i) < 32:
                new = new + '?'
            else:
                new = new + i

        return new


    # Higher level functions ------------------------------

    def info(self):
        """
        Provides general information on the target machine,
        keyboard layout, file creator and target emulator.
        """

        # Info command
    
        # Split paragraphs
        creator = string.split(self.creator, '\012')
    
        print 'File creator:'
        for line in creator:
            print line
        print
        print 'File format version: %i.%i' % (self.major, self.minor)
        print
        print 'Target machine : '+self.target_machine
        print 'Keyboard layout: '+self.keyboard_layout
        print 'Emulator       : '+self.emulator
        print
        if self.features != '':

            print 'Contains:'
            print self.features
            print
        print '(%i chunks)' % len(self.chunks)
        print

    def cat(self):
        """
        Prints a catalogue of the files stored in the UEF file.
        """

        # Catalogue command
    
        if self.contents == []:
    
            print 'No files'
    
        else:
    
            print 'Contents:'
    
            file_number = 0
    
            for file in self.contents:
    
                # Converts non printable characters in the filename
                # to ? symbols
                new_name = self.printable(file['name'])
    
                print string.expandtabs(string.ljust(str(file_number), 3)+': '+
                            string.ljust(new_name, 16)+
                            string.upper(
                                string.ljust(hex(file['load'])[2:], 10) +'\t'+
                                string.ljust(hex(file['exec'])[2:], 10) +'\t'+
                                string.ljust(hex(len(file['data']))[2:], 6)
                            ) +'\t'+
                            'chunks %i to %i' % (file['position'], file['last position']) )
    
                file_number = file_number + 1

    def show_chunks(self):
        """
        Display the chunks in the UEF file in a table format
        with the following symbols denoting each type of
        chunk:
                O        Originator information            (0x0)
                I        Instructions/manual               (0x1)
                C        Author credits                    (0x2)
                S        Inlay scan                        (0x3)
                M        Target machine information        (0x5)
                X        Multiplexing information          (0x6)
                P        Extra palette                     (0x7)

                #, *     File data block             (0x100,0x102)
                #x, *x   Multiplexed block           (0x101,0x103)
                -        High tone (inter-block gap)       (0x110)
                +        High tone with dummy byte         (0x111)
                _        Gap (silence)                     (0x112)
                B        Change of baud rate               (0x113)
                !        Position marker                   (0x120)
                D        Disc information                  (0x200)
                d        Standard disc side                (0x201)
                dx       Multiplexed disc side             (0x202)
                R        Standard machine ROM              (0x300)
                Rx       Multiplexed machine ROM           (0x301)
                6        6502 standard state               (0x400)
                U        Electron ULA state                (0x401)
                W        WD1770 state                      (0x402)
                m        Standard memory data              (0x410)
                mx       Multiplexed memory data           (0x410)

                E        Emulator identification string    (0xff00)
                ?        Unknown (unsupported chunk)
        """

        chunks_symbols = {
                            0x0:    'O ',   # Originator
                            0x1:    'I ',   # Instructions/manual
                            0x2:    'C ',   # Author credits
                            0x3:    'S ',   # Inlay scan
                            0x5:    'M ',   # Target machine info
                            0x6:    'X ',   # Multiplexing information
                            0x7:    'P ',   # Extra palette
                            0x100:  '# ',   # Block information (implicit start/stop bit)
                            0x101:  '#x',   # Multiplexed (as 0x100)
                            0x102:  '* ',   # Generic block information
                            0x103:  '*x',   # Multiplexed generic block (as 0x102)
                            0x110:  '- ',   # High pitched tone
                            0x111:  '+ ',   # High pitched tone with dummy byte
                            0x112:  '_ ',   # Gap (silence)
                            0x113:  'B ',   # Change of baud rate
                            0x120:  '! ',   # Position marker
                            0x200:  'D ',   # Disc information
                            0x201:  'd ',   # Standard disc side
                            0x202:  'dx',   # Multiplexed disc side
                            0x300:  'R ',   # Standard machine ROM
                            0x301:  'Rx',   # Multiplexed machine ROM
                            0x400:  '6 ',   # 6502 standard state
                            0x401:  'U ',   # Electron ULA state
                            0x402:  'W ',   # WD1770 state
                            0x410:  'm ',   # Standard memory data
                            0x411:  'mx',   # Multiplexed memory data
                            0xff00: 'E '   # Emulator identification string
                        }

        if len(self.chunks) == 0:
            print 'No chunks'
            return

        # Display chunks
        print 'Chunks:'

        n = 0

        for c in self.chunks:

            if n % 16 == 0:
                sys.stdout.write(string.rjust('%i: '% n, 8))
            
            if chunks_symbols.has_key(c[0]):
                sys.stdout.write(chunks_symbols[c[0]])
            else:
                # Unknown
                sys.stdout.write('? ')

            if n % 16 == 15:
                sys.stdout.write('\n')

            n = n + 1

        print
