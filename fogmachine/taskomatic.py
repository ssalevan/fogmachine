#!/usr/bin/python
# Simple periodic task scheduler
# mostly ganked from:
# http://stackoverflow.com/questions/373335/suggestions-for-a-cron-like-scheduler-in-python

import logging
import signal
import traceback
import time
import os
import sys
import pdb

from datetime import datetime, timedelta
from periodic_tasks import *

log = logging.getLogger("fogmachine.taskomatic")

# Some utility classes / functions first
class AllMatch(set):
    """Universal set - match everything"""
    def __contains__(self, item): return True

allMatch = AllMatch()

def conv_to_set(obj):  # Allow single integer to be provided
    if isinstance(obj, (int,long)):
        return set([obj])  # Single item
    if not isinstance(obj, set):
        obj = set(obj)
    return obj

# The actual Event class
class Task(object):
    """
    A Task is a wrapper class that pairs a Python method to run
    frequency information so that Taskomatic can run them at the given
    time intervals
    """
    def __init__(self, action, min=allMatch, hour=allMatch, 
                       day=allMatch, month=allMatch, dow=allMatch, 
                       args=(), kwargs={}):
        self.mins = conv_to_set(min)
        self.hours= conv_to_set(hour)
        self.days = conv_to_set(day)
        self.months = conv_to_set(month)
        self.dow = conv_to_set(dow)
        self.action = action
        self.args = args
        self.kwargs = kwargs

    def matchtime(self, t):
        """Return True if this event should trigger at the specified datetime"""
        return ((t.minute     in self.mins) and
                (t.hour       in self.hours) and
                (t.day        in self.days) and
                (t.month      in self.months) and
                (t.weekday()  in self.dow))

    def check(self, t):
        """
        Given time object t, checks to see if it is time to run the supplied
        Python method
        """
        log.debug( "Checking timematch for action: %s" % self.action )
        if self.matchtime(t):
            log.info("Running periodic task: %s" % self.action )
            try:
                #pdb.set_trace()
                self.action(*self.args, **self.kwargs)
            except:
                log.error("Error running task:\n%s" % traceback.format_exc())
            log.info( "Periodic task complete: %s" % self.action )

class Taskomatic(object):
    """
    A reimplementation of Crontab in Python, ganked from the above site, with
    a few bugfixes and the ability to run in a separate process added to suit
    the needs of Fogmachine
    """
    def __init__(self, *events):
        self.events = events

    def start(self):
        """
        Starts Taskomatic in a separate process by calling os.fork()
        """
        self.child = os.fork()
        if self.child == 0:
            return
        else:
            self.run()
            
    def run(self):
        """
        Calls main Taskomatic loop, listens for SIGINT or fatal exceptions
        """
        try:
            self.main_loop()
        except KeyboardInterrupt:
            log.info("Taskomatic caught SIGINT.  Dying...")
            sys.exit(0)
        except:
            log.info("Taskomatic caught error, dying:\n%s" % traceback.format_exc())
            self.die()
            
    def die(self):
        """
        Called after Taskomatic catches exception, kills child process
        """
        try:
            os.kill(self.child, signal.SIGKILL)
        except OSError:
            pass
        
    def main_loop(self):
        """
        Taskomatic main loop, checks every time interval set to determine
        if a Task (a Python method wrapped with run frequency information)
        should be executed
        """
        log.info("Taskomatic started at %s." % datetime.now())
        t = datetime(*datetime.now().timetuple()[:5])
        while 1:
            for e in self.events:
                e.check(t)
                
            t = datetime(*datetime.now().timetuple()[:5])
            t += timedelta(minutes=1)
            time.sleep((t - datetime.now()).seconds + 1)
                
def start_taskomatic():
    """
    Creates a new Taskomatic object, populates it with Fogmachine's
    periodically-running tasks, and starts it in a separate process
    """
    taskomatic = Taskomatic(
        Task(retire_expired_guests, min=0),
        Task(update_free_mem, min=range(0,60,5)),
        Task(update_guest_states, min=range(0,60,5))) 
    taskomatic.start()
