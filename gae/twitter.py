import cgi
import datetime
import logging
import tweepy

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
consumer_key = 'g3H8iTwBmFKK2pPphAHg'
consumer_secret = 'AbSm2dIUwKV1lVT6sz6VfDgqKdPC6BbmM784gVRGw'

class TwitterPage(webapp.RequestHandler):
    def get(self):
        try:
            session=get_current_session()
            """if session!=None:
                if session.has_key('twitter_access_key') and session.has_key('twitter_access_secret'):
                    self.redirect('./timeline')
                    return"""
            oauth_auth= tweepy.OAuthHandler(consumer_key, consumer_secret,self.request.url+'authorization')
            url=oauth_auth.get_authorization_url()
            token=oauth_auth.request_token
            session['oauth_token']=token.key
            session['oauth_secret']=token.secret
            self.redirect(url)
        except Exception,e:
            self.response.out.write(e)

class TwitterAuthorizationPage(webapp.RequestHandler):
    def get(self):
        try:
            session=get_current_session()
            oauth_auth= tweepy.OAuthHandler(consumer_key, consumer_secret)
            oauth_token=self.request.get('oauth_token');
            token=tweepy.oauth.OAuthToken(oauth_token,session['oauth_secret'])
            del session['oauth_token']
            del session['oauth_secret']
            oauth_auth.request_token=token
            oauth_auth.get_access_token(self.request.get('oauth_verifier'))

            session['twitter_access_key']=oauth_auth.access_token.key
            session['twitter_access_secret']=oauth_auth.access_token.secret
            self.api=tweepy.API(oauth_auth)
            meinfo=self.api.me()

            todata=TwitterOauth.gql('where user_id=:id',id=meinfo.id).get()
            if  todata is None:
                todata=TwitterOauth()
                todata.user_id=meinfo.id
                todata.screen_name=meinfo.screen_name
            todata.access_key=oauth_auth.access_token.key;
            todata.access_secret=oauth_auth.access_token.secret;
            todata.save()

            self.response.out.write("I am %s"%meinfo.screen_name)
        except Exception,e:
            self.response.out.write(e)
class TwitterAll(webapp.RequestHandler):
    def get(self):
        name=self.request.get('name');
        oauths=TwitterOauth.gql('where screen_name=:name',name=name)

        resarray=[]
        for oauth in oauths:
            resarray.append({'name':oauth.screen_name,'key':oauth.access_key,'secret':oauth.access_secret})
        json.dump(resarray,self.response.out)

class PageTools:
    def getTwitterClient(self):
        session=get_current_session()
        oauth_auth= tweepy.OAuthHandler(consumer_key, consumer_secret)
        oauth_auth.set_access_token(session['twitter_access_key'],session['twitter_access_secret'])
        return tweepy.API(oauth_auth)
    def render(self, template_name, template_values={}):
        directory = os.path.dirname(__file__)
        path = os.path.join(directory, os.path.join('templates', template_name))
        self.response.out.write(template.render(path, template_values, debug=_DEBUG))

class TwitterTimeLine(webapp.RequestHandler,PageTools):
    def get(self):
        try:
            api=self.getTwitterClient()
            meinfo=api.me()
            time_line=api.home_timeline()
            self.render('twittertimeline.htm',{'me':meinfo,'timeline':time_line})
        except Exception,e:
            self.response.out.write(e)

application = webapp.WSGIApplication([
    ('/tr/authorization',TwitterAuthorizationPage),
    ('/tr/all',TwitterAll),
    ('/tr/timeline',TwitterTimeLine),
    ('/tr/',TwitterPage)
], debug=_DEBUG)


def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()