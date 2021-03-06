# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import unittest
import gdb
import sys
if sys.version_info.major >= 3:
    from io import StringIO
else:
    from cStringIO import StringIO

from crash.exceptions import MissingSymbolError
from crash.commands import CrashCommandLineError
from crash.commands.syscmd import SysCommand

class TestSysCmd(unittest.TestCase):
    def setUp(self):
        gdb.execute("file tests/test-syscache", to_string=True)
        self.cmd = SysCommand("pysys")

    def test_sys(self):
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        self.cmd.invoke_uncaught("", from_tty=False)
        result = sys.stdout.getvalue()
        sys.stdout = old_stdout
        self.assertTrue('UPTIME: 0:02:34' in result)
        self.assertTrue('NODENAME: linux' in result)
        self.assertTrue('RELEASE: 4.4.21-default' in result)
        self.assertTrue('VERSION: #7 SMP Wed Nov 2 16:08:46 EDT 2016' in result)
        self.assertTrue('MACHINE: x86_64' in result)

    def test_sys_garbage(self):
        with self.assertRaises(CrashCommandLineError):
            self.cmd.invoke_uncaught("garbage", from_tty=False)

    def test_sys_garbage_flag(self):
        with self.assertRaises(CrashCommandLineError):
            self.cmd.invoke_uncaught("-a", from_tty=False)

    def test_sys_config(self):
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        self.cmd.invoke_uncaught("config", from_tty=False)
        result = sys.stdout.getvalue()
        sys.stdout = old_stdout

        self.assertTrue('CONFIG_HZ=' in result)
        self.assertTrue('CONFIG_MODULES=' in result)
