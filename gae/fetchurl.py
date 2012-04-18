import cgi
import datetime
import logging
import urllib2
import string
import re
from StringIO import StringIO
import gzip
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from HTMLParser import HTMLParser
import html5lib
import itertools

class MyHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.page_encode=None
        self.links=[]
 
    def handle_starttag(self, tag, attrs):
        #print "Encountered the beginning of a %s tag" % tag
        attrdic={}
        if len(attrs)>0:
            for (variable, value)  in attrs:
                attrdic[variable]=value
        if tag=='meta':
          if attrdic.get('http-equiv')=='Content-Type':
              encode_str=attrdic.get('content')
              if self.page_encode==None and encode_str!=None:
                  re_res=re.search(';\s*charset\s*=\s*([\w\d-]+)',encode_str,re.IGNORECASE)
                  if re_res!=None:
                      self.page_encode=re_res.group(1)
        elif tag == "a":
            url=attrdic.get('href')
            if url!=None:
                self.links.append(url)
    def handle_data(self, data):
        if self.page_encode==None:
            decode_code='UTF-8'
        else:
            decode_code=self.page_encode;
        self.links.append(data.decode(decode_code,'ignore'))
                        
class FetchPage (webapp.RequestHandler):
    def get(self):
        url = self.request.get("url")
        try:
            request = urllib2.Request(url)
            request.add_header('Accept-encoding', 'gzip')
            response = urllib2.urlopen(request)
            cl=response.info().getheader('Content-length');
            if cl==None:
                cl=0;
            else:
                cl=string.atoi(cl);
            if cl==0:
                content=response.read();
            else:
                content=response.read(cl);
            if response.info().get('Content-Encoding') == 'gzip':
                buf = StringIO(content)
                f = gzip.GzipFile(fileobj=buf)
                content = f.read()
            
            ct_str=response.info().get('Content-Type')
            if ct_str!=None:
                re_res=re.search(';\s*charset\s*=\s*([\w\d-]+)',ct_str,re.IGNORECASE)
                if re_res!=None:
                    encode=re_res.group(1)
                else:
                    encode=None
          
            """
            parser=MyHTMLParser()
            if encode!=None:
                parser.page_encode=encode
            parser.feed(content)
            parser.close()
            self.response.out.write('<br />'.join(parser.links));"""
            parser = html5lib.HTMLParser()
            domtree=parser.parse(content,encoding=encode)
            self.response.out.write(domtree.printTree())
        except urllib2.URLError, e:
            self.response.out.write(e)

application = webapp.WSGIApplication([
    ('/fetch/fetch', FetchPage),
], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()