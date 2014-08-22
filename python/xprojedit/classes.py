"""wrapper nodes for pbx objects."""
import os

import collections

import plistlib
import subprocess
import re
import uuid

# special comments
BLD_PBXNATIVETARGETNOTE = 'Build configuration list for PBXNativeTarget "TARGET_NAME"'
BLD_UNITY_IPHONENOTE = 'Build configuration list for PBXProject "Unity-iPhone"'

# list of sections and whether they should be written with linefeeds or without.
SECTIONS = [('PBXBuildFile', False),
            ('PBXCopyFilesBuildPhase', True),
            ('PBXFileReference', False),
            ('PBXFrameworksBuildPhase', True),
            ('PBXGroup', True),
            ('PBXAggregateTarget', True),
            ('PBXNativeTarget', True),
            ('PBXProject', True),
            ('PBXResourcesBuildPhase', True),
            ('PBXShellScriptBuildPhase', True),
            ('PBXSourcesBuildPhase', True),
            ('XCBuildConfiguration', True),
            ('XCConfigurationList', True),
            ('PBXTargetDependency', True),
            ('PBXVariantGroup', True),
            ('PBXReferenceProxy', True),
            ('PBXContainerItemProxy', True)]

# list of filetypes and which buildphases they should be added to.
FILETYPE_BUILDPHASES = {
    '.a': ('archive.ar', 'PBXFrameworksBuildPhase'),
    '.app': ('wrapper.application', None),
    '.s': ('sourcecode.asm', 'PBXSourcesBuildPhase'),
    '.c': ('sourcecode.c.c', 'PBXSourcesBuildPhase'),
    '.cpp': ('sourcecode.cpp.cpp', 'PBXSourcesBuildPhase'),
    '.framework': ('wrapper.framework', 'PBXFrameworksBuildPhase'),
    '.h': ('sourcecode.c.h', None),
    '.hpp': ('sourcecode.c.h', None),
    '.icns': ('image.icns', 'PBXResourcesBuildPhase'),
    '.m': ('sourcecode.c.objc', 'PBXSourcesBuildPhase'),
    '.j': ('sourcecode.c.objc', 'PBXSourcesBuildPhase'),
    '.mm': ('sourcecode.cpp.objcpp', 'PBXSourcesBuildPhase'),
    '.nib': ('wrapper.nib', 'PBXResourcesBuildPhase'),
    '.plist': ('text.plist.xml', 'PBXResourcesBuildPhase'),
    '.json': ('text.json', 'PBXResourcesBuildPhase'),
    '.png': ('image.png', 'PBXResourcesBuildPhase'),
    '.rtf': ('text.rtf', 'PBXResourcesBuildPhase'),
    '.tiff': ('image.tiff', 'PBXResourcesBuildPhase'),
    '.txt': ('text', 'PBXResourcesBuildPhase'),
    '.xcodeproj': ('wrapper.pb-project', None),
    '.xib': ('file.xib', 'PBXResourcesBuildPhase'),
    '.strings': ('text.plist.strings', 'PBXResourcesBuildPhase'),
    '.bundle': ('wrapper.plug-in', 'PBXResourcesBuildPhase'),
    '.dylib': ('compiled.mach-o.dylib', 'PBXFrameworksBuildPhase')
    }

SPECIALFOLDEREXTENSIONS = ['.bundle', '.framework', '.xcodeproj']
REGEX = re.compile(r'[a-zA-Z0-9\\._/-]*')


def guess_filetypeandbuildphase(filepath, ignore_unknown_type=False):
    """return filetype and buildphase."""
    ext = os.path.splitext(filepath)[1]
    if os.path.isdir(filepath) and ext not in ('.framework', '.bundle'):
        filetype = 'folder'
        build_phase = None
    else:
        default_buildphase = ('?', 'PBXResourcesBuildPhase')
        filetype, build_phase = FILETYPE_BUILDPHASES.get(ext, default_buildphase)

    return filetype, build_phase


def slashed(stringobj):
    """add slashes before special characters in stringobj."""
    rep_key = {'"': '\\"',
               "'": "\\'",
               "\0": "\\\0",
               "\\": "\\\\",
               "\n": "\\n"}
    return ''.join(rep_key.get(ch, ch) for ch in stringobj)


class XcodeNode(collections.MutableMapping):
    """wrapper for pbx objects that makes it easy to do recursive functions."""
    def __init__(self, project, parent, guid, *args, **kwargs):
        self.project = project
        self.parent = parent
        self.rawdata = self.project.plistdata
        self.nodedata = self.project.plistdata.get('objects').get(guid)
        self.guid = guid

        self.isa_type = self.nodedata['isa']
        self.node_name = self.nodedata.get('name', 'XcodeNode')

        self.update(dict(*args, **kwargs))

    def __convert(self, value):
        """return nodedata if value is a reference, else return value."""

        if isinstance(value, str) and value in self.rawdata['objects']:
            return XcodeNode(self.project, self, value)

        return value

    def __repr__(self):
        return '%s("%s")' % (self.isa_type, self.node_name)

    def __getattr__(self, attr):
        """allow dot notation for keys."""
        if attr in self.keys():
            return self.__getitem__(attr)
        elif attr in self.nodedata.__dict__.keys():
            return self.nodedata.__dict__.get(attr)
        return None

    def __getitem__(self, key):
        """return converted version of the value paired with given key."""

        value = self.nodedata.get(key)

        if isinstance(value, str):
            return self.__convert(value)
        elif isinstance(value, list):
            return [self.__convert(val) for val in value]
        elif isinstance(value, dict):
            new_dict = {}
            for k, v in value.items():
                new_dict[self.__convert(k)] = self.__convert(v)
            return new_dict
        else:
            return value

    def __setitem__(self, key, value):
        self.nodedata[key] = value

    def __delitem__(self, key):
        del self.nodedata[key]

    def __hash__(self):
        return id(frozenset(self))

    def __iter__(self):
        return iter(self.nodedata)

    def __len__(self):
        return len(self.nodedata)

    def __contains__(self, attr):
        return attr in self.nodedata.keys()

    def tree(self, dironly=False):
        """convert object into a tree of {self:dict}."""
        if not self:
            return ''

        children = self.children
        if children:
            if dironly:
                return {self: [child.tree(dironly) for child in children
                               if child.children]}
            else:
                return {self: [child.tree() for child in children]}

        else:
            return self

    def remove_child(self, child):
        """remove child from chilren."""
        if hasattr(self, 'children'):
            if isinstance(child, str):
                child = XcodeNode(self.project, self, child)
            childid = child.guid

            if child.children:
                for grandchild in child.children:
                    child.remove_child(grandchild)

            buildfiles = [bfuid
                          for bfuid, bf in self.rawdata['objects'].items()
                          if bf['isa'] == 'PBXBuildFile' and
                          bf['fileRef'] == childid]
            for buildfile_uid in buildfiles:
                self.rawdata['objects'].pop(buildfile_uid)

            self.rawdata['objects'].pop(childid)
            self.rawdata['objects'][self.guid]['children'].remove(childid)

    def add_folder(self, folderpath, excludes=None, recursive=True):
        """add folder to this node."""
        create_build_files = True
        if not os.path.isdir(folderpath):
            # continue only of folderpath exists
            return

        if not excludes:
            excludes = []

        specials = []

        path2parentnodes = {os.path.split(folderpath)[0]: self}

        for (dirpath, dirnames, filenames) in os.walk(folderpath):
            parent_folder, folder_name = os.path.split(dirpath)
            parent = path2parentnodes.get(parent_folder, self)

            # checks first
            if [sp for sp in specials if parent_folder.startswith(sp)]:
                continue

            if folder_name.startswith('.'):
                specials.append(dirpath)
                continue

            if os.path.splitext(dirpath)[1] in SPECIALFOLDEREXTENSIONS:
                # if this file has a special extension
                # (bundle or framework mainly) treat it as a file
                specials.append(dirpath)
                parent.add_file(dirpath, create_build_files)

            # ignore this file if it is in excludes
            if [m for m in excludes if re.match(m, dirpath)]:
                continue

            rel_dirpath = self.get_relative(dirpath)
            group = parent.getcreate_group(folder_name, rel_dirpath)
            path2parentnodes[dirpath] = group

            # add files
            for fp in filenames:
                # ignore files matching excludes or if it starts with a .
                if fp[0] == '.' or [m for m in excludes if re.match(m, fp)]:
                    continue

                path2parentnodes[dirpath].add_file(os.path.join(dirpath, fp),
                                                   create_build_files)

    def add_file(self, filepath, create_build_files=True, tree='SOURCE_ROOT'):
        """add file to this node."""

        if not os.path.exists(filepath):
            print 'file not found: %s' % filepath
            return

        if tree == '<absolute>':
            filepath = os.path.abspath(filepath)
        elif tree == 'SOURCE_ROOT':
            filepath = self.get_relative(filepath)

        filerefobj = self.getcreate_file(filepath, tree)

        build_phase = filerefobj.extra['build_phase']

        # create_build_files adds files to certain buildphases
        if create_build_files and build_phase:
            phases = self.get_build_phases(build_phase)
            for phase in phases:
                build_file_data = {'fileRef': filerefobj.id,
                                   'isa': 'PBXBuildFile'}
                buildfile_obj = UniqueObject(build_file_data)
                phase['files'].append(buildfile_obj.id)
                self.rawdata['objects'][buildfile_obj.id] = buildfile_obj

    def get_relative(self, filepath):
        """return filepath relative to project."""
        filepath = os.path.relpath(filepath,
                                   os.path.dirname(self.project.filepath))
        filepath = '/'.join(filepath.split('/')[1:])
        return filepath

    def get_build_phases(self, phase_name):
        """return objects of given phase_name type."""
        return [p for p in self.rawdata['objects'].values()
                if p.get('isa') == phase_name]

    def getcreate_file(self, filepath, sourcetree):
        """create and return filereference.

        delete when initially found along with buildfiles.
        """
        children = self.children
        foundchild = None
        for chld in children:
            if chld.path == filepath:
                foundchild = chld
                self.rawdata['objects'].pop(chld.guid)
                self.rawdata['objects'][self.guid]['children'].remove(chld.guid)

                # delete associated build files otherwise we'll have duplicates
                buildfiles = [bfuid
                              for bfuid, bf in self.rawdata['objects'].items()
                              if bf['isa'] == 'PBXBuildFile' and
                              bf['fileRef'] == chld.guid]
                for buildfile_uid in buildfiles:
                    self.rawdata['objects'].pop(buildfile_uid)

        filetype, build_phase = guess_filetypeandbuildphase(filepath)
        if not foundchild:
            foundchild = {'path': filepath,
                          'isa': 'PBXFileReference',
                          'name': os.path.split(filepath)[1],
                          'sourceTree': sourcetree,
                          'lastKnownFileType': filetype}

        extra = {'build_phase': build_phase}
        filerefobj = UniqueObject(dict(foundchild), extra)

        self.rawdata['objects'][filerefobj.id] = filerefobj
        self.rawdata['objects'][self.guid]['children'].append(filerefobj.id)

        return XcodeNode(self.project, self, filerefobj.id)

    def getcreate_group(self, folder_name, dirpath):
        """create a group or find child with matching foldername."""

        children = self.children
        for child in children:
            if child.name == folder_name:
                return child

        # child doesn't exist so we create it.
        group = {'name': folder_name,
                 'isa': 'PBXGroup',
                 'children': [],
                 'path': dirpath,
                 'sourceTree': '<group>'}
        groupobj = UniqueObject(group)

        self.rawdata['objects'][groupobj.id] = group
        self.rawdata['objects'][self.guid]['children'].append(groupobj.id)

        return XcodeNode(self.project, self, groupobj.id)


class UniqueObject(dict):

    """Uniqify Object by associating uuid string to it."""

    def __init__(self, data, extra={}):
        dict.__init__(self, data)
        if hasattr(data, 'id') and data.id:
            self.id = data.id
        else:
            # create unique id, when needed
            self.id = ''.join(str(uuid.uuid4()).upper().split('-')[1:])

        # extra variables
        self.extra = extra


class XcodeObject():
    """xprojedit interface starting point."""
    def __init__(self, filepath):
        self.filepath = filepath

        plutilcmd = 'plutil -convert xml1 -o - %s' % filepath
        p = subprocess.Popen(plutilcmd.split(),
                             stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        self.plistdata = plistlib.readPlistFromString(stdout)

    def root(self):
        """returns the first node."""
        rootid = self.plistdata.get('rootObject')
        return XcodeNode(project=self,
                         parent=None,
                         guid=rootid)

    def save(self):
        """save xcode project with changes."""

        # collect objects
        objs = self.plistdata.get('objects')
        sections = dict()
        comments = dict()

        for key_id, val_objct in objs.iteritems():

            # get object type section list
            object_type_section = []
            object_type = val_objct.get('isa')
            if object_type in sections:
                object_type_section = sections.get(object_type)

            # add this key value pair
            object_type_section.append(tuple([key_id, val_objct]))

            # save section
            sections[object_type] = object_type_section

            # make comments
            if 'name' in val_objct:
                comments[key_id] = val_objct.get('name')
            elif 'path' in val_objct:
                comments[key_id] = val_objct.get('path')
            else:
                if val_objct.get('isa') == 'PBXProject':
                    build_conf = val_objct.get('buildConfigurationList')
                    comments[build_conf] = BLD_UNITY_IPHONENOTE
                elif val_objct.get('isa')[0:3] == 'PBX':
                    comments[key_id] = val_objct.get('isa')[3:-10]
                else:
                    comments[key_id] = BLD_PBXNATIVETARGETNOTE

        # go through items again and collect fileref comments
        for key_id, val_objct in objs.iteritems():
            # fix note for fileRefs, with data only available on second loop
            if 'fileRef' in val_objct and val_objct.get('fileRef') in comments:
                comments[key_id] = comments[val_objct.get('fileRef')]

            # fix target_name
            if object_type == 'PBXNativeTarget':
                build_conf_list = comments[val_objct['buildConfigurationList']]
                new_target_name = comments[key_id]
                new_build_conf_list = build_conf_list.replace('TARGET_NAME',
                                                              new_target_name)
                comments[build_conf_list] = new_build_conf_list

        # add root object note
        rootobject_uid = self.plistdata.get('rootObject')
        comments[rootobject_uid] = 'Project Object'

        self.sections = sections
        self.comments = comments

        self.openfile = open(self.filepath, 'w')
        self.openfile.write('// !$*UTF8*$!\n')
        self.__print_to_file(self.plistdata, '', linefeeds=True)
        self.openfile.close()

    def __write(self, buff):
        """convenient function to write to self.openfile utf-8 encoded."""
        self.openfile.write(buff.encode('utf-8'))

    def __print_to_file(self, node, tab, linefeeds=True):
        """print node raw representation to self.openfile via __handler*."""
        if isinstance(node, dict):
            self.__handle_dict(linefeeds, node, tab)

        elif isinstance(node, list):
            self.__handle_list(linefeeds, node, tab)

        else:
            self.__handle_else(node)

    def __handle_else(self, node):
        """handler for none list or dict type objects."""
        if node and REGEX.match(node).group(0) == node:
            self.__write(node)
        else:
            self.__write('"%s"' % slashed(node))

        if node in self.comments:
            self.__write(" /* %s */" % self.comments[node])

    def __handle_list(self, linefeeds, node, tab):
        """handler for list type objects."""
        self.__write('(\n' if linefeeds else '(')

        for value in node:
            self.__write('\t%s' % tab if linefeeds else '')

            self.__print_to_file(value, '\t' + tab, linefeeds=linefeeds)

            self.__write(',\n' if linefeeds else ',')

        self.__write('%s)' % tab if linefeeds else ')')

    def __handle_dict(self, linefeeds, node, tab):
        """handler for dict type objects."""
        self.__write('{\n' if linefeeds else '{')

        object_type = node.pop('isa', '')

        if object_type != '':
            if linefeeds:
                self.__write('\t%s' % tab)

            self.__write('isa = ')
            self.__print_to_file(object_type, '\t' + tab, linefeeds)

            self.__write(';\n' if linefeeds else '; ')

        for key in sorted(node.iterkeys()):
            if linefeeds:
                self.__write('\t%s' % tab)

            if REGEX.match(key).group(0) == key:
                self.__write('%s = ' % key)
            else:
                self.__write('"%s" = ' % key)

            if key == 'objects':
                self.__handle_objects(linefeeds, tab, key)
            else:
                self.__print_to_file(node[key], '\t%s' % tab, linefeeds)

            self.__write(';\n' if linefeeds else '; ')

        node['isa'] = object_type

        self.__write('%s}' % tab if linefeeds else '}')

    def __handle_objects(self, linefeeds, tab, key):
        """special handler for objects section."""
        self.__write('{\n' if linefeeds else '{')

        for section, linefeed in SECTIONS:
            cur_section = self.sections.get(section)

            if cur_section is None:
                # skip empty
                continue

            self.__write('\n/* Begin %s section */' % section)

            # sort according to item at index 0
            cur_section.sort(cmp=lambda x, y: cmp(x[0], y[0]))

            for key, value in cur_section:
                self.__write('\n')

                if linefeeds:
                    self.__write('\t\t%s' % tab)

                self.__write(key)

                if key in self.comments:
                    self.__write(" /* %s */" % self.comments[key])

                self.__write(" = ")
                self.__print_to_file(value, '\t\t%s' % tab, linefeeds=linefeed)
                self.__write(';')

            self.__write('\n/* End %s section */\n' % section)

        self.__write('%s\t}' % tab)
