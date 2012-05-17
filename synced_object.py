#!/usr/bin/env python
from logged_object import logged_object, logged_dict, play, summarize
from copy import deepcopy
import json

nextId = 1000

def pull_request_single(so):
    if so._id is None:
        return []
    return [(so._id, so._version_base)]

def make_pull_request(objects, extra_ids=None):
    d = dict(i for so in objects for i in pull_request_single(so))
    if extra_ids is not None:
        d.update(dict((id, 0) for id in extra_ids))
    return json.dumps(d)

def make_pull_response(db, request):
    response = {}
    r = json.loads(request)
    for id_string,version_base in r.iteritems():
        if int(id_string) in db:
            response[id_string] = db[int(id_string)].diff(version_base)
        else:
            response[id_string] = None # deletion notice? assertion?
    return json.dumps(response)

def apply_pull_response(db, response):
    r = json.loads(response)
    for id_string,diff in r.iteritems():
        if diff is not None:
            if int(id_string) in db:
                db[int(id_string)].rebase(diff)
            else:
                db[int(id_string)] = synced_object(id=int(id_string))
                db[int(id_string)].rebase(diff)
        else:
            # object doesn't exist on server. derp.
            pass

def make_push_request(objects):
    request = {}
    for o in objects:
        request[o._id] = o.diff(o._version_base)
    return json.dumps(request)

def apply_push_request(db, request):
    response = {}
    r = json.loads(request)
    for id_string,diff in r.iteritems():
        if int(id_string) in db:
            o = db[int(id_string)]
            if diff[2] == o.latest_version():
                keep = o.fast_forward(diff[0])
            else:
                keep = None
            response[id_string] = (int(id_string), keep, diff[2])
        else:
            global nextId
            newId = nextId
            nextId += 1
            keep = []
            db[newId] = synced_object(newId, diff[0], diff[2], keep=keep)
            response[id_string] = (newId, keep, diff[2])
    return json.dumps(response)

def change_id(db, from_id, to_id):
    db[to_id] = db[from_id]
    db[to_id]._id = to_id
    del db[from_id]
    # XXX relabel references

def apply_push_response(db, response):
    unsynced = []
    r = json.loads(response)
    for id_string,(id, keep, version_base) in r.iteritems():
        if int(id_string) != id:
            change_id(db, int(id_string), id)
        if id in db:
            if keep is not None:
                if False in keep:
                    db[id].cherry_pick(keep, version_base)
                db[id].squash(version_base + sum(keep))
            else:
                unsynced.append(id)
    return unsynced

class synced_object(logged_object):
    def __init__(self, id=None, log=None, version_base=0, base=None, keep=None):
        super(synced_object, self).__init__(log, version_base, base, keep)
        self._weak_references = {}
        self._id = id
    def squash(self, new_version_base):
        self._base = self[new_version_base]._dict
        del self._l[:new_version_base - self._version_base]
        self._l[0] = ''
        self._version_base = new_version_base
    def rebase(self, diff):
        log, log_base, log_version_base = diff
        rebased = False
        if log is not None and len(log) and \
                log_base is None and \
                log_version_base == self._version_base:
            self._l[1:1] = log
            self.squash(log_version_base + len(log))
            rebased = True
        elif log is None and \
                log_base is not None and \
                log_version_base > self._version_base:
            self._base = logged_dict(log_base)
            self._version_base = log_version_base
            rebased = True
        elif log is not None and 0==len(log) and \
                log_base is None and \
                log_version_base == self._version_base:
            print 'id %d: Nothing to do.' % self._id
        else:
            print 'id %d: Rebase not applied.' % self._id
        if rebased:
            x = deepcopy(self._base)
            keep = []
            play(self._l, x, self._globals(), keep)
            for i in xrange(len(self._l)-1, -1, -1):
                if not keep[i]:
                    del self._l[i]
            self._latest._reload()
    def diff(self, from_version):
        # all edits based on from_version
        # so if self._version_base == 1 and from_version == 2,
        # we should return self._l[2:]
        i = from_version-self._version_base+1
        if i <= 0:
            # we don't remember that far back; just send latest blob
            return (None, self._latest._to_dict(),
                    self._version_base + len(self._l) - 1)
        else:
            return (self._l[i:], None, from_version)
    def fast_forward(self, log):
        keep = []
        for stmt in log:
            keep.append(self.mutate(stmt))
        return keep
    def cherry_pick(self, keep, version_base):
        # check version_base
        assert version_base == self._version_base
        # edit log
        for i in xrange(len(keep)-1, -1, -1):
            if not keep[i]:
                del self._l[i+1]
        # reload state
        self._latest._reload()

def sync(client, extra_ids=None):
    apply_pull_response(client, make_pull_response(server, make_pull_request(client.values(), extra_ids)))
    apply_push_response(client, apply_push_request(server, make_push_request(client.values())))

def new(client):
    id = 0
    while id in client:
        id += 1
    x = synced_object(id=id)
    client[id] = x
    return x

clientA = {}
clientB = {}
server = {}

db = clientA
db2 = server

if __name__ == '__main__' and 0:
    tests = [1,2,3,4,5]
    a = new()
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
    print 'Squashing 0-4'
    a.squash(4)
    print
    summarize(a)
    print
    print 'Regression test 1'
    a.zzz
    a.zzz = 1
    if 1:
        print 'Rebase test 1: server has a version 4 setting x.zzz=2'
        a.rebase((['x.zzz = 2'], None, 4))
        summarize(a)
    if 1:
        print 'Rebase test 2: server has forgotten base'
        a.rebase((None, {}, 6))
        summarize(a)
    if 1 in tests:
        print 'Sync test 1: pull, server and client are the same object'
        apply_pull_response(db, make_pull_response(db, make_pull_request(db.values())))
        summarize(a)
    if 2 in tests:
        print 'Sync test 2: pull-push, server hasn\'t heard of object'
        apply_pull_response(db, make_pull_response(db2, make_pull_request(db.values())))
        apply_push_response(db, apply_push_request(db2, make_push_request(db.values())))
        b = db2[a._id]
        summarize(b)
    if 3 in tests:
        print 'Sync test 3: push is idempotent'
        apply_pull_response(db, make_pull_response(db2, make_pull_request(db.values())))
        apply_push_response(db, apply_push_request(db2, make_push_request(db.values())))
        summarize(b)
    if 4 in tests:
        print 'Sync test 4: pull, server is one version behind'
        a.xyzyx = 100
        apply_pull_response(db, make_pull_response(db2, make_pull_request(db.values())))
        summarize(a)
    if 5 in tests:
        print 'Sync test 5: push, server is one version behind'
        apply_push_response(db, apply_push_request(db2, make_push_request(db.values())))
        summarize(b)

show_diagnostics = lambda : None
show_logs = lambda : None

statements = [
    [1, 'x = new(clientA)'],
    [1, 'clientA[x._id].count = 0'],
    [1, 'show_diagnostics()'],
    [0, 'print "Client A state: ", clientA'],
    [0, 'print "Client B state: ", clientB'],
    [0, 'print "Server state:   ", server'],
    [2, None],
    [1, 'sync(clientA)'],
    [1, 'sync(clientB, [x._id])'],
    [1, 'show_diagnostics()'],
    [0, 'print "Client A state: ", clientA'],
    [0, 'print "Client B state: ", clientB'],
    [0, 'print "Server state:   ", server'],
    [2, None],
    [1, 'clientA[x._id].mutate("x.count += 1")'],
    [1, 'clientB[x._id].mutate("x.count += 1")'],
    [1, 'sync(clientA)'],
    [1, 'sync(clientB)'],
    [1, 'show_diagnostics()'],
    [0, 'print "Client A state: ", clientA'],
    [0, 'print "Client B state: ", clientB'],
    [0, 'print "Server state:   ", server'],
    [1, 'show_logs()'],
    [0, 'print "Client A log:   [" + ", ".join(repr(str(x)) if len(x) else "\\\'x = { ... }\\\'" for x in clientA[x._id]._l) + "]"'],
    [0, 'print "Client B log:   [" + ", ".join(repr(str(x)) if len(x) else "\\\'x = { ... }\\\'" for x in clientB[x._id]._l) + "]"'],
    [0, 'print "Server log:     [" + ", ".join(repr(str(x)) if len(x) else "\\\'Create x\\\'" for x in server[x._id]._l) + "]"']]

def demo():
    import sys, time
    promptWritten = False
    for echo, stmt in statements:
        if echo == 1:
            if not promptWritten:
                sys.stdout.write('>>> ')
                sys.stdout.flush()
                time.sleep(.5)
                promptWritten = True
            for c in stmt:
                sys.stdout.write(c)
                sys.stdout.flush()
                time.sleep(.05)
            time.sleep(2.)
            sys.stdout.write('\n')
            sys.stdout.flush()
        elif echo == 2:
            if not promptWritten:
                sys.stdout.write('>>> ')
                sys.stdout.flush()
                promptWritten = True
            time.sleep(5.)
            continue
        exec stmt
        promptWritten = False

