from django.db import models
from django.conf import settings
from django.contrib.auth.models import Permission
from janeus import Janeus


class JaneusUser(models.Model):
    uid = models.CharField(max_length=250, unique=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)

    def __unicode__(self):
        return unicode(u"Janeus User '{0}'".format(self.uid))

    def reset_from_ldap(self, attrs=None, groups=None):
        assert self.user is not None
        assert self.pk is not None

        # retrieve attrs and groups if necessary
        if attrs is None or groups is None:
            res = Janeus().by_uid(self.uid)
            if res is None:
                self.user.delete()  # cascades
                return None
            dn, attrs = res
            if groups is None:
                groups = Janeus().groups_of_dn(dn)

        # check if user has access
        if not hasattr(settings, 'JANEUS_AUTH') or not settings.JANEUS_AUTH(self.uid, groups):
            self.user.delete()  # cascades
            return None

        # set attributes
        setattr(self.user, 'last_name', attrs['sn'][0])
        setattr(self.user, 'email', attrs['mail'][0])
        setattr(self.user, 'is_active', True)
        setattr(self.user, 'is_staff', True)

        # remove all permissions
        self.user.user_permissions.clear()

        # add permissions
        if hasattr(settings, 'JANEUS_AUTH_PERMISSIONS'):
            for p in Permission.objects.filter(settings.JANEUS_AUTH_PERMISSIONS(self.uid, groups)):
                self.user.user_permissions.add(p)

        # save user
        self.user.save()
        return self.user
