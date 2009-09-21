from django.db import models
from django.contrib.auth.models import User

class Host(models.Model):
     cobbler_name = models.CharField(max_length=255)

     def __unicode__(self):
         return self.cobbler_name

class Guest(models.Model):
     cobbler_name = models.CharField(max_length=255)
     virt_name = models.CharField(max_length=255)
     host = models.ForeignKey(Host)
     owner = models.ForeignKey(User)
     expire_date = models.DateTimeField('expiration date')
     purpose = models.CharField(max_length=255)

     def __unicode__(self):
         return self.cobbler_name

#class Poll(models.Model):
#    question = models.CharField(max_length=200)
#    pub_date = models.DateTimeField('date published')
#
#class Choice(models.Model):
#    poll = models.ForeignKey(Poll)
#    choice = models.CharField(max_length=200)
#    votes = models.IntegerField()

