# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import sys
from parglare.termui import s_attention as _a

if sys.version < '3':
    text = unicode  # NOQA
else:
    text = str


class Location(object):
    """
    Represents a location (point or span) of the object in the source code.

    Args:
    context(Context): Parsing context used to populate this object.

    Attributes:
    input_str: The input string (from context) being parsed.
    file_name(str): The name (path) to the file this location refers to.
    start_position(int): The position of the span if applicable
    end_position(int): The end of the span if applicable.
    position(int): An absolute position of this location inside the file.
    line, column (int): The line/column calculated from the position and
        input_str.
    """

    __slots__ = ['context', 'file_name',
                 '_line', '_column',
                 '_line_end', '_column_end']

    def __init__(self, context=None, file_name=None):

        self.context = context
        self.file_name = file_name

        # Evaluate this only when string representation is needed.
        # E.g. during error reporting
        self._line = None
        self._column = None

        self._line_end = None
        self._column_end = None

    @property
    def line(self):
        if self._line is None:
            self.evaluate_line_col()
        return self._line

    @property
    def line_end(self):
        if self._line_end is None:
            self.evaluate_line_col_end()
        return self._line_end

    @property
    def column(self):
        if self._column is None:
            self.evaluate_line_col()
        return self._column

    @property
    def column_end(self):
        if self._column_end is None:
            self.evaluate_line_col_end()
        return self._column_end

    def evaluate_line_col(self):
        context = self.context
        if hasattr(context, 'start_position') \
                and context.start_position:
            position = context.start_position
        else:
            position = context.position
        self._line, self._column = pos_to_line_col(context.input_str,
                                                   position)

    def evaluate_line_col_end(self):
        context = self.context
        if hasattr(context, 'end_position') \
                and context.end_position:
            self._line_end, self._column_end = \
                pos_to_line_col(context.end_position)

    def __getattr__(self, name):
        return getattr(self.context, name)

    def __str__(self):
        line, column = self.line, self.column
        context = self.context
        if line is not None:
            return ('{}{}:{}:"{}"'
                    .format("{}:".format(self.file_name)
                            if self.file_name else "",
                            line, column,
                            position_context(context.input_str,
                                             context.position)))
        elif self.file_name:
            return _a(self.file_name)
        else:
            return "<Unknown location>"

    def __repr__(self):
        return str(self)


def position_context(input_str, position):
    """
    Returns position context string.
    """
    start = max(position-10, 0)
    c = text(input_str[start:position]) + _a(" **> ") \
        + text(input_str[position:position+10])
    return replace_newlines(c)


def replace_newlines(in_str):
    try:
        return in_str.replace("\n", "\\n")
    except AttributeError:
        return in_str


def load_python_module(mod_name, mod_path):
    """
    Loads Python module from an arbitrary location.
    See https://stackoverflow.com/questions/67631/how-to-import-a-module-given-the-full-path  # noqa
    """
    if sys.version_info >= (3, 5):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            mod_name, mod_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    elif sys.version_info >= (3, 3):
        from importlib.machinery import SourceFileLoader
        module = SourceFileLoader(
            mod_name, mod_path).load_module()
    else:
        import imp
        module = imp.load_source(mod_name, mod_path)

    return module


def get_collector():
    """
    Produces action/recognizers collector/decorator that will collect all
    decorated objects under dictionary attribute `all`.
    """
    all = {}

    class Collector(object):
        def __call__(self, name_or_f):
            """
            If called with action/recognizer name return decorator.
            If called over function apply decorator.
            """
            is_name = type(name_or_f) in [str, text]

            def decorator(f):
                if is_name:
                    name = name_or_f
                else:
                    name = f.__name__
                objects = all.get(name, None)
                if objects:
                    if type(objects) is list:
                        objects.append(f)
                    else:
                        all[name] = [objects, f]
                else:
                    all[name] = f
                return f
            if is_name:
                return decorator
            else:
                return decorator(name_or_f)

    objects = Collector()
    objects.all = all
    return objects


def pos_to_line_col(input_str, position):
    """
    Returns position in the (line,column) form.
    """

    if position is None:
        return None, None

    if type(input_str) is not text:
        # If we are not parsing string
        return 1, position

    line = 1
    old_pos = 0
    try:
        cur_pos = input_str.index("\n")
        while cur_pos < position:
            line += 1
            old_pos = cur_pos + 1
            cur_pos = input_str.index("\n", cur_pos + 1)
    except ValueError:
        pass

    return line, position - old_pos
