#! /usr/bin/env python
#coding=utf-8
from google.appengine.ext import db
class SinaWeiboOauth(db.Model):
    user_id=db.IntegerProperty(required=True)
    screen_name=db.StringProperty()
    access_token = db.StringProperty()
    expires_in=db.IntegerProperty()

class TwitterOauth(db.Model):
    user_id=db.IntegerProperty()
    screen_name=db.StringProperty()
    access_key = db.StringProperty()
    access_secret = db.StringProperty()

class AccountConnect(db.Model):
    max_msg=db.StringProperty()
    SinaOauth=db.ReferenceProperty(SinaWeiboOauth)
    TwitterOauth=db.ReferenceProperty(TwitterOauth)