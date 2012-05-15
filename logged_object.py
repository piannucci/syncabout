#!/usr/bin/env python
from copy import deepcopy
import sys

class logged_scalar:
    def __init__(self, scalar, callback=None, name=''):
        self.scalar = scalar
        self.callback = callback
        self.name = name
    def __getattr__(self, attr):
        if hasattr(self.scalar, attr):
            if attr in ['add', 'remove', 'clear', 'update', 'append',
                        'extend', 'insert', 'pop', 'sort', '__iadd__']:
                self.__dict__[attr] = lambda *args: self.__f__(attr, *args)
            else:
                self.__dict__[attr] = getattr(self.scalar, attr)
        else:
            raise AttributeError("%s object has no attribute %s" % (repr(self.scalar.__name__), repr(attr)))
        return self.__dict__[attr]
    def __f__(self, fname, *args, **kwargs):
        stmt = 'x.%s(%s)' % (self.name + fname, ', '.join(map(repr, args) + ['%s=%s' % (k, repr(v)) for k,v in kwargs]))
        if self.callback is not None:
            self.callback(stmt)
        return getattr(self.scalar, fname)(*args, **kwargs)

class logged_dict_callback(object):
    def __init__(self, callback, path=''):
        self.path = path
        self.callback = callback
    def __call__(self, attr, value):
        if self.callback is not None:
            stmt = 'x.%s=%s' % (self.path + attr, repr(value))
            self.callback(stmt)
    def child(self, attr):
        return logged_dict_callback(self.callback, self.path + attr + '.')
    def childname(self, attr):
        return self.path + attr + '.'

class logged_dict(object):
    def __init__(self, callback=None):
        self.__dict__['_dict'] = {}
        self.__dict__['_readonly'] = False
        self._callback = callback
    def _set_readonly(self, ro):
        self._readonly = ro
        for v in self._dict.itervalues():
            if hasattr(v, '_set_readonly'):
                v._set_readonly(ro)
    def __getattr__(self, attr):
        if hasattr(self._dict, attr):
            return getattr(self._dict, attr)
        if attr not in self._dict and not self._readonly and not attr.startswith('__'):
            self._dict[attr] = logged_dict(self._callback.child(attr))
        value = self._dict[attr]
        if isinstance(value, logged_dict):
            return value
        else:
            return logged_scalar(value, self._callback.callback, self._callback.childname(attr))
    def __setattr__(self, attr, value):
        if self._readonly:
            raise AttributeError('attribute \'%s\' is read-only' % attr)
        if attr == '_callback':
            if not isinstance(value, logged_dict_callback):
                value = logged_dict_callback(value)
        if attr.startswith('_'):
            return self.__dict__.__setitem__(attr, value)
        if attr not in self._dict or \
                value != self._dict[attr]:
            self._callback(attr, value)
        self._dict[attr] = value
    def __getitem__(self, item):
        return self.__getattr__(item)
    def __setitem__(self, item, value):
        return self.__setattr__(item, value)
    def __deepcopy__(self, memo):
        x = logged_dict()
        x._dict = deepcopy(self._dict, memo)
        x._callback = self._callback
        return x
    def __eq__(self, other):
        A = self._dict
        B = other
        if isinstance(B, logged_dict):
            B = B._dict
        return A == B
    def __ne__(self, other):
        A = self._dict
        B = other
        if isinstance(B, logged_dict):
            B = B._dict
        return A != B
    def __coerce__(self, other):
        return NotImplemented
    def __repr__(self):
        return repr(self._dict)

def play_one(x, stmt, globals=None):
    if globals is None:
        globals = {}
    try:
        exec stmt in globals, {'x': x}
        return True
    except:
        print 'Statement %s raised %s' % (repr(stmt), sys.exc_info()[0])
        return False

def play(log, onto, globals=None):
    if onto is not None:
        state = onto
    else:
        state = logged_dict(callback)
    for stmt in log:
        undo = deepcopy(state)
        if not play_one(state, stmt, globals):
            state = undo
    return state

class logged_object_view_ro(object):
    def __init__(self, lo, version):
        self._version = version
        self._lo = lo
        self._dict = deepcopy(lo._base)
        play(lo._l[:version-lo._version_base+1], self._dict, lo._globals())
        self._dict._set_readonly(True)
    def __setattr__(self, attr, value):
        if attr.startswith('_'):
            return self.__dict__.__setitem__(attr, value)
        raise AttributeError('attribute \'%s\' is read-only' % attr)
    def __getattr__(self, attr):
        return self._dict[attr]
    def __delattr__(self, attr):
        raise AttributeError('attribute \'%s\' is read-only' % attr)
    def __repr__(self):
        return '<logged_object 0x%x(%d)+ro %s>' % (id(self._lo), self._version, repr(self._dict))
    def __eq__(self, other):
        return self._dict._dict == other._dict._dict

class logged_object_view_rw(object):
    def __init__(self, lo, version):
        self._version = version
        self._lo = lo
        self._dict = deepcopy(lo._base)
        play(lo._l[:version+1], self._dict, lo._globals())
        self._dict._callback = lo._mutate
    def __setattr__(self, attr, value):
        if attr.startswith('_'):
            return self.__dict__.__setitem__(attr, value)
        return self._dict.__setitem__(attr, value)
    def __getattr__(self, attr):
        return self._dict[attr]
    def __delattr__(self, attr):
        del self._dict[attr]
    def __repr__(self):
        return '<logged_object 0x%x(%d)+rw %s>' % (id(self._lo), self._version, repr(self._dict))
    def __eq__(self, other):
        return self._dict._dict == other._dict._dict

class logged_object(object):
    def __init__(self, log=None, version_base=0, base=None):
        if log is None:
            log = ['']
        if base is None:
            base = logged_dict()
        self._l = log
        self._base = base
        self._version_base = version_base
        self._ignoring = 0
        self._latest = logged_object_view_rw(self, -1)
    def __getitem__(self, item):
        if item != -1:
            item = min(item, len(self._l) - 1 + self._version_base)
            item = max(item, self._version_base)
        if item == -1:
            return self._latest
        else:
            return logged_object_view_ro(self, item)
    def _mutate(self, stmt):
        if self._ignoring == 0:
            self._l.append(stmt)
            print 'Logged %s' % repr(stmt)
    def mutate(self, stmt):
        self._l.append(stmt)
        print 'Logged %s' % repr(stmt)
        ll = len(self._l)
        state = self._latest._dict
        undo = deepcopy(state)
        self._ignoring += 1
        if not play_one(state, stmt, self._globals()):
            self._latest._dict = undo
            ll -= 1
            print 'Undo %s' % repr(stmt)
        self._ignoring -= 1
        del self._l[ll:]
    def __setattr__(self, attr, value):
        if attr.startswith('_'):
            return self.__dict__.__setitem__(attr, value)
        return self._latest.__setattr__(attr, value)
    def __getattr__(self, attr):
        return self._latest.__getattr__(attr)
    def __delattr__(self, attr):
        return self._latest.__delattr__(attr)
    def _globals(self):
        return {}
    def flatten(self, new_version_base):
        self._base = self[new_version_base]._dict
        del self._l[:new_version_base - self._version_base]
        self._l[0] = ''
        self._version_base = new_version_base

if __name__ == '__main__':
    a = logged_object()
    a.foo = 1
    a.foo += 2
    a.mutate('x.foo += 2')
    a.bar = [100]
    a.bar += [1,2,3]
    a.bar.append(4)
    a.baz.mumble.frotz = set()
    a.baz.mumble.frotz.add(2)
    a.mutate('raise ValueError()')
    print
    print 'Base:'
    print a._base
    print
    print 'Edit log:'
    print a._l
    print
    print 'Versions:'
    for i in xrange(0, len(a._l)):
        print repr(a[i+a._version_base])
    print 'Latest:'
    print repr(a[-1])
    print
    print 'Version -1 == version 8:', a[-1] == a[8]
    print 'Version -1 == version 7:', a[-1] == a[7]
    print
    print 'Flattening 0-4'
    a.flatten(4)
    print
    print 'Base:'
    print a._base
    print
    print 'Edit log:'
    print a._l
    print
    print 'Versions:'
    for i in xrange(0, len(a._l)):
        print repr(a[i+a._version_base])
    print 'Latest:'
    print repr(a[-1])
    print
    print 'Version -1 == version 8:', a[-1] == a[8]
    print 'Version -1 == version 7:', a[-1] == a[7]
    print
    print 'Regression test 1'
    a.zzz
    a.zzz = 1
