#! /usr/bin/env python
#coding=utf-8
import cgi
import datetime
import logging
import tweepy
import weibo_api
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
from global_data import *

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
        oauth_auth= tweepy.OAuthHandler(g_appkey['twitter']['key'], g_appkey['twitter']['secret'])
        oauth_auth.set_access_token(twitter_oauth.access_key,twitter_oauth.access_secret)
        return tweepy.API(oauth_auth)
    def getSinaClient(self,sina_oauth):
        client=weibo_api.APIClient(app_key=g_appkey['weibo']['key'],app_secret=g_appkey['weibo']['secret'])
        client.set_access_token(sina_oauth.access_token, sina_oauth.expires_in)
        return client
    def get(self):
        try:
            all_ac=AccountConnect.all().fetch(20)
            for ac in all_ac:
                sina_oauth=ac.SinaOauth;
                twitter_oauth=ac.TwitterOauth;
                sina_client=self.getSinaClient(sina_oauth)
                twitter_client=self.getTwitterClient(twitter_oauth)

                if str(ac.max_msg) == 0:
                    time_line=twitter_client.home_timeline()
                else:
                    time_line=twitter_client.home_timeline(since_id=ac.max_msg)

                for msg in time_line:
                    try:
                        sina_client.post.statuses__update(status=msg.text)
                    except Exception,e:
                        logging.error('wei bo fail:%s %s',str(e),msg.text)

                if len(time_line):
                    ac.max_msg=time_line[0].id_str
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
