#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys

def main():
    while 1:
        l = sys.stdin.readline().split()
        try:
            user = l[0]
            url = l[1]
        except IndexError:
            continue
        sys.stderr.write('Got request' + ' '.join(l))

        sys.stdout.write('OK\n')
        sys.stdout.flush()

if __name__ == '__main__':
    sys.exit(main())
