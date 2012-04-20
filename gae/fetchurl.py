import cgi
import datetime
import logging
import urllib2
import string
import re
from StringIO import StringIO
import gzip
import zlib
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from HTMLParser import HTMLParser
import html5lib
import itertools
import json

def FindSubNode(root, name):
    for one in root.childNodes:
        if one.type == 5:
            if one.name == name:
                 return one
    return None

settings = {
            'digi': 16,
            'add': 10,
            'plus': 7,
            'cha': 36,
            'center': {
                'lat': 34.957995,
                'lng': 107.050781,
                'isDef': True
            }
        }
def intToStr(Num, radix):
    _base = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    _res = ''
    while 1:
        _d = Num % radix
        _res += _base[_d]
        Num = Num / radix
        if Num == 0:
            return _res
def decodeDP_POI(C):
        I = -1;
        H = 0;
        B = "";
        J = len(C);
        G = C[J - 1];
        C = C[0: J - 1];
        J -= 1
        for E in range(0, J):
            D = string.atoi(C[E], settings['cha']) - settings['add'];
            if D >= settings['add']:
                D = D - settings['plus']
            B += intToStr (D, settings['cha'])
            if D > H:
                I = E;
                H = D
        A = string.atoi(B[0:I], settings['digi']);
        F = string.atoi(B[I + 1:], settings['digi']);
        L = float(A + F - string.atoi(G, 36)) / 2;
        K = float(F - L) / 100000;
        L = float(L) / 100000;
        return {
            'lat': K,
            'lng': L
        }
def ReadHttpBody(response):
    cl = response.info().getheader('Content-length');
    if cl == None:
        cl = 0;
    else:
        cl = string.atoi(cl);
    if cl == 0:
        content = response.read();
    else:
        content = response.read(cl);
    if response.info().get('Content-Encoding') == 'gzip':
        buf = StringIO(content)
        f = gzip.GzipFile(fileobj=buf)
        content = f.read()
    elif response.info().get('Content-Encoding') == 'deflate':
        content = zlib.decompress(content)
    return content

class FetchPage (webapp.RequestHandler):
    def get(self):
        url = self.request.get("url")
        try:
            request = urllib2.Request(url)
            request.add_header('Accept-encoding', 'gzip')
            request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.162 Safari/535.19')
            response = urllib2.urlopen(request)
            content = ReadHttpBody(response)
        except urllib2.URLError, e:
            self.response.out.write(e)
            return
            
        ct_str = response.info().get('Content-Type')
        if ct_str != None:
            re_res = re.search(';\s*charset\s*=\s*([\w\d-]+)', ct_str, re.IGNORECASE)
            if re_res != None:
                encode = re_res.group(1)
            else:
                encode = None
      
        parser = html5lib.HTMLParser()
        domtree = parser.parse(content, encoding=encode)
        
        html_root = FindSubNode(domtree, 'html')
        html_body = FindSubNode(html_root, 'body')
        for one in html_body.childNodes:
            if one.type == 5:
                if one.name == 'script':
                    for second in one.childNodes:
                        if second.type == 4:
                            re_res = re.search('^\s*var\s+page\s*=', second.value, re.IGNORECASE)
                            if re_res != None:
                                start = second.value.find('{')
                                end = second.value.find('}')
                                #jobject=json.load(StringIO(second.value[start:end+1]))
                                all_word = second.value[start + 1:end].split(',')
                                all_list = {}
                                for pair in all_word:
                                    kvl = pair.split(':')
                                    if len(kvl) < 2:
                                        continue
                                    all_list[kvl[0].strip()] = kvl[1].strip(' \r\n"')
                                msg_list_tmp = re.split('<.*?>', all_list['msg'])
                                msg_list = []
                                for spltmsg in msg_list_tmp:
                                    spltmsg2 = spltmsg.strip()
                                    if len(spltmsg2) > 0:
                                        msg_list.append(spltmsg2)
                                oneShop = {
                                         'pos':decodeDP_POI(all_list['p']),
                                         'shopId':all_list['shopId']
                                         }
                                if len(msg_list) > 0:
                                    oneShop['shopName'] = msg_list[0]
                                if len(msg_list) > 1:
                                    oneShop['address'] = msg_list[1]
                                self.response.out.write(str(oneShop))

application = webapp.WSGIApplication([
    ('/fetch/fetch', FetchPage),
], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()
