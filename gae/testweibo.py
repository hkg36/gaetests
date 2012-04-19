import weibo
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import images
from google.appengine.api import memcache

APP_KEY = '685427335'
APP_SECRET = '1d735fa8f18fa94d87cd9196867edfb6'

class SinaWeiboOauth(db.Model):
    user_id=db.IntegerProperty(required=True)
    screen_name=db.StringProperty()
    access_key = db.StringProperty()
    access_secret = db.StringProperty()
    
class RootPage(webapp.RequestHandler):
    def get(self):
        CALLBACK_URL=self.request.url+'authorization'
        client = weibo.APIClient(app_key=APP_KEY, app_secret=APP_SECRET, callback=CALLBACK_URL)
        request_token = client.get_request_token()
        memcache.set(request_token.oauth_token, request_token.oauth_token_secret,60*5)
        url = client.get_authorize_url(request_token)
        self.redirect(url)

class AuthorizationPage(webapp.RequestHandler):
    def get(self):
        oauth_token = self.request.get('oauth_token')
        oauth_verifier = self.request.get('oauth_verifier')
        oauth_token_secret=memcache.get(oauth_token)
        memcache.delete(oauth_token)
        
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
        
        self.response.out.write(str(account))
        
application = webapp.WSGIApplication([
    ('/weibo/authorization',AuthorizationPage),
    ('/weibo/',RootPage)
], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()