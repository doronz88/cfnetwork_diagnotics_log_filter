#!/usr/local/bin/python3
import logging
import posixpath

import click
import coloredlogs
from pygments import highlight
from pygments.formatters import TerminalTrueColorFormatter
from pygments.lexers import HttpLexer
from pymobiledevice3.lockdown import LockdownClient
from pymobiledevice3.services.os_trace import OsTraceService

coloredlogs.install(level=logging.DEBUG)


def parse_fields(message: str):
    result = {}

    for line in message.split('\n'):
        if ': ' not in line:
            continue

        line = line.strip()
        k, v = line.split(':', 1)
        k = k.strip()
        v = v.strip()
        result[k] = v

    return result


@click.command()
@click.option('pids', '-p', '--pid', multiple=True, help='filter pid list')
@click.option('process_names', '-pn', '--process-name', multiple=True, help='filter process name list')
@click.option('--color/--no-color', default=True)
@click.option('--request/--no-request', is_flag=True, default=True, help='show requests')
@click.option('--response/--no-response', is_flag=True, default=True, help='show responses')
def main(pids, process_names, color, request, response):
    lockdown = LockdownClient()

    for entry in OsTraceService(lockdown).syslog():
        if entry.label is None or entry.label.subsystem != 'com.apple.CFNetwork' or \
                entry.label.category != 'Diagnostics':
            continue

        if pids and (entry.pid not in pids):
            continue

        if process_names and (posixpath.basename(entry.filename) not in process_names):
            continue

        lines = entry.message.split('\n')
        if len(lines) < 2:
            continue

        buf = ''

        if lines[1].strip().startswith('Protocol Enqueue: request') and request:
            # request
            print('➡️   ', end='')
            fields = parse_fields(entry.message)
            buf += f'{fields["Message"]}\n'
            for name, value in fields.items():
                if name in ('Protocol Enqueue', 'Request', 'Message'):
                    continue
                buf += f'{name}: {value}\n'

        elif lines[1].strip().startswith('Protocol Received: request') and response:
            # response
            print('⬅️   ', end='')
            fields = parse_fields(entry.message)
            buf += f'{fields["Response"]} ({fields["Protocol Received"]})\n'
            for name, value in fields.items():
                if name in ('Protocol Received', 'Response'):
                    continue
                buf += f'{name}: {value}\n'

        if buf:
            if color:
                print(highlight(buf, HttpLexer(), TerminalTrueColorFormatter(style='autumn')))
            else:
                print(buf)


if __name__ == '__main__':
    main()
