Acorn Format Tools
==================

This repository contains Python modules and tools for manipulating different
files and formats used by Acorn 8-bit range of computers, such as SSD and DSD
files containing DFS and ADFS format disk images, and UEF files containing
cassette data.

Tools for converting data between formats and examples showing how to use the
modules are also provided.

The aim is to provide Python 2 and Python 3 versions of all modules, tools
and examples.


Modules
-------

* diskutils.py
  Defines abstractions such as files and directories with features that are
  common to many of the Acorn filing systems.
* makedfs.py
  Defines structures such as disks and catalogues that are specific to DFS.


Tools
-----

* make_dfs_disk.py
  Creates a DFS disk image with a given name, containing the files specified
  as arguments on the command line.


Authors
-------

* David Boddie <david@boddie.org.uk>

License
-------


Both the assembly language routines and the Python modules and tools are
licensed under the GNU General Public License version 3 or later:

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

