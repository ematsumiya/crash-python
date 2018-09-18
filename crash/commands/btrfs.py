# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
import sys
import os.path
import argparse
import re
import uuid

from crash.commands import CrashCommand, CrashCommandParser
from crash.exceptions import DelayedAttributeError
from crash.subsystem.filesystem import for_each_super_block
from crash.subsystem.filesystem.btrfs import btrfs_fs_info

if sys.version_info.major >= 3:
    long = int

class BtrfsCommand(CrashCommand):
    """display Btrfs internal data structures

NAME
  btrfs - display Btrfs internal data structures

SYNOPSIS
  btrfs <command> <superblock>

COMMANDS
  btrfs list - list all btrfs file systems"""
    __types__ = [ 'struct btrfs_fs_info' ]

    def __init__(self, name):
        parser = CrashCommandParser(prog=name)
        subparsers = parser.add_subparsers(help="sub-command help")
        ail_parser = subparsers.add_parser('list', help='list help')
        ail_parser.set_defaults(subcommand=self.list_btrfs)

        parser.format_usage = lambda: 'btrfs <subcommand> [args...]\n'
        CrashCommand.__init__(self, name, parser)

    def list_btrfs(self, args):
        for sb in for_each_super_block():
            if sb['s_type']['name'].string() == "btrfs":
                fs_info = btrfs_fs_info(sb)
                u = long(0)
                for i in range(0, 16):
                    u <<= 8
                    u += long(fs_info['fsid'][i])
                u = uuid.UUID(int=u)
                print("{} -> {} {}".format(sb.address, sb['s_id'].string(), u))

    def execute(self, args):
        try:
            args.subcommand(args)
        except Exception as e:
            raise gdb.GdbError(str(e))

BtrfsCommand("btrfs")
