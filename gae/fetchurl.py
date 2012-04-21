# coding=utf-8
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
from google.appengine.api import taskqueue
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from HTMLParser import HTMLParser
import html5lib
import itertools
import json

class DianPinShopData(db.Model):
    shopId=db.IntegerProperty()
    address=db.StringProperty()
    pos = db.GeoPtProperty()
    shopName = db.StringProperty()

def FindSubNode(root, name):
    for one in root.childNodes:
        if one.type == 5:
            if one.name == name:
                 return one
    return None
def SearchSubNodes(root,name,returnlist):
    for one in root.childNodes:
        if one.type == 5:
            if one.name == name:
                 returnlist.append(one)
        SearchSubNodes(one,name,returnlist)

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
def getUrlDomTree(url):
    request = urllib2.Request(url)
    request.add_header('Accept-encoding', 'gzip')
    request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.162 Safari/535.19')
    response = urllib2.urlopen(request)
    content = ReadHttpBody(response)
    
    ct_str = response.info().get('Content-Type')
    if ct_str != None:
        re_res = re.search(';\s*charset\s*=\s*([\w\d-]+)', ct_str, re.IGNORECASE)
        if re_res != None:
            encode = re_res.group(1)
        else:
            encode = None
  
    parser = html5lib.HTMLParser()
    return parser.parse(content, encoding=encode)
    
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

class FetchMapPage (webapp.RequestHandler):
    def get(self):
        url = 'http://www.dianping.com/shop/%s/map'%(self.request.get('id'))
        try:
            domtree=getUrlDomTree(url)
        except Exception, e:
            self.response.out.write(e)
            return
        
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
                                         'shopId':string.atoi(all_list['shopId'])
                                         }
                                if len(msg_list) > 0:
                                    oneShop['shopName'] = msg_list[0]
                                if len(msg_list) > 1:
                                    oneShop['address'] = msg_list[1]
                                    
                                dianpindata=DianPinShopData.gql('where shopId=:shopId',shopId=oneShop['shopId']).get()
                                if dianpindata==None:
                                    dianpindata=DianPinShopData()
                                    dianpindata.shopId=oneShop['shopId']
                                dianpindata.pos=db.GeoPt(oneShop['pos']['lat'],oneShop['pos']['lng'])
                                dianpindata.address=oneShop['address']
                                dianpindata.shopName=oneShop['shopName']
                                dianpindata.put()
                                self.response.out.write(str(oneShop))

class FetchCategoryPage (webapp.RequestHandler):
    def get(self):
        url='http://www.dianping.com/search/category/%s/0/r%sp%s'%\
            (self.request.get('a'),self.request.get('r'),self.request.get('p'))
        try:
            domtree=getUrlDomTree(url)
        except Exception, e:
            self.response.out.write(e)
            return
        
        searchList=None
        for node in iter(domtree):
            if node.type==5 and node.name=='div' :
                idstr=node.attributes.get('id')
                if   idstr !=None and idstr.lower()=='searchlist':
                    searchList=node
                    break
        if searchList==None:
            return
        searchdl=FindSubNode(searchList,'dl')
        shopid_list=[]
        for node in searchdl.childNodes:
            if node.type==5 and node.name=='dd':
                pnode=None
                for subnode in node.childNodes:
                    if subnode.type==5 and subnode.name=='p':
                        pnode=subnode
                        break
                if pnode!=None:
                    for anode in iter(pnode):
                        
                        if anode.type==5 and anode.name=='a':
                            hrefmap=anode.attributes.get('href')
                            if hrefmap!=None:
                                re_res=re.search('/shop/(\d+?)/map',hrefmap,re.IGNORECASE)
                                if re_res!=None:
                                    find_shopNum=re_res.group(1)
                                    shopid_list.append(string.atoi(find_shopNum))
                                    break
        for sid in shopid_list:
            fetchtask=taskqueue.Task(url='/fetch/fetchmap?id=%d'%sid,method='GET')
            fetchtask.add('copydianpin')
        self.response.out.write(str(shopid_list))
        
class FetchShopAllPage (webapp.RequestHandler):
    def get(self):
        url='http://www.dianping.com/shopall/%s/0'%(self.request.get('a'))
        try:
           domtree=getUrlDomTree(url)
        except Exception, e:
           self.response.out.write(e)
           return
        
        try:
            for node in iter(domtree):
               if node.type==5 and node.name=='a':
                   if node.attributes.get('name')=='BDBlock':
                       frelist=node.parent.parent
                       prenode=node.parent
                       break
            for i in range(len(frelist.childNodes)):
                if frelist.childNodes[i]==prenode:
                    checknode=frelist.childNodes[i+1]
                    break
        except Exception, e:
           self.response.out.write(e)
           return
        link_list=[]
        for node in checknode.childNodes:
            if node.type==5 and node.name=="dl":
                linkNode=SearchSubNodes(node,'a',link_list)
        categorylist=[]     
        for linkNode in link_list:
            hrefstr=linkNode.attributes.get('href')
            if hrefstr!=None:
                re_res=re.search('/search/category/(\d+)/0/r(\d+)',hrefstr,re.IGNORECASE)
                if re_res!=None:
                    cell={'a':string.atoi(re_res.group(1)),'r':string.atoi(re_res.group(2))}
                    categorylist.append(cell)
        self.response.out.write(str(categorylist))
         
application = webapp.WSGIApplication([
    ('/fetch/fetchmap', FetchMapPage),
    ('/fetch/fetchcategory', FetchCategoryPage),
    ('/fetch/fetchallpage',FetchShopAllPage),
], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()
