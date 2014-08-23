from distutils.core import setup

long_description = """
=========
XprojEdit
=========

*xprojedit* allows users working with xcode projects to make changes without
having to open the Xcode.  Why would anyone ever want to do that?  Some
programmers would rather use their favorite text editors instead of Xcode.
Having to constantly move back to Xcode just to add a resource .png file can be
a pain.  So if you are one of those, you can use *xprojedit* to make changes to
your xcode project from either the *xprojedit* cli executable or via the
*xprojedit* python library.

The cli xprojedit executable allows you to:

:tree: show tree structure of the project.
:find: find files or folders matching pattern.
:addfolder: add a folder to a group.
:addfiles: add a file or set of files to a specific group.
:rmgrp: remove a group.
:syncgrp: makes sure the contents of a group match the folder it links to.

The python library *xprojedit.interface* has corresponding functions for each
sub-command from the executable.  So if you'd like to write plug-ins for your
favorite text editor, you could use the *xprojedit.interface* module.

This makes good use of mod_pbxproj.
"""

setup(name='xprojedit',
      version='0.1',
      description='Convenient methods for Xcode Project manipulation.',
      long_description=long_description.strip(),
      author='David Marte',
      author_email='redesigndavid@gmail.com',
      url='http://www.redesigndavid.com/?tags=xprojedit',
      py_modules=['xprojedit.classes', 'xprojedit.interface', 'xprojedit.__init__'],
      package_dir={'': 'python'},
      scripts=['bin/xprojedit'],
      )
