from __future__ import unicode_literals

import re
from binascii import hexlify
from os import urandom

from django.contrib.auth.models import User
from django.db import models


class Token(models.Model):
    """
    User token for API access.
    """
    created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, 
                             related_name='authtokens', 
                             on_delete=models.CASCADE)
    key = models.CharField(max_length=100)
    active = models.BooleanField(default=True)

    def generate_key(self):
        """Generate a 20 bytes access key"""
        self.key = hexlify(urandom(20)).decode()
        return self.key

    def disable(self):
        """Disable this token."""
        if self.active:
            self.active = False
            self.save()

    def enable(self):
        """Enable this token."""
        if not self.active:
            self.active = True
            self.save()

    @staticmethod
    def auth(request):
        # Check HTTP AUTH header:
        if request.META.has_key('HTTP_AUTHENTICATION'):
            auth = request.META.get('HTTP_AUTHENTICATION')
        else:
            return False
        # Get username and token key:
        #p = "Token ([a-zA-Z0-9_-]+):([a-zA-Z0-9_-]+)"
        p = "Token ([a-zA-Z0-9]+)"
        match = re.match(p, auth)
        if match is None:
            return False
        #username = match.groups()[0] 
        key = match.groups()[0]
        # Check user and key:
        try:
            #user = User.objects.get(username=username)
            #token = Token.objects.get(user=user, key=key)
            token = Token.objects.get(key=key)
            user = token.user
            print(user.username)
            print(token.key)
            return token.active
        except:
            return False
