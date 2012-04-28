#! /usr/bin/env python
#coding=utf-8
import cgi
import datetime
import logging
import tweepy
import weibo
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import images
from google.appengine.api import memcache
from google.appengine.ext.webapp import template
import json
import os
from gaesessions import get_current_session
from datamodel import *

_DEBUG=True

class PageTools:
    def render(self, template_name, template_values={}):
        directory = os.path.dirname(__file__)
        path = os.path.join(directory, os.path.join('templates', template_name))
        self.response.out.write(template.render(path, template_values, debug=_DEBUG))

class ListPage(webapp.RequestHandler,PageTools):
    def get(self):
        try:
            weibo_all_list=SinaWeiboOauth.all().fetch(50)
            twitter_all_list=TwitterOauth.all().fetch(50)
            self.render('twitterdumptoweibo_list.htm',{'weibo_users':weibo_all_list,'twitter_users':twitter_all_list})
        except Exception,e:
            self.response.out.write(e)

class ConnectUser(webapp.RequestHandler,PageTools):
    def get(self):
        pass

application = webapp.WSGIApplication([
    ('/conn/listall',ListPage),
], debug=_DEBUG)


def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
