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
import string
from gaesessions import get_current_session
from datamodel import *
import re

_DEBUG=True
APP_KEY = '685427335'
APP_SECRET = '1d735fa8f18fa94d87cd9196867edfb6'
CALLBACK_URL='http://www.hkg36.tk/weibo/authorization'

class RootPage(webapp.RequestHandler):
    def get(self):
        try:
            session=get_current_session()
            """if session!=None:
                if session.has_key('weibo_access_key') and session.has_key('weibo_access_secret'):
                    self.redirect('./timeline')
                    return"""
            session['callbackurl']=CALLBACK_URL
            client = weibo_api.APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=CALLBACK_URL)
            url = client.get_authorize_url()
            self.redirect(url)
        except Exception,e:
            self.response.out.write(e)

class AuthorizationPage(webapp.RequestHandler):
    def get(self):
        session=get_current_session()
        code=self.request.get('code')
        client = weibo_api.APIClient(app_key=APP_KEY, app_secret=APP_SECRET,redirect_uri=CALLBACK_URL)
        r = client.request_access_token(code)
        client.set_access_token(r.access_token, r.expires_in)
        uid=string.atoi(r.uid)

        u_info=client.users__show(uid=uid)
        save_oauth=SinaWeiboOauth.gql('where user_id=:user_id',user_id=uid).get()
        if save_oauth==None:
            save_oauth=SinaWeiboOauth(user_id=uid)
        save_oauth.screen_name=u_info.screen_name
        save_oauth.access_token=r.access_token
        save_oauth.expires_in=r.expires_in
        save_oauth.put()

        session['access_token']=r.access_token
        session['expires_in']=r.expires_in

        self.response.out.write(str(u_info))

class PageTools:
    def getSinaClient(self):
        session=get_current_session()
        client=weibo_api.APIClient(app_key=APP_KEY, app_secret=APP_SECRET,redirect_uri=CALLBACK_URL)
        client.set_access_token(session['access_token'],session['expires_in'])
        return client
    def render(self, template_name, template_values={}):
        directory = os.path.dirname(__file__)
        path = os.path.join(directory, os.path.join('templates', template_name))
        self.response.out.write(template.render(path, template_values, debug=_DEBUG))

class ReadUserTimeLine(webapp.RequestHandler,PageTools):
    def get(self):
        client=self.getSinaClient()

        timeline=client.statuses__home_timeline()
        statuses=timeline['statuses']
        tl_list=[]
        for node in statuses:
            user=node.get('user')
            one={'text':node.get('text'),
            'imghead':user.get('profile_image_url'),
            'user':user.get('screen_name'),
            }
            tl_list.append(one)
        self.render('weiboInfo.htm',{'timeline':tl_list})

class PostPage(webapp.RequestHandler,PageTools):
    def get(self):
        word=self.request.get('word')
        client=self.getSinaClient()
        res=client.post.statuses__update(status=word)
        self.render('weiboPostRes.htm',{'user':res['user'],'text':res['text']})
class UnfollowAll(webapp.RequestHandler,PageTools):
    def get(self):
        client=self.getSinaClient()
        while 1:
            friends_ids=client.friends__ids()
            idlist=friends_ids['ids']
            if len(idlist)==0:
                break
            for id in idlist:
                try:
                    client.post.friendships__destroy(user_id=id)
                except Exception,e:
                    self.response.out.write(e)

class SinaWeiboUserData(db.Model):
    user_id=db.IntegerProperty()
    user_name=db.StringProperty()
    headimg=db.StringProperty()
    headlarger=db.StringProperty()
    description=db.StringProperty()
    location=db.StringProperty()
    followers_count=db.IntegerProperty()
    friends_count=db.IntegerProperty()
    statuses_count=db.IntegerProperty()

class CollectUser(webapp.RequestHandler,PageTools):
    def get(self):
        user=self.request.get('user')
        if user==None or len(user)==0:
            user='HK_G36'

        weibo_oauth=SinaWeiboOauth.gql('where screen_name=:name',name=user).get()
        if weibo_oauth==None:
            self.response.out.write('no user %s'%user)
            return
        client=weibo_api.APIClient(app_key=APP_KEY, app_secret=APP_SECRET,redirect_uri=CALLBACK_URL)
        client.set_access_token(weibo_oauth.access_token,weibo_oauth.expires_in)
        timeline=client.statuses__public_timeline(count=100)
        statuses=timeline.statuses
        uidrecorded=set()
        count=0

        rm_space=re.compile('\s+')
        for one in statuses:
            user=one.user
            if user.id in uidrecorded:
                continue
            uidrecorded.add(user.id)
            u_date=SinaWeiboUserData.gql('where user_id=:uid',uid=user.id).get()
            if u_date!=None:
                continue
            u_data=SinaWeiboUserData()
            u_data.user_id=user.id
            u_data.user_name=user.screen_name
            u_data.headimg=user.profile_image_url
            u_data.headlarger=user.avatar_large
            u_data.description=re.sub(rm_space,'',user.description)
            u_data.location=user.location
            u_data.followers_count=user.followers_count
            u_data.friends_count=user.friends_count
            u_data.statuses_count=user.statuses_count
            u_data.put()
            count=count+1
        self.response.out.write('saved %d user info'%count)

class CollectUserList(webapp.RequestHandler,PageTools):
    PAGE_SIZE=30
    def get(self):
        query=SinaWeiboUserData.all().order('user_id')
        nextpos=self.request.get('nxt')
        if nextpos!=None and len(nextpos)>0:
            query.filter('user_id >=', string.atoi(nextpos))

        infos=query.fetch(self.PAGE_SIZE)
        self.render('weibouserlist.htm',{'nextpos':nextpos,'infos':infos})

class CollectUserListJson(webapp.RequestHandler,PageTools):
    PAGE_SIZE=100
    def get(self):
        query=SinaWeiboUserData.all().order('user_id')
        nextpos=self.request.get('nxt')
        if nextpos!=None and len(nextpos)>0:
            query.filter('user_id >', string.atoi(nextpos))

        infos=query.fetch(self.PAGE_SIZE)
        infolist=[]
        for info in infos:
            one={"user_id":info.user_id,
            "user_name":info.user_name,
            "headimg":info.headimg,
            "headlarger":info.headlarger,
            "description":info.description,
            "location":info.location,
            "followers_count":info.followers_count,
            "friends_count":info.friends_count,
            "statuses_count":info.statuses_count,
            }
            infolist.append(one)
        json.dump(infolist,self.response.out)


application = webapp.WSGIApplication([
    ('/weibo/authorization',AuthorizationPage),
    ('/weibo/timeline',ReadUserTimeLine),
    ('/weibo/post',PostPage),
    ('/weibo/unfollowall',UnfollowAll),
    ('/weibo/collect',CollectUser),
    ('/weibo/collectlist',CollectUserList),
    ('/weibo/collectlistjson',CollectUserListJson),
    ('/weibo/',RootPage)
], debug=_DEBUG)


def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()

#a = "Sat Mar 28 22:24:24 2009"
#b = time.mktime(time.strptime(a,"%a %b %d %H:%M:%S %Y"))