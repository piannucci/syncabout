from collections import defaultdict
nextVersion = 0
nextId = 0

class Node:
    def __init__(self, blob, type):
        global nextId, nextVersion
        self.id = nextId
        nextId += 1
        self.blob = blob
        self.type = type
        self.version = nextVersion # should be (server version, client version)
        self.deleted = False
        nextVersion += 1

class NodeType:
    def __init__(self, name):
        self.name = name

class Edge:
    def __init__(self, idFrom, idTo, type):
        global nextVersion
        self.idFrom = idFrom
        self.idTo = idTo
        self.type = type
        self.version = nextVersion
        nextVersion += 1

class EdgeType:
    def __init__(self, name):
        self.name = name

class Subscriber:
    def __init__(self, name):
        self.name = name
    def push(self, id):
        print 'Pushed %d to %s' % (id, self.name)

nodesById = {}
nodesByVersion = defaultdict(set)
edgesByFrom = defaultdict(set)
edgesByTo = defaultdict(set)
edgesByVersion = defaultdict(set)
nodeTypes = set()
edgeTypes = set()
subscribersById = {}
subscribersToNode = defaultdict(set)

def notifySubscribers(id):
    for s in subscribersToNode[id]:
        s.push(id)

def addNode(blob, type):
    n = Node(blob, type)
    nodesById[n.id] = n
    nodesByVersion[n.version].add(n)
    return n

def addEdge(idFrom, idTo, type):
    e = Edge(idFrom, idTo, type)
    edgesByFrom[idFrom].add(e)
    edgesByTo[idTo].add(e)
    edgesByVersion[e.version].add(e)
    notifySubscribers(idFrom)

def delEdge(idFrom, idTo, type):
    deletedEdges = set()
    deletedEdges.update(set(e for e in edgesByFrom[idFrom] if e.idTo == idTo and e.type == type))
    deletedEdges.update(set(e for e in edgesByTo[idTo] if e.idFrom == idFrom and e.type == type))
    edgesByFrom[idFrom].difference_update(deletedEdges)
    edgesByTo[idTo].difference_update(deletedEdges)
    for e in deletedEdges:
        edgesByVersion[e.version].discard(e)
    notifySubscribers(idFrom)

def delNode(id):
    global nextVersion
    if not id in nodesById:
        raise "No such node"
    notifySubscribers(id)
    n = nodesById[id]
    nodesByVersion[n.version].discard(n)
    del nodesById[id]
    for e in edgesByTo[id]:
        notifySubscribers(e.idFrom)
    deletedEdges = set()
    deletedEdges.update(edgesByTo[id])
    deletedEdges.update(edgesByFrom[id])
    edgesByTo[id].clear()
    edgesByFrom[id].clear()
    for e in deletedEdges:
        edgesByVersion[e.version].discard(e)
    subscribersToNode[id].clear()
    nextVersion += 1

def addSubscription(idFrom, subscriber):
    subscribersToNode[idFrom].add(subscriber);
    subscriber.push(idFrom)

def mutateNode(id, blob):
    global nextVersion
    if not id in nodesById:
        raise "No such node"
    n = nodesById[id]
    n.blob = blob
    nodesByVersion[n.version].discard(n)
    n.version = nextVersion
    nodesByVersion[n.version].add(n)
    notifySubscribers(id)
    for e in edgesByTo[id]:
        edgesByVersion[e.version].discard(e)
        e.version = nextVersion
        edgesByVersion[e.version].add(e)
        notifySubscribers(e.idFrom)
    nextVersion += 1

# subscribe to the things you care about, but not leaves
# mutating an object mutates its in-edge, so subscribers to its parent notice
# sync by posting the last version number you've seen, then getting all the
# objects up to the latest version that you are subscribed to
# subscriptions are implicit in application logic and explicit in the database
# integrity checking can be performed with hash splay tree
# edge mutations result in the pointed-to object getting synced

def pull(subscriber, version):
    versions = set(i for i in edgesByVersion.iterkeys() if i > version)
    edges = set()
    nodes = set()
    for v in versions:
        edges.update(edgesByVersion[v])
    for e in edges:
        nodes.add(nodesById[e.nTo])
    versions = set(i for i in nodesByVersion.iterkeys() if i > version)
    for v in versions:
        nodes.update(nodesByVersion[v])
