#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright © 2015, IOhannes m zmölnig, forum::für::umläute

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this file.  If not, see <http://www.gnu.org/licenses/>.

import requests
import json

if '__main__' ==  __name__:
    URL='http://localhost:8000'
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url', type=str, default=URL, help='connection URL for oracle server (default: %s)' % URL)
    parser.add_argument('text', nargs='+', help='some text you want to enter')
    args=parser.parse_args()
    text=' '.join(args.text)
    payload={'text': text}
    r = requests.post(args.url, data=json.dumps(payload))
    print(r.text)

    #t=o.speak(inputtext="The artist is stupid!", nouns=["oracle", "situtation"], adjectives=["solid", "nice"], truncate=True)
    #print(ot.array2text(t))
