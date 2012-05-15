#!/usr/bin/env python
from logged_object import logged_object

class synced_object(logged_object):
    def __init__(self, id=None, log=None, version_base=0, base=None):
        super(synced_object, self).__init__(log, version_base, base)
        self._weak_references = {}
