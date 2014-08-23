"""wrapper nodes for pbx objects."""

import collections
import mod_pbxproj


class XcodeNode(collections.MutableMapping):
    """wrapper for pbx objects that makes it easy to do recursive functions."""
    def __init__(self, project, parent, guid, *args, **kwargs):
        self.project = project
        self.parent = parent
        self.guid = guid
        self.rawdata = self.project.mod_pbxproj
        self.nodedata = self.project.mod_pbxproj.get('objects').get(guid)

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
        elif isinstance(value, list) or isinstance(value, mod_pbxproj.PBXList):
            return [self.__convert(val) for val in value]
        elif isinstance(value, dict) or isinstance(value, mod_pbxproj.PBXDict):
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


class XcodeObject():
    """xprojedit interface starting point."""
    def __init__(self, filepath):
        self.filepath = filepath
        self.mod_pbxproj = mod_pbxproj.XcodeProject.Load(self.filepath)

    def root(self):
        """returns the first node."""
        rootid = self.mod_pbxproj.get('rootObject')
        return XcodeNode(project=self,
                         parent=None,
                         guid=rootid)
