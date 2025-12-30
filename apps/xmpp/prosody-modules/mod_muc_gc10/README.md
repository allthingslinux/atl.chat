# Groupchat 1.0 usage statistics gathering

Groupchat 1.0 was probably the protocol that predated
[XEP-0045: Multi-User Chat] and there is still some compatibility that
lives on, in the XEP and in implementations.

This module tries to detect clients still using the GC 1.0 protocol and
what software they run, to determine if support can be removed. 

Since joins in the GC 1.0 protocol are highly ambiguous, some hits
reported will be because of desynchronized MUC clients

# Compatibility

Should work with Prosody 0.10.x and earlier.

It will not work with current trunk, since the MUC code has had major
changes.
