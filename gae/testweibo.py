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

_DEBUG=True
APP_KEY = '685427335'
APP_SECRET = '1d735fa8f18fa94d87cd9196867edfb6'

class SinaWeiboOauth(db.Model):
    user_id=db.IntegerProperty(required=True)
    screen_name=db.StringProperty()
    access_key = db.StringProperty()
    access_secret = db.StringProperty()

class RootPage(webapp.RequestHandler):
    def get(self):
        session=get_current_session()
        if session!=None:
            if session.has_key('weibo_access_key') and session.has_key('weibo_access_secret'):
                self.redirect('./timeline')
                return
        CALLBACK_URL=self.request.url+'authorization'
        client = weibo.APIClient(app_key=APP_KEY, app_secret=APP_SECRET, callback=CALLBACK_URL)
        request_token = client.get_request_token()
        session['oauth_token']=request_token.oauth_token
        session['oauth_secret']=request_token.oauth_token_secret
        url = client.get_authorize_url(request_token)
        self.redirect(url)

class AuthorizationPage(webapp.RequestHandler):
    def get(self):
        session=get_current_session()
        oauth_token = self.request.get('oauth_token')
        oauth_verifier = self.request.get('oauth_verifier')
        oauth_token_secret=session['oauth_secret']
        del session['oauth_token']
        del session['oauth_secret']

        request_token = weibo.OAuthToken(oauth_token, oauth_token_secret, oauth_verifier)
        client = weibo.APIClient(app_key=APP_KEY, app_secret=APP_SECRET, token=request_token)

        access_token = client.get_access_token()
        client = weibo.APIClient(app_key=APP_KEY, app_secret=APP_SECRET, token= access_token)
        account = client.account__verify_credentials()

        save_oauth=SinaWeiboOauth.gql('where user_id=:user_id',user_id=account.id).get()
        if save_oauth==None:
            save_oauth=SinaWeiboOauth(user_id=account.id)
        save_oauth.screen_name=account.screen_name
        save_oauth.access_key=access_token.oauth_token
        save_oauth.access_secret=access_token.oauth_token_secret
        save_oauth.put()

        session['weibo_access_key']=access_token.oauth_token
        session['weibo_access_secret']=access_token.oauth_token_secret

        self.response.out.write(str(account))

class PageTools:
    def getSinaClient(self):
        session=get_current_session()
        token=weibo.OAuthToken(session['weibo_access_key'],session['weibo_access_secret'])
        client=weibo.APIClient(app_key=APP_KEY,app_secret=APP_SECRET,token=token)
        return client
    def render(self, template_name, template_values={}):
        directory = os.path.dirname(__file__)
        path = os.path.join(directory, os.path.join('templates', template_name))
        self.response.out.write(template.render(path, template_values, debug=_DEBUG))

class ReadUserTimeLine(webapp.RequestHandler,PageTools):
    def get(self):
        client=self.getSinaClient()

        timeline=client.statuses__home_timeline()
        tl_list=[]
        for node in timeline:
            user=node['user']
            one={'text':node.get('text'),
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

application = webapp.WSGIApplication([
    ('/weibo/authorization',AuthorizationPage),
    ('/weibo/timeline',ReadUserTimeLine),
    ('/weibo/post',PostPage),
    ('/weibo/unfollowall',UnfollowAll),
    ('/weibo/',RootPage)
], debug=_DEBUG)


def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()

#a = "Sat Mar 28 22:24:24 2009"
#b = time.mktime(time.strptime(a,"%a %b %d %H:%M:%S %Y"))