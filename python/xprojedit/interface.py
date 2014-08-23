"""collection of interfaces."""
import os
import re

from xprojedit.classes import XcodeObject
import mod_pbxproj


def _cleanup(xcodeobject, guid):
    node = xcodeobject.mod_pbxproj.get('objects').get(guid)

    # remove build files
    references = set()
    for objectid, objectvalue in xcodeobject.mod_pbxproj.get('objects').items():
        if (guid in objectvalue.values() and
                objectvalue.get('isa') == 'PBXBuildFile'):
            references.add(objectid)

    for referenceid in references:
        _cleanup(xcodeobject, referenceid)

    # recurse
    if 'children' in node:
        for childid in node['children']:
            _cleanup(xcodeobject, childid)

    xcodeobject.mod_pbxproj.get('objects').pop(guid)


def tree_lines(xcodepath, noindent, dir_only, location='//'):
    """print tree representation of xcodeproject."""
    xcodepath, xcb = get_xcodeobject(xcodepath)
    style = parent_style if noindent else bullet_style
    locationobj = find_location(xcb, location)
    lines = get_tree_lines(locationobj.tree(dir_only), style)

    # responsible root name swapping
    # so root is represented by a double slash
    rtname = xcb.root().mainGroup.name
    lines = [re.sub(r'^%s/' % rtname, '//', line) for line in lines]

    return lines


def add_folder(xcodepath, diskpath, pathtogroup, nosave=False):
    """add diskpath reference pathtogroup."""
    xcodepath, xcb = get_xcodeobject(xcodepath)

    # look for starting position
    location = find_location(xcb, pathtogroup)

    # just in case it is needed, I think it is.
    project_dir = os.path.dirname(xcodepath)
    absdiskpath = os.path.abspath(diskpath)
    os.chdir(project_dir)
    xcb.mod_pbxproj.add_folder(absdiskpath, parent=location.guid)

    if not nosave:
        xcb.mod_pbxproj.save()


def add_files(xcodepath, filestoadd, pathtogroup, nosave=False):
    """add files to pathtogroup."""
    xcodepath, xcb = get_xcodeobject(xcodepath)

    # look for starting position
    foundlocation = mod_pbxproj.PBXGroup(find_location(xcb, pathtogroup))

    # just in case it is needed, I think it is.
    project_dir = os.path.dirname(xcodepath)
    absdiskpaths = [os.path.abspath(diskpath) for diskpath in filestoadd]
    os.chdir(project_dir)
    for filetoadd in absdiskpaths:
        xcb.mod_pbxproj.add_file(filetoadd,
                                 foundlocation)

    if not nosave:
        xcb.mod_pbxproj.save()


def remove_location(xcodepath, pathtogroup, nosave=False):
    """removes a location in an xcodeproject."""
    xcodepath, xcb = get_xcodeobject(xcodepath)

    # look for starting position
    foundlocation = find_location(xcb, pathtogroup)

    # find parent node
    parentnode = mod_pbxproj.PBXGroup(foundlocation.parent)

    # remove and save and done
    parentnode.remove_child(foundlocation.guid)

    _cleanup(xcb, foundlocation.guid)

    if not nosave:
        xcb.mod_pbxproj.save()


def sync_location(xcodepath, pathtogroup, nosave=False):
    """removes a location in an xcodeproject."""
    xcodepath, xcb = get_xcodeobject(xcodepath)

    basedir = os.path.dirname(xcodepath)
    os.chdir(basedir)

    # look for starting position
    foundlocation = find_location(xcb, pathtogroup)
    linkedfolder = os.path.join(basedir, '..', foundlocation.path)
    if not os.path.exists(linkedfolder):
        print 'linked folder was not found'
        return 1

    pathtogroupparts = pathtogroup.split('/')
    parentpath = '/'.join(pathtogroupparts[:-1])

    # remove and add
    remove_location(xcb, pathtogroup, nosave=True)
    add_folder(xcb, linkedfolder, parentpath, nosave=True)
    if not nosave:
        xcb.mod_pbxproj.save()


def find_matching_regex(xcodepath, searchstring, location='//'):
    """regex search of fullpaths given a path to xcode."""
    # wrap simplestrings with .* so they act as globglob.
    searchstring = ('.*%s.*' % searchstring
                    if re.match('^[0-9a-zA-Z]+$', searchstring)
                    else searchstring)
    lines = tree_lines(xcodepath, True, False, location)
    return [line for line in lines if re.match(searchstring, line)]


################################################################################
# utility function #############################################################
################################################################################


def get_xcodeobject(xcodepath):
    """returns xcodeobject when it needs to."""
    if isinstance(xcodepath, str):
        return xcodepath, XcodeObject(xcodepath)
    else:
        return xcodepath.filepath, xcodepath


def get_tree_lines(tree_obj, style):
    """recursive function to get tree lines to print."""
    lines = []
    if isinstance(tree_obj, dict):
        for key, value in tree_obj.items():
            parent = key.name
            lines.append(style('singlegroup', key))
            lastidx = len(value) - 1

            for idx, item in enumerate(value):
                item_lines = get_tree_lines(item, style)

                if not item_lines:
                    continue

                last = bool(idx == lastidx)
                opts = (last, parent)
                lines.extend(style('indent', item_lines, opts))
    else:
        lines.append(style('single', tree_obj))
    return lines


def find_location(xcobject, location):
    """utility to find node in given location."""
    root = xcobject.root().mainGroup

    parts = [loc for loc in location.split('/') if loc]

    pointer = root
    while parts:
        part = parts.pop(0)

        children = pointer.children
        for child in children:

            # this should never return str unless the object the id
            # describes was not found, hence we skip
            if isinstance(child, str):
                continue

            if child.name == part or child.path == part:
                pointer = child
                break
        else:
            raise LocationNotFound('could not find %s' % location)

    return pointer


################################################################################
# exceptions ###################################################################
################################################################################

class LocationNotFound(Exception):
    pass


################################################################################
# print styles #################################################################
################################################################################

def bullet_style(style, inputs, opts=None):
    if opts:
        last, parent = opts

    if style == 'indent':
        lines = []
        bullet = '`' if last else '|'
        lines.append('  %s-- %s' % (bullet, inputs[0]))
        for item_line in inputs[1:]:
            picket = ' ' if last else '|'
            lines.append('  %s  %s' % (picket, item_line))
        return lines
    elif style == 'singlegroup':
        return '"%s" (%s)' % (inputs.name, inputs.isa)
    elif style == 'single':
        if inputs.name:
            return '"%s" -> "%s"' % (inputs.name, inputs.path)
        else:
            return '"%s"' % inputs.path


def parent_style(style, inputs, opts=None):
    if opts:
        last, parent = opts

    if style == 'indent':
        lines = []
        for item_line in inputs[:]:
            lines.append('%s/%s' % (parent, item_line))
        return lines
    elif style == 'singlegroup':
        return inputs.name
    elif style == 'single':
        if inputs.name:
            return '%s -> %s' % (inputs.name, inputs.path)
        else:
            return '%s' % inputs.path
