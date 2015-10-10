from __future__ import unicode_literals
from django.db import models
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class JaneusRole(models.Model):
    role = models.CharField(max_length=250)
    groups = models.ManyToManyField(Group, blank=True)
    permissions = models.ManyToManyField(Permission, blank=True)
    sites = models.ManyToManyField("sites.Site", blank=True)

    def __str__(self):
        return "Role '{0}'".format(self.role)


@python_2_unicode_compatible
class JaneusUser(models.Model):
    uid = models.CharField(max_length=250, unique=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return "Janeus User '{0}'".format(self.uid)
