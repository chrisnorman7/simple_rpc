"""Test the Python portions of the code."""

from json import dumps
from pytest import raises
from simplerpc import WSProtocol, SimpleRPCContainer


class CommandWorks(Exception):
    pass


class ArgsWorks(Exception):
    pass


class KwargsWorks(Exception):
    pass


class BothWorks(Exception):
    pass


class MyProtocol(WSProtocol):
    def send(self, *args, **kwargs):
        self.send_args = args
        self.send_kwargs = kwargs


c = SimpleRPCContainer(protocol=MyProtocol)
p = c.protocol()


@c.register
def works():
    raise CommandWorks()


@c.register
def with_args(first, second):
    assert first == 'hello'
    assert second == 'world'
    raise ArgsWorks()


@c.register
def with_kwargs(first=None, hello=None):
    assert first == 'second'
    assert hello == 'world'
    raise KwargsWorks()


@c.register
def with_both(first, hello=None):
    assert first == 'second'
    assert hello == 'world'
    raise BothWorks()


def test_protocol_init():
    assert p.id == 0
    assert p.waiters == {}


def test_handle_command_valid():
    data = dumps(['works', [], {}, 0])
    with raises(CommandWorks):
        p.onMessage(data)


def test_handle_command_invalid():
    data = dumps(['Invalid', [], {}, 0])
    with raises(RuntimeError):
        p.onMessage(data)


def test_handle_command_arguments():
    # With args:
    data = dumps(['with_args', ['hello', 'world'], {}, 0])
    with raises(ArgsWorks):
        p.onMessage(data)
    # With kwargs:
    data = dumps(['with_kwargs', [], dict(first='second', hello='world'), 0])
    with raises(KwargsWorks):
        p.onMessage(data)
    # With both:
    data = dumps(['with_both', ['second'], dict(hello='world'), 0])
    with raises(BothWorks):
        p.onMessage(data)
