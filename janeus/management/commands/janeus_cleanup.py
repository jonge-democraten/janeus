from __future__ import print_function
from django.core.management.base import BaseCommand
from janeus.models import JaneusUser, JaneusRole
from janeus.backend import JaneusBackend


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        for u in JaneusUser.objects.all():
            self.check_user(u)

    def check_user(self, juser):
        attrs, groups = JaneusBackend.get_attrs_groups(juser.uid)

        # check if user has access
        roles = JaneusRole.objects.filter(role__in=groups)
        if len(roles) == 0:
            juser.user.delete()  # cascades
            print("Deleted {}".format(juser.uid))
        else:
            # set attributes
            if attrs is not None:
                setattr(juser.user, 'last_name', attrs['sn'][0])
                setattr(juser.user, 'email', attrs['mail'][0])
                juser.user.save()
                print("Updated {}".format(juser.uid))
