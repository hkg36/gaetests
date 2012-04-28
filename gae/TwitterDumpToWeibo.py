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
        sina_user=self.request.get('sina')
        tr_user=self.request.get('tr')
        if len(sina_user)==0 or len(tr_user )==0:
            self.response.out.write('param error')
            return
        sina_oauth=SinaWeiboOauth.gql('where screen_name=:name',name=sina_user).get()
        twitter_oauth=TwitterOauth.gql('where screen_name=:name',name=tr_user).get()
        if sina_oauth==None and twitter_oauth==None:
            self.response.out.write('user not exists')
        ac=AccountConnect.gql('where SinaOauth=:so and TwitterOauth=:to',so=sina_oauth,to=twitter_oauth).get()
        if ac==None:
            ac=AccountConnect()
            ac.SinaOauth=sina_oauth;
            ac.TwitterOauth=twitter_oauth;
            ac.put()
        self.response.out.write('done')
        pass
class TransMessage(webapp.RequestHandler,PageTools):
    def getTwitterClient(self,twitter_oauth):
        consumer_key = 'g3H8iTwBmFKK2pPphAHg'
        consumer_secret = 'AbSm2dIUwKV1lVT6sz6VfDgqKdPC6BbmM784gVRGw'
        oauth_auth= tweepy.OAuthHandler(consumer_key, consumer_secret)
        oauth_auth.set_access_token(twitter_oauth.access_key,twitter_oauth.access_secret)
        return tweepy.API(oauth_auth)
    def getSinaClient(self,sina_oauth):
        APP_KEY = '685427335'
        APP_SECRET = '1d735fa8f18fa94d87cd9196867edfb6'
        token=weibo.OAuthToken(sina_oauth.access_key,sina_oauth.access_secret)
        client=weibo.APIClient(app_key=APP_KEY,app_secret=APP_SECRET,token=token)
        return client
    def get(self):
        try:
            all_ac=AccountConnect.all().fetch(20)
            for ac in all_ac:
                sina_oauth=ac.SinaOauth;
                twitter_oauth=ac.TwitterOauth;
                sina_client=self.getSinaClient(sina_oauth)
                twitter_client=self.getTwitterClient(twitter_oauth)

                if ac.max_msg is None:
                    time_line=twitter_client.home_timeline()
                else:
                    time_line=twitter_client.home_timeline(since_id=ac.max_msg)

                max_msg_id=0
                for msg in time_line:

                    try:
                        sina_client.post.statuses__update(status=msg.text)
                        if msg.id>max_msg_id:
                            max_msg_id=msg.id
                    except Exception,e:
                        self.response.out.write('wei bo fail:%s<br />'%e)

                if max_msg_id>0 and max_msg_id>ac.max_msg:
                    ac.max_msg=max_msg_id
                    ac.put()
        except Exception,e:
            self.response.out.write(e)

application = webapp.WSGIApplication([
    ('/conn/listall',ListPage),
    ('/conn/conn',ConnectUser),
    ('/conn/trans',TransMessage)
], debug=_DEBUG)


def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()