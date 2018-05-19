#!/usr/bin/python

from charms.reactive import (
    hook,
    RelationBase,
)
from charmhelpers.core.hookenv import atexit
from charms.reactive.bus import (
    StateList,
    State,
)
from charms.reactive import scopes


class LXDCluster(RelationBase):
    scope = scopes.SERVICE

    class states(StateList):
        connected = State('{relation_name}.connected')
        joined = State('{relation_name}.joined')
        departed = State('{relation_name}.departed')

    @hook('{peers:lxd-cluster}-relation-{joined,changed}')
    def joined_or_changed(self):
        self.set_state('{relation_name}.connected')
        self.set_trigger_like_state(self.states.joined)

    @hook('{peers:lxd-cluster}-relation-departed')
    def departed(self):
        self.set_trigger_like_state(self.states.departed)
        if not self.units():
            self.remove_state('{relation_name}.connected')

    def units(self):
        """ Retrieve all connected hosts private-address
        Works only in hook context. """
        hosts = []
        for conv in self.conversations():
            hosts.append(conv.get_remote('private-address'))
        return hosts

    def set_trigger_like_state(self, state):
        """ States set via this helper will be unset at the end of the
        hook invocation. This behves somewhat like a event rather than a state.
        """
        self.set_state(state)

        def cleanup_func():
            self.remove_state(state)
        atexit(cleanup_func)
