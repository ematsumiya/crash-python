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
from crash.types.list import list_for_each_entry
from crash.subsystem.filesystem import for_each_super_block, get_super_block
from crash.subsystem.filesystem.xfs import xfs_mount
from crash.subsystem.filesystem.xfs import xfs_for_each_ail_log_item
from crash.subsystem.filesystem.xfs import xfs_log_item_typed
from crash.subsystem.filesystem.xfs import xfs_format_xfsbuf
from crash.subsystem.filesystem.xfs import XFS_LI_TYPES
from crash.subsystem.filesystem.xfs import XFS_LI_EFI, XFS_LI_EFD
from crash.subsystem.filesystem.xfs import XFS_LI_IUNLINK, XFS_LI_INODE
from crash.subsystem.filesystem.xfs import XFS_LI_BUF, XFS_LI_DQUOT
from crash.subsystem.filesystem.xfs import XFS_LI_QUOTAOFF, XFS_BLI_FLAGS

if sys.version_info.major >= 3:
    long = int

class XFSCommand(CrashCommand):
    """display XFS internal data structures

NAME
  xfs - display XFS internal data structures

SYNOPSIS
  xfs <command> [arguments ...]

COMMANDS
  xfs list
  xfs dump-ail <superblock>
  xfs dump-buft <buftarg>
  """

    __types__ = [ 'uuid_t', 'struct xfs_buf *' ]

    def __init__(self, name):
        parser = CrashCommandParser(prog=name)
        subparsers = parser.add_subparsers(help="sub-command help")
        list_parser = subparsers.add_parser('list', help='listail help')
        list_parser.set_defaults(subcommand=self.list_xfs)
        ail_parser = subparsers.add_parser('dump-ail', help='ail help')
        ail_parser.set_defaults(subcommand=self.dump_ail)
        ail_parser.add_argument('addr')
        buft_parser = subparsers.add_parser('dump-buft', help='buft help')
        buft_parser.set_defaults(subcommand=self.dump_buftargs)
        buft_parser.add_argument('addr')

        parser.format_usage = lambda: 'xfs <subcommand> [args...]\n'
        CrashCommand.__init__(self, name, parser)

    def list_xfs(self, args):
        for sb in for_each_super_block():
            if sb['s_type']['name'].string() == "xfs":
                mp = xfs_mount(sb)
                u = long(0)
                if 'b' in self.uuid_t_type:
                    member = 'b'
                else:
                    member = '__u_bits'
                for i in range(0, 16):
                    u <<= 8
                    u += long(mp['m_sb']['sb_uuid'][member][i])
                u = uuid.UUID(int=u)
                print("{} -> {} {}".format(sb.address, sb['s_id'].string(), u))

    def dump_ail(self, args):
        sb = get_super_block(args.addr)
        mp = xfs_mount(sb)
        ail = mp['m_ail']
        itemno = 0
        print("AIL @ {:x}".format(long(ail)))
        print("target={} last_pushed_lsn={} log_flush="
              .format(long(ail['xa_target']), long(ail['xa_last_pushed_lsn'])),
                      end='')
        try:
            print("{}".format(long(['xa_log_flush'])))
        except:
            print("[N/A]")

        for bitem in xfs_for_each_ail_log_item(mp):
            li_type = long(bitem['li_type'])
            lsn = long(bitem['li_lsn'])
            item = xfs_log_item_typed(bitem)
            print("{}: item={:x} lsn={} {} "
                  .format(itemno, long(bitem.address), lsn,
                          XFS_LI_TYPES[li_type][7:]), end='')
            if li_type == XFS_LI_BUF:
                buf = item['bli_buf']
                flags = []
                bli_flags = long(item['bli_flags'])

                for flag in XFS_BLI_FLAGS.keys():
                    if flag & bli_flags:
                        flags.append(XFS_BLI_FLAGS[flag])

                print(" buf@{:x} bli_flags={}"
                      .format(long(buf), "|".join(flags)))

                print("     {}".format(xfs_format_xfsbuf(buf)))
            elif li_type == XFS_LI_INODE:
                xfs_inode = item['ili_inode']
                print("inode@{:x} i_ino={}"
                      .format(long(xfs_inode['i_vnode'].address),
                              long(xfs_inode['i_ino'])))
            elif li_type == XFS_LI_EFI:
                efi = item['efi_format']
                print("efi@{:x} size={}, nextents={}, id={:x}"
                      .format(long(item.address), long(efi['efi_size']),
                              long(efi['efi_nextents']), long(efi['efi_id'])))
            elif li_type == XFS_LI_EFI:
                efd = item['efd_format']
                print("efd@{:x} size={}, nextents={}, id={:x}"
                      .format(long(item.address), long(efd['efd_size']),
                              long(efd['efd_nextents']), long(efd['efd_id'])))
            elif li_type == XFS_LI_DQUOT:
                dquot = item['qli_dquot']
                print("dquot@{:x}".format(long(dquot), long(dquot['dq_flags'])))
            elif li_type == XFS_LI_QUOTAOFF:
                qoff = item['qql_format']
                print("qoff@{:x} type={} size={} flags={}"
                      .format(long(qoff), long(qoff['qf_type']),
                              long(qoff['qf_size']), long(qoff['qf_flags'])))
            else:
                print("item@{:x}".format(long(item.address)))
            itemno += 1

    @classmethod
    def dump_buftarg(cls, targ):
        for buf in list_for_each_entry(targ['bt_delwrite_queue'],
            cls.xfs_buf_p_type.target(), 'b_list'):
            print("{:x} {}".format(long(buf.address), xfs_format_xfsbuf(buf)))

    @classmethod
    def dump_buftargs(cls, args):
        sb = get_super_block(args.addr)
        mp = xfs_mount(sb)
        ddev = mp['m_ddev_targp']
        ldev = mp['m_logdev_targp']

        print("Data device queue @ {:x}:".format(long(ddev)))
        cls.dump_buftarg(ddev)

        if long(ddev) != long(ldev):
            print("Log device queue:")
            cls.dump_buftarg(ldev)

    def execute(self, args):
        args.subcommand(args)

XFSCommand("xfs")
