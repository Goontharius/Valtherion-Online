from weakref import WeakKeyDictionary
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy import JSON


class MutableJSONDict(MutableDict):
    _json_parent = None

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        for k in list(dict.keys(self)):
            child = dict.__getitem__(self, k)
            dict.__setitem__(self, k, _json_coerce(child))
            _json_attach(dict.__getitem__(self, k), self, k)

    @classmethod
    def coerce(cls, key, value):
        if isinstance(value, MutableJSONDict):
            return value
        if isinstance(value, MutableJSONList):
            return value
        if isinstance(value, dict):
            return cls(value)
        return MutableDict.coerce(key, value)

    def __setitem__(self, key, value):
        child = _json_coerce(value)
        _json_attach(child, self, key)
        dict.__setitem__(self, key, child)
        _json_mark(self)

    def __delitem__(self, key):
        child = dict.get(self, key)
        if isinstance(child, (MutableJSONDict, MutableJSONList)):
            child._json_parent = None
        dict.__delitem__(self, key)
        _json_mark(self)

    def update(self, *a, **kw):
        dict.update(self, *a, **kw)
        for k in list(dict.keys(self)):
            child = dict.__getitem__(self, k)
            if not isinstance(child, (MutableJSONDict, MutableJSONList)):
                dict.__setitem__(self, k, _json_coerce(child))
                _json_attach(dict.__getitem__(self, k), self, k)
        _json_mark(self)

    def pop(self, *args):
        key = args[0]
        child = dict.get(self, key)
        result = dict.pop(self, *args)
        if isinstance(child, (MutableJSONDict, MutableJSONList)):
            child._json_parent = None
        _json_mark(self)
        return result

    def popitem(self):
        key, child = dict.popitem(self)
        if isinstance(child, (MutableJSONDict, MutableJSONList)):
            child._json_parent = None
        _json_mark(self)
        return key, child

    def clear(self):
        dict.clear(self)
        _json_mark(self)

    def setdefault(self, *args):
        result = dict.setdefault(self, *args)
        key = args[0]
        if not isinstance(result, (MutableJSONDict, MutableJSONList)):
            dict.__setitem__(self, key, _json_coerce(result))
            _json_attach(dict.__getitem__(self, key), self, key)
        _json_mark(self)
        return dict.__getitem__(self, key)


class MutableJSONList(MutableList):
    _json_parent = None

    def __init__(self, *args, **kwargs):
        list.__init__(self, *args, **kwargs)
        for i in range(len(self)):
            child = list.__getitem__(self, i)
            list.__setitem__(self, i, _json_coerce(child))
            _json_attach(list.__getitem__(self, i), self, i)

    @classmethod
    def coerce(cls, key, value):
        if isinstance(value, MutableJSONList):
            return value
        if isinstance(value, MutableJSONDict):
            return value
        if isinstance(value, list):
            return cls(value)
        return MutableList.coerce(key, value)

    def __setitem__(self, index, value):
        child = _json_coerce(value)
        _json_attach(child, self, index)
        list.__setitem__(self, index, child)
        _json_mark(self)

    def __delitem__(self, index):
        child = list.__getitem__(self, index)
        if isinstance(child, (MutableJSONDict, MutableJSONList)):
            child._json_parent = None
        list.__delitem__(self, index)
        _json_mark(self)

    def append(self, value):
        child = _json_coerce(value)
        _json_attach(child, self, len(self))
        list.append(self, child)
        _json_mark(self)

    def extend(self, values):
        for v in values:
            child = _json_coerce(v)
            _json_attach(child, self, len(self))
            list.append(self, child)
        _json_mark(self)

    def insert(self, index, value):
        child = _json_coerce(value)
        _json_attach(child, self, index)
        list.insert(self, index, child)
        _json_mark(self)

    def remove(self, value):
        index = list.index(self, value)
        child = list.__getitem__(self, index)
        if isinstance(child, (MutableJSONDict, MutableJSONList)):
            child._json_parent = None
        list.remove(self, value)
        _json_mark(self)

    def pop(self, *args):
        result = list.pop(self, *args)
        if isinstance(result, (MutableJSONDict, MutableJSONList)):
            result._json_parent = None
        _json_mark(self)
        return result

    def clear(self):
        list.clear(self)
        _json_mark(self)


def _json_coerce(value):
    if isinstance(value, MutableJSONDict):
        return value
    if isinstance(value, MutableJSONList):
        return value
    if isinstance(value, dict):
        return MutableJSONDict(value)
    if isinstance(value, list):
        return MutableJSONList(value)
    return value


def _json_attach(child, parent, key):
    if isinstance(child, (MutableJSONDict, MutableJSONList)):
        child._json_parent = parent


def _json_mark(node):
    while node is not None:
        parent = node._json_parent
        if parent is None:
            node.changed()
            return
        node = parent


def MutableJSON():
    return MutableJSONDict.as_mutable(JSON)


def MutableJSONArray():
    return MutableJSONList.as_mutable(JSON)
