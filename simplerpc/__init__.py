"""RPC without complications."""

from inspect import getargspec
from json import loads, dumps
from attr import attrs, attrib, Factory
from autobahn.twisted.websocket import WebSocketServerProtocol

reserved_names = ('_return', '_error', '_commands')


@attrs
class Waiter:
    """Acts like a JavaScript promise."""

    id = attrib()
    on_return = attrib(default=Factory(lambda: None))
    on_error = attrib(default=Factory(lambda: None))

    def then(self, func):
        """Add a success callback."""
        self.on_return = func
        return self

    def catch(self, func):
        """Add an error callback."""
        self.on_error = func
        return self


class WSProtocol(WebSocketServerProtocol):
    """The protocol for bi-directional communication."""

    rpc_container = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = 0
        self.waiters = {}

    def onOpen(self):
        """Socket is open. Send all supported commands."""
        self.do_commands()

    def onMessage(self, payload, binary=False):
        """Decode the data into [name, args, kwargs, id], and look for a
        command with the given name. If a command is found it will be called
        with args and kwargs, otherwise an error will be sent back. The return
        value from the function will be sent back with the given ID. If an
        error is raised then that will be sent."""
        if binary:
            raise RuntimeError('Binary is not supported yet.')
        name, args, kwargs, rid = loads(payload)
        self.handle_command(name, args, kwargs, rid)

    def handle_command(self, name, args, kwargs, rid):
        """Handle a command."""
        if name in reserved_names:
            if name == '_commands':
                self.do_commands()
            elif rid in self.waiters:
                w = self.waiters[rid]
                func = getattr(w, 'on%s' % name)
                if func is not None:
                    func(*args, **kwargs)
            else:
                raise RuntimeError(
                    '%s value for invalid ID %r.' % (name.title(), rid)
                )
        elif name in self.rpc_container.commands:
            func = self.rpc_container.commands[name]
            try:
                value = func(*args, **kwargs)
                self.do_return(rid, value)
            except Exception as e:
                self.do_error(rid, e)
        else:
            raise RuntimeError('Invalid command name %r.' % name)

    def send_command(self, name, *args, **kwargs):
        """Send a command with args and kwargs."""
        data = dumps(dict(name=name, args=args, kwargs=kwargs))
        self.sendMessage(data.encode())

    def do_return(self, rid, value):
        """Send a return value."""
        self.send_command('_return', rid, value)

    def do_error(self, rid, e):
        """Send an error back to a call."""
        value = str(e)
        self.send_command('_error', rid, value)

    def do_commands(self):
        """Send a list of command names to the client."""
        self.send_command('_commands', self.rpc_container.get_commands())

    def call(self, name, *args, **kwargs):
        """Call a javascript function. Returns a Waiter instance which can be
        used like a JavaScript promise."""
        self.id += 1
        args = [self.id, args]
        w = Waiter(self.id)
        self.send_command('command', *args, **kwargs)
        return w


@attrs
class SimpleRPCContainer:
    """Holds references to decorated functions that can be called from
    JavaScript."""

    protocol = attrib(default=Factory(lambda: WSProtocol))
    commands = attrib(default=Factory(dict), init=False)

    def __attrs_post_init__(self):
        self.protocol.rpc_container = self

    def register(self, func):
        """Register a function so that it can be called from JavaScript."""
        name = func.__name__
        if name in reserved_names:
            raise NameError('Name %r is invalid: %r.' % (name, reserved_names))
        self.commands[name] = func

    def get_commands(self):
        """Returns a list of function names that JavaScript can call."""
        commands = []
        for name, func in self.commands.items():
            commands.append([name, getargspec(func).args])
        return commands
