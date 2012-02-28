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
from django.utils import simplejson

consumer_key = 'g3H8iTwBmFKK2pPphAHg'
consumer_secret = 'AbSm2dIUwKV1lVT6sz6VfDgqKdPC6BbmM784gVRGw'

class TwitterOauth(db.Model):
    screen_name=db.StringProperty()
    access_key = db.StringProperty()
    access_secret = db.StringProperty()
    
class TwitterPage(webapp.RequestHandler):
    def get(self):
        oauth_auth= tweepy.OAuthHandler(consumer_key, consumer_secret,self.request.url+'authorization')
        url=oauth_auth.get_authorization_url()
        token=oauth_auth.request_token
        memcache.set(token.key,token.secret,60*5)
        self.redirect(url)

class TwitterAuthorizationPage(webapp.RequestHandler):
    def get(self):
        oauth_auth= tweepy.OAuthHandler(consumer_key, consumer_secret)
        oauth_token=self.request.get('oauth_token');
        token=tweepy.oauth.OAuthToken(oauth_token,memcache.get(oauth_token))
        memcache.delete(oauth_token)
        oauth_auth.request_token=token
        oauth_auth.get_access_token(self.request.get('oauth_verifier'))
        
        self.api=tweepy.API(oauth_auth)
        meinfo=self.api.me()
        
        todata=TwitterOauth.gql('where screen_name=:name',name=meinfo.screen_name).get()
        if  todata is None:
            todata=TwitterOauth()
            todata.screen_name=meinfo.screen_name
        todata.access_key=oauth_auth.access_token.key;
        todata.access_secret=oauth_auth.access_token.secret;
        todata.save()
        
        self.response.out.write("I am %s"%meinfo.screen_name)
class TwitterAll(webapp.RequestHandler):
    def get(self):
        name=self.request.get('name');
        oauths=TwitterOauth.gql('where screen_name=:name',name=name)
        
        resarray=[]
        for oauth in oauths:
            resarray.append({'name':oauth.screen_name,'key':oauth.access_key,'secret':oauth.access_secret})
        simplejson.dump(resarray,self.response.out)
        
application = webapp.WSGIApplication([
    ('/twitter/authorization',TwitterAuthorizationPage),
    ('/twitter/all',TwitterAll),
    ('/twitter/',TwitterPage)
], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()