#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The analyser is the central point of the yoda project. It analyses the given script and store the results in a mongodb
collection. Configuration of the mongodb is done in the settings.py file.
.. todo:: Use a better way to store settings in order to let the user change things
`todo`

This script can't be run directly and must be imported your own script in order to analyse it. Be sure to
add the ``set_trace()`` function at the beginning and ``set_quit()`` and the end of the section of code you want to
analyse.

:Example:

import yoda.analyser

yoda.analyser.db.set_trace()

a = 1
b = 3

for c in range(10):
    d = c
    print(c)
yoda.analyser.db.set_quit()
"""

import bdb
from collections import defaultdict
from datetime import datetime
import subprocess
import sys
import timeit
import copy

from mongoengine import *

import yoda.settings as settings
from yoda.docdef import *


class Yoda(bdb.Bdb):
    run = 0
    json_results = None
    instrumented_types = (int, float, str, list, dict)
    #instrumented_types = (dict, bytes, bool, float, int, list, object, str, tuple)
    prev_lineno = defaultdict(int)
    prev_lineno['<module>'] = 0
    cur_framename = '<module>'

    def __init__(self):
        bdb.Bdb.__init__(self)
        if not settings.DEBUG: # If DEBUG is to FALSE connect to mongodb
            connect(settings.MONGODB)
        self._clear_cache()

    def _clear_cache(self):
        self.json_results = defaultdict(lambda: defaultdict(defaultdict))

    def _filter_locals(self, local_vars):
        print("FILTER LOCALS")
        new_locals = {}
        for name, value in list(local_vars.items()):
            if name.startswith('__'):
                continue
            if not isinstance(value, self.instrumented_types):
                continue
            if type(value) == str:
                new_locals[name] = [copy.deepcopy(value)]
            else:
                new_locals[name] = copy.deepcopy(value)

            print(new_locals)

        return new_locals

    def _get_git_revision_short_hash(self):
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'])

    def _get_git_username(self):
        return subprocess.check_output(['git', 'config', 'user.name'])

    def user_call(self, frame, args):
        print("CALL EVENT")
        self.cur_framename = str(frame.f_code.co_name)
        self.prev_lineno[self.cur_framename] = frame.f_lineno

        self.set_step() # continue

    def user_line(self, frame):
        print("---------------------------------------------------------------------------------------------------------------------------------------------------------")
        print("LINE EVENT")
        print("Premier", self.json_results)
        cur_lineno = frame.f_lineno
        lineno = self.prev_lineno[self.cur_framename]

        locals = self._filter_locals(frame.f_locals)
        filename = frame.f_globals['__file__']

        if locals:
            if not self.json_results[filename][self.cur_framename].get(lineno):
                #print(locals)
                #print(lineno)
                self.json_results[filename][self.cur_framename][lineno] = locals
                print("Deuxième",self.json_results)
                print("stored")
            else:
                print("pasla")
                for k,v in locals.items():
                    if not self.json_results[filename][self.cur_framename][lineno].get(k):
                        self.json_results[filename][self.cur_framename][lineno][k] = v
                    else:
                        self.json_results[filename][self.cur_framename][lineno][k].append(v[0])

        self.prev_lineno[self.cur_framename] = cur_lineno

        self.set_step()
        print("Troisième",self.json_results)

    def user_return(self, frame, value):
        print("RETURN EVENT")
        self.cur_framename = '<module>'
        self.set_step()  # continue

    def user_exception(self, frame, exception):
        print("EXCEPTION EVENT")
        name = frame.f_code.co_name or "<unknown>"
        print("exception in", name, exception)
        self.set_continue()  # continue

    def set_quit(self):
        self.stopframe = self.botframe
        self.returnframe = None
        self.quitting = True
        sys.settrace(None)

        if self.json_results:
            print(self.json_results)

            if settings.DEBUG:
                print(self.json_results)
            else:
                for module_file, frames in self.json_results.items():
                    if 'analyser.py' not in module_file:
                        file = open(module_file, 'r')
                        file_content = file.read()
                        file.close()

                        if file_content:
                            item = File(user=self._get_git_username(), revision=self._get_git_revision_short_hash(), filename=module_file, timestamp=datetime.now(), content=file_content)
                            for name, lines in sorted(frames.items()):
                                frame = Frame(name=name)
                                for lineno, data in sorted(lines.items()):
                                    line = Line(lineno = lineno, data = data)
                                    frame.lines.append(line)

                                item.frames.append(frame)

                            item.save()
                self._clear_cache()
        print(timeit.timeit('"-".join(str(n) for n in range(100))', number=10000))



db = Yoda()
