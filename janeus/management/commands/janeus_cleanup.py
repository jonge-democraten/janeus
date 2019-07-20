from __future__ import print_function
from django.core.management.base import BaseCommand
from janeus.models import JaneusUser, JaneusRole
from janeus.backend import JaneusBackend


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        for u in JaneusUser.objects.all():
            self.check_user(u)

    def check_user(self, juser):
        # first we retrieve the groups that the given user <juser.uid> is in
        attrs, groups = JaneusBackend.get_attrs_groups(juser.uid)

        if groups is None:
            # the user does not actually exist
            juser.user.delete()  # cascades
            print("Deleted unknown user {}".format(juser.uid))
        else:
            # retrieve the user's groups that are roles in our database
            roles = JaneusRole.objects.filter(role__in=groups)
            if len(roles) == 0:
                # the user has no relevant roles
                juser.user.delete()  # cascades
                print("Deleted user without roles {}".format(juser.uid))
            else:
                # update the attributes, if we received them
                if attrs is not None:
                    if 'sn' in attrs:
                        setattr(juser.user, 'last_name', attrs['sn'][0])
                    if 'mail' in attrs:
                        setattr(juser.user, 'email', attrs['mail'][0])
                    juser.user.save()
                    print("Updated user {}".format(juser.uid))
