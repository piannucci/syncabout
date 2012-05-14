#!/usr/bin/env python
from copy import deepcopy
import sys

class logged_scalar:
    def __init__(self, scalar, callback=None, name=''):
        self.scalar = scalar
        self.callback = callback
        self.name = name
    def __getattr__(self, attr):
        if not attr in self.__dict__:
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

class logged_dict_callback:
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

class logged_dict:
    def __init__(self, callback=None):
        self.__dict__['_dict'] = {}
        if not isinstance(callback, logged_dict_callback):
            self.__dict__['_callback'] = logged_dict_callback(callback)
        else:
            self.__dict__['_callback'] = callback
    def __getattr__(self, attr):
        if hasattr(self._dict, attr):
            return getattr(self._dict, attr)
        if attr not in self._dict:
            self._dict[attr] = logged_dict(self._callback.child(attr))
        value = self._dict[attr]
        if isinstance(value, logged_dict):
            return value
        else:
            return logged_scalar(value, self._callback.callback, self._callback.childname(attr))
    def __setattr__(self, attr, value):
        if attr == '_callback':
            self.__dict__['_callback'] = logged_dict_callback(value)
            return
        if attr not in self._dict or value != self._dict[attr]:
            self._callback(attr, value)
        self._dict[attr] = value
    def __getitem__(self, item):
        return self.__getattr__(item)
    def __setitem__(self, item, value):
        return self.__setattr__(item, value)
    def __deepcopy__(self, memo):
        x = logged_dict()
        x.__dict__['_dict'] = deepcopy(self._dict, memo)
        x.__dict__['_callback'] = self._callback
        return x

def play_one(x, stmt):
    try:
        exec stmt in {'get': lookup, 'x': x}
        return True
    except:
        print 'Statement %s raised %s' % (repr(stmt), sys.exc_info()[0])
        return False

def play(log, initial=None, callback=None):
    if initial is not None:
        state = deepcopy(initial)
    else:
        state = logged_dict(callback)
    for stmt in log:
        undo = deepcopy(state)
        if not play_one(state, stmt):
            state = undo
    return state

class logged_object_view_ro:
    def __init__(self, lo, version):
        self.__dict__['version'] = version
        self.__dict__['lo'] = lo
        self.__dict__['_dict'] = play(lo.l[:version+1])
    def __setattr__(self, attr, value):
        raise AttributeError('attribute \'%s\' is read-only' % attr)
    def __getattr__(self, attr):
        return self._dict[attr]
    def __delattr__(self, attr):
        raise AttributeError('attribute \'%s\' is read-only' % attr)
    def __repr__(self):
        return '<logged_object 0x%x(%d)+ro %s>' % (id(self.lo), self.version, repr(self._dict))

class logged_object_view_rw:
    def __init__(self, lo, version):
        self.__dict__['version'] = version
        self.__dict__['lo'] = lo
        self.__dict__['_dict'] = play(lo.l[:version+1])
        self._dict._callback = lo._mutate
    def __setattr__(self, attr, value):
        self._dict[attr] = value
    def __getattr__(self, attr):
        return self._dict[attr]
    def __delattr__(self, attr):
        del self._dict[attr]
    def __repr__(self):
        return '<logged_object 0x%x(%d)+rw %s>' % (id(self.lo), self.version, repr(self._dict))

class logged_object:
    def __init__(self, l=None):
        if l is None:
            l = []
        self.__dict__['l'] = l
        self.__dict__['latest'] = logged_object_view_rw(self, len(self.l)-1)
        self.__dict__['_ignoring'] = 0
    def __getitem__(self, item):
        if item >= len(self.l):
            item = len(self.l) - 1
        if item == -1:
            return self.latest
        else:
            return logged_object_view_ro(self, item)
    def _mutate(self, stmt):
        if self._ignoring == 0:
            self.__dict__['l'].append(stmt)
            print 'Logged %s' % repr(stmt)
    def mutate(self, stmt):
        self.__dict__['l'].append(stmt)
        print 'Logged %s' % repr(stmt)
        ll = len(self.l)
        state = self.latest._dict
        undo = deepcopy(state)
        self.__dict__['_ignoring'] += 1
        if not play_one(state, stmt):
            self.latest.__dict__['_dict'] = undo
            ll -= 1
            print 'Undo %s' % repr(stmt)
        self.__dict__['_ignoring'] -= 1
        del self.l[ll:]
    def __setattr__(self, attr, value):
        return self.latest.__setattr__(attr, value)
    def __getattr__(self, attr):
        return self.latest.__getattr__(attr)
    def __delattr__(self, attr):
        return self.latest.__delattr__(attr)

if __name__ == '__main__':
    def lookup(id):
        pass
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
    print a.l
    for i in xrange(0, len(a.l)):
        print a[i]
    print a[-1]
