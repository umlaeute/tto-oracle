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

import OracleText as ot

import http.server
import socketserver
import json
from urllib.parse import parse_qs

PORT = 8000


def _dictget_typed(d, key, default):
    res=default
    try:
        res=d[key]
        if list != type(default):
            return default
    except KeyError:
        pass
    return res

class Handler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(s):
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.end_headers()
    def _write(self, s):
        self.wfile.write(bytes(s, 'UTF-8'))
    def do_GET(s):
        """Respond to a GET request."""
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.end_headers()
        s._write("<html><head><title>The Tech Oracle.</title></head>")
        s._write("<body><p>You should POST.</p>")
        s._write("</body></html>")
    def do_POST(self):
        try:
            length = self.headers['content-length']
            data = self.rfile.read(int(length))
        except Exception as e:
            print("POST-exception: %s" % (e))
            return
        try:
            d=self.parseQuery(data)
            def test_json(J):
                print("JSON   : %s" % (J))
                D=J['comments']
                print("data   : %s (%s)" % (D, type(D)))
            #test_json(d)
            self._process(d, self.respond_JSON)
        except TypeError as e:
            print("oops: %s" % (e))
    def getoracle(self, words):
        oracles=self.server.get('oracles')
        print("oracles: %s" % (oracles))
        if False:
            o=oracles[0]
        else:
            o=sorted(oracles, key=lambda x:x.similindex(words), reverse=True)[0]
        print("%s oracles choraclese %s" % (len(oracles), o.name))
        return o

    def _process(self, d, respondfun=None):
        # rooms: questions, comments, protests, answers
        inputtexts=[]
        for room in ['comments', 'protests', 'answers']:
            t=d.get(room, '')
            if type(t) == list:
                t=' '.join(t)
            print("text[%s]=%s (%s)" % (room, t, type(t)))
            inputtexts+=[t]
        inputtext=' '.join(inputtexts)
        print("input: %s" % (inputtext))
        d=ot.OracleText.postag_words(inputtext, dictionary={})
        #print("intag: %s" % (d))
        interesting=ot.INTERESTING_TAGS

        deltags=[]
        for tag in d:
            keep=False
            for t in interesting:
                if tag.startswith(t):
                    keep=True
            if not keep:
                deltags+=[tag]
        for tag in deltags:
            del d[tag]
        words=[]
        for tag in d:
            words+=d.get(tag, [])
        words=list(set(words))
        #print("input: %s" % (inputtext))
        #print("tagged: %s" % d)
        #print("words: %s" % (words))

        o=self.getoracle(words)

        t=o.speak(inputtext=inputtext, truncate=True)
        if t:
            if respondfun:
                respondfun(t)

    @staticmethod
    def parseQuery(data):
        d=data.decode()
        try:
            return json.loads(d)
        except ValueError:
            return parse_qs(d)

    def respond_JSON(self, data):
        if not data:
            return None
        j=json.dumps(data)

        self.send_response(200)
        self.send_header  ("Content-type", "application/json")
        self. end_headers ()
        self._write(j)


class Server(socketserver.TCPServer):
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        socketserver.TCPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
        self._userdata={}
    def set(self, key, value):
        self._userdata[key]=value;
    def get(self, key):
        return self._userdata.get(key, None)

if '__main__' ==  __name__:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=PORT, help='port that the HTTP-server listens on (default: %d)' % PORT)
    parser.add_argument('textfiles', nargs='+', help='one or more textfiles as oracle text corpus')
    args=parser.parse_args()
    oracles=[]
    for filename in args.textfiles:
        print("creating oracle using %s" % (filename))
        try:
            o=ot.OracleText(filename)
            print("created oracle %s" % (o))
            oracles+=[o]
        except FileNotFoundError:
            print("couldn't read %s" % filename)
    if not oracles:
        import sys
        sys.exit(1)
    hnd = Handler
    httpd = Server(("", args.port), hnd)
    httpd.set('oracles', oracles)
    hnd.cgi_directories = ["/"]
    print("serving at port", args.port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    except:
        pass
    print("shutting down")
    httpd.shutdown()

    #t=o.speak(inputtext="The artist is stupid!", truncate=True)
    #print(ot.array2text(t))
