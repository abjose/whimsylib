import functools
import logging
import inspect
import re

from whimsylib import say
from whimsylib.globals import poll_events


class _InvalidCommand(Exception):
    pass


class _CommandTemplate:

    _FORMULA_PATTERN = re.compile("^[a-z][a-z0-9]*$")
    _ARGUMENT_PATTERN = re.compile("^[A-Z][A-Z0-9]*$")

    def __init__(self, command_template, context=None):
        match = []
        self._prefix = None
        self._arguments = []

        # TODO: Do we need the prefixes?
        for i, word in enumerate(command_template.strip().split()):
            logging.debug("word IS %s", word)
            if self._FORMULA_PATTERN.search(word):
                match.append(r"" + word)
            elif self._ARGUMENT_PATTERN.search(word):
                if i == 0:
                    raise _InvalidCommand("Commands must start with a minuscule word.")
                # Prefix consists of all non-argument terms before first argument.
                if self._prefix is None:
                    self._prefix = " ".join(match)
                word = word.lower()
                self._arguments.append(word)
                match.append(r"" + f"(?P<{word}>.*)")
            else:
                raise _InvalidCommand(
                    "All words in a command must start with a letter and "
                    "consist only of letters and numbers. Letters in each "
                    "word must all be of the same case."
                )
        self._pattern = re.compile(r"^" + r" +".join(match) + r"$", re.IGNORECASE)
        logging.debug(self._pattern)

    @property
    def arguments(self):
        return self._arguments

    @property
    def prefix(self):
        return self._prefix

    def match(self, command):
        return self._pattern.match(command)


class _CommandHandler:

    _COMMANDS = []

    @classmethod
    def register(cls, command, function, context=None, **kwargs):
        command_template = _CommandTemplate(command, context)

        signature = inspect.signature(function)
        try:
            _ = signature.bind(*command_template.arguments, **kwargs)
        except TypeError:
            raise _InvalidCommand(
                f"Function with signature {signature} cannot accept arguments "
                f"[{', '.join(command_template.arguments)}]."
            )

        cls._COMMANDS.append((command_template, function, kwargs))

    @classmethod
    def handle(cls, command):
        command = command.lower().strip()
        max_matches = -1
        call_me = None
        func_me = None
        for template, function, kwargs in cls._COMMANDS:
            match = template.match(command)
            if match is not None:
                call_kwargs = match.groupdict()
                if len(call_kwargs) > max_matches:
                    max_matches = len(call_kwargs)
                call_kwargs.update(kwargs)
                call_me = call_kwargs
                func_me = function
        if func_me is not None:
            func_me(**call_me)
        else:
            say.insayne(f'I don\'t understand "{command}."')


def handle(command):
    _CommandHandler.handle(command)


def poll(poll_before=True, poll_after=True):
    def poll_decorator(function):
        @functools.wraps(function)
        def poll_wrapped(*args, **kwargs):
            with poll_events(poll_before, poll_after):
                return function(*args, **kwargs)

        return _poll_wrapped

    return poll_decorator


def when(command, context=None, **kwargs):
    """Decorator for command functions."""

    def when_wrapped(function):
        _CommandHandler.register(command, function, context, **kwargs)
        return function

    return when_wrapped
