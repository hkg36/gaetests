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
from google.appengine.api import taskqueue

class Addtask(webapp.RequestHandler):
    def get(self):
        backq = taskqueue.Queue('backendqueue')
        tasks = []
        payload_str=self.request.get('payload')
        if payload_str==None:
            payload_str = 'show task'
        tasks.append(taskqueue.Task(payload=payload_str, method='PULL'))
        backq.add(tasks)


application = webapp.WSGIApplication([
    ('/main/addtask', Addtask)
], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()