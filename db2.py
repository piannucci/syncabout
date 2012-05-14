#!/usr/bin/env python

class db:
    def __init__(self):
        self.h = {}
        self.next = next
        if self.next is not None:
            self.depth = self.next + 1
        else:
            self.depth = 0
        self.nextId = 0
        self.normalization = {}
    def __getitem__(self, slice):
        return self.h[slice] if slice in self.h else \
               self.next[slice] if self.next else None
    def add(self):
        id = (None,) * self.depth + (self.nextId,)
        self.nextId += 1
        self.h[id] = x
        return id
    def rem(self, id):
        if id in self.h:
            del self.h[id]
        elif self.next is not None:
            self.next.rem(id)

def lookup(id):
    # look up id in global db
    pass

