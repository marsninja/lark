###{standalone
#
#
#   Lark Stand-alone Generator Tool
# ----------------------------------
# Generates a stand-alone LALR(1) parser
#
# Git:    https://github.com/erezsh/lark
# Author: Erez Shinan (erezshin@gmail.com)
#
#
#    >>> LICENSE
#
#    This tool and its generated code use a separate license from Lark,
#    and are subject to the terms of the Mozilla Public License, v. 2.0.
#    If a copy of the MPL was not distributed with this
#    file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
#    If you wish to purchase a commercial license for this tool and its
#    generated code, you may contact me via email or otherwise.
#
#    If MPL2 is incompatible with your free or open-source project,
#    contact me and we'll work it out.
#
#

from copy import deepcopy
from abc import ABC, abstractmethod
from types import ModuleType
from typing import (
    TypeVar, Generic, Type, Tuple, List, Dict, Iterator, Collection, Callable, Optional, FrozenSet, Any,
    Union, Iterable, IO, TYPE_CHECKING, overload, Sequence,
    Pattern as REPattern, ClassVar, Set, Mapping
)
###}

import sys
import token, tokenize
import os
from os import path
from collections import defaultdict
from functools import partial
from argparse import ArgumentParser

import lark
from lark.tools import lalr_argparser, build_lalr, make_warnings_comments


from lark.grammar import Rule
from lark.lexer import TerminalDef

_dir = path.dirname(__file__)
_larkdir = path.join(_dir, path.pardir)


EXTRACT_STANDALONE_FILES = [
    'tools/standalone.py',
    'exceptions.py',
    'utils.py',
    'tree.py',
    'visitors.py',
    'grammar.py',
    'lexer.py',
    'common.py',
    'parse_tree_builder.py',
    'parsers/lalr_analysis.py',
    'parsers/lalr_parser_state.py',
    'parsers/lalr_parser.py',
    'parsers/lalr_interactive_parser.py',
    'parser_frontends.py',
    'lark.py',
    'indenter.py',
]

def extract_sections(lines):
    section = None
    text = []
    sections = defaultdict(list)
    for line in lines:
        clean_line = line.strip()
        if clean_line.startswith("###"):
            if clean_line[3] == "{":
                section = clean_line[4:].strip()
            elif clean_line[3] == "}":
                sections[section] += text
                section = None
                text = []
            else:
                raise ValueError(line)
        elif section:
            text.append(line)

    return {name: ''.join(text) for name, text in sections.items()}


def strip_docstrings(line_gen):
    """ Strip comments and docstrings from a file.
    Based on code from: https://stackoverflow.com/questions/1769332/script-to-remove-python-comments-docstrings
    """
    res = []

    prev_toktype = token.INDENT
    last_lineno = -1
    last_col = 0

    tokgen = tokenize.generate_tokens(line_gen)
    for toktype, ttext, (slineno, scol), (elineno, ecol), ltext in tokgen:
        if slineno > last_lineno:
            last_col = 0
        if scol > last_col:
            res.append(" " * (scol - last_col))
        if toktype == token.STRING and prev_toktype == token.INDENT:
            # Docstring
            res.append("#--")
        elif toktype == tokenize.COMMENT:
            # Comment
            res.append("##\n")
        else:
            res.append(ttext)
        prev_toktype = toktype
        last_col = ecol
        last_lineno = elineno

    return ''.join(res)


def gen_standalone(lark_inst, output=None, out=sys.stdout, compress=False):
    if output is None:
        output = partial(print, file=out)

    import pickle, zlib, base64
    def compressed_output(obj):
        s = pickle.dumps(obj, pickle.HIGHEST_PROTOCOL)
        c = zlib.compress(s)
        output(repr(base64.b64encode(c)))

    def output_decompress(name):
        output('%(name)s = pickle.loads(zlib.decompress(base64.b64decode(%(name)s)))' % locals())

    output('# The file was automatically generated by Lark v%s' % lark.__version__)
    output('__version__ = "%s"' % lark.__version__)
    output()

    for i, pyfile in enumerate(EXTRACT_STANDALONE_FILES):
        with open(os.path.join(_larkdir, pyfile)) as f:
            code = extract_sections(f)['standalone']
            if i:   # if not this file
                code = strip_docstrings(partial(next, iter(code.splitlines(True))))
            output(code)

    data, m = lark_inst.memo_serialize([TerminalDef, Rule])
    output('import pickle, zlib, base64')
    if compress:
        output('DATA = (')
        compressed_output(data)
        output(')')
        output_decompress('DATA')
        output('MEMO = (')
        compressed_output(m)
        output(')')
        output_decompress('MEMO')
    else:
        output('DATA = (')
        output(data)
        output(')')
        output('MEMO = (')
        output(m)
        output(')')


    output('Shift = 0')
    output('Reduce = 1')
    output("def Lark_StandAlone(**kwargs):")
    output("  return Lark._load_from_dict(DATA, MEMO, **kwargs)")




def main():
    make_warnings_comments()
    parser = ArgumentParser(prog="prog='python -m lark.tools.standalone'", description="Lark Stand-alone Generator Tool",
                            parents=[lalr_argparser], epilog='Look at the Lark documentation for more info on the options')
    parser.add_argument('-c', '--compress', action='store_true', default=0, help="Enable compression")
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    ns = parser.parse_args()

    lark_inst, out = build_lalr(ns)
    gen_standalone(lark_inst, out=out, compress=ns.compress)

    ns.out.close()
    ns.grammar_file.close()


if __name__ == '__main__':
    main()
