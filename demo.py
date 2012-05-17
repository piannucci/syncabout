from synced_object import clientA, clientB, server, new, sync

x = new(clientA)
clientA[x._id].count = 0

print "Client A state: ", clientA
print "Client B state: ", clientB
print "Server state:   ", server

sync(clientA)
sync(clientB, [x._id])

print "Client A state: ", clientA
print "Client B state: ", clientB
print "Server state:   ", server

clientA[x._id].mutate("x.count += 1")
clientB[x._id].mutate("x.count += 1")

sync(clientA)
sync(clientB)

print "Client A state: ", clientA
print "Client B state: ", clientB
print "Server state:   ", server
print
print "Client A log:   [" + ", ".join(repr(str(x)) if len(x) else "\\\'x = { ... }\\\'" for x in clientA[x._id]._l) + "]"
print "Client B log:   [" + ", ".join(repr(str(x)) if len(x) else "\\\'x = { ... }\\\'" for x in clientB[x._id]._l) + "]"
print "Server log:     [" + ", ".join(repr(str(x)) if len(x) else "\\\'Create x\\\'" for x in server[x._id]._l) + "]"
