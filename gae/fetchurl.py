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

def get_html_Encode(content):
    if len(content)>500:
        s = content[0:500]
    else:
        s = content;
    m_charset = re.search('<meta\s*http-equiv="?Content-Type"? content="text/html;\s*charset=([\w\d-]+?)"', s.decode("ISO-8859-1"), re.IGNORECASE)
    return m_charset.group(1)

class FetchPage (webapp.RequestHandler):
    def get(self):
        url = self.request.get("url")
        try:
            request = urllib2.Request(url)
            request.add_header('Accept-encoding', 'gzip')
            response = urllib2.urlopen(request)
            cl=response.info().getheader('Content-length');
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
            if encode==None:
                encode=get_html_Encode(content)
            if encode!=None:
                content=content.decode(encode,'ignore');
            self.response.out.write(content);
        except urllib2.URLError, e:
            self.response.out.write(e)

application = webapp.WSGIApplication([
    ('/fetch/fetch', FetchPage),
], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()