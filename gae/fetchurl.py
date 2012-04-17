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
            encode=get_html_Encode(content)
            self.response.out.write(content.decode(encode,'ignore'));
        except urllib2.URLError, e:
            self.response.out.write(e)

application = webapp.WSGIApplication([
    ('/fetch/fetch', FetchPage),
], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()