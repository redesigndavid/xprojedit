XprojEdit
=========

*xprojedit* allows users working with xcode projects to make changes without
having to open Xcode.  Why would anyone ever want to do that?  Some programmers
would rather use their favorite text editors instead of Xcode.  Having to
constantly move back to Xcode just to add a resource .png file can be a pain.
So if you are one of those, you can use this package to make changes to your
xcode project from either the cli executable or via the python library
included.

The cli executable allows you to:

subcommand | description
----------:|:------------------------------------------------------------------
tree       | show tree structure of the project.
find       | find files or folders matching pattern.
addfolder  | add a folder to a group.
addfiles   | add a file or set of files to a specific group.
rmgrp      | remove a group.
syncgrp    | makes sure the contents of a group match the folder it links to.

xprodedit python library
------------------------
The python library *xprojedit.interface* has corresponding functions for each
subcommand from the executable.  So if you'd like to write plug-ins for your
favorite text editor, you could use the *xprojedit.interface* module.

This makes good use of *mod_pbxproj*.  In fact, for all intents and purposes,
xprodedit would appear to be *just* a wrapper to mod-pbxproj.  And so if all
you wanted was a starting point to write a plugin, you might as well use
mod-pbxproj directly.  But I originally intended *xprojedit* to stand on its
own until I saw the excellent work the community has done on mod-pbxproj and I
didn't want to duplicate efforts.


Install
-------

`$ git clone --recurse-submodules http://github.com/redesigndavid/xprojedit`  
`$ cd xprojedit && python setup.py build install`

**NOTE**  This repo links to another github repo (hence the addition of
--recurse-submodules in the clone command).  When you run `python setup.py
build install`, it would build and install both xprojedit and mod-pbxproj.  If
you'd rather install the 2 yourself, just make sure you put both somewhere in
your PYTHONPATH before running xprojedit.

Sample Usage
------------

To see a tree listing of your project:  
`$ xprojedit tree /path/to/project.pbxproj`

To see only groups withouts files:  
`$ xprojedit tree /path/to/project.pbxproj -d`

To see tree listing without indents:  
`$ xprojedit tree /path/to/project.pbxproj -i`

To grep/search files and folders:  
`$ xprojedit find /path/to/project.pbxproj foo`

To only search a folder:  
`$ xprojedit find /path/to/project.pbxproj //Resources foo`

You can also use regex patterns:  
`$ xprojedit find /path/to/project.pbxproj //Resources foo.*bar`

You can add a folder to a group.  This command adds a folder named foobar to
Resources.  
`$ xprojedit addfolder /path/to/project.pbxproj //Resources /path/to/foobar`

You can add files too:  
`$ xprojedit addfiles /path/to/project.pbxproj //Resources /path/to/blah*.png`

You can remove groups:  
`$ xprojedit rmgrp /path/to/project.pbxproj //Resources/foobar`

Or just sync the group so it would again contain the files and folders of the
folders of the original folder it was supposed to represent.  
`$ xprojedit syncgrp /path/to/project.pbxproj //Resources/foobar`
