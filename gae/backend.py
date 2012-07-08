#!/usr/bin/env python
# -*- coding: utf-8 -*-
import weibo_api
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import images
from google.appengine.api import memcache
from google.appengine.ext.webapp import template
from google.appengine.api import apiproxy_stub_map
from google.appengine.api import runtime
import json
import os
import string
from gaesessions import get_current_session
from datamodel import *
import re
import logging
import time
from google.appengine.api import taskqueue

class FetchBackend(webapp.RequestHandler):
    def get(self):
        logging.info('one run');
        taskq=taskqueue.Queue('backendqueue')
        while not runtime.is_shutting_down():
            try:
                tasks = taskq.lease_tasks(3600, 100)
            except Exception as e:
                logging.error(e)
                time.sleep(60)
                return
            logging.info('pull %d task',len(tasks))
            if len(tasks)==0:
                return
            tasktodelete=[]
            for task in tasks:
                logging.info(task.payload)
                tasktodelete.append(task)
            taskq.delete_tasks(tasks)


def my_shutdown_hook():
  apiproxy_stub_map.apiproxy.CancelApiCalls()
  #save_state()
runtime.set_shutdown_hook(my_shutdown_hook)

application = webapp.WSGIApplication([
('/_ah/start',FetchBackend)],
debug=True)

def main():
    run_wsgi_app(application)
if __name__ == '__main__':
    main()
