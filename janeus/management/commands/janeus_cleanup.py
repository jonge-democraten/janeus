from django.core.management.base import BaseCommand
from janeus.models import JaneusUser


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        for u in JaneusUser.objects.all():
            uid = u.uid
            if u.reset_from_ldap() is None:
                print "Deleted {}".format(uid)
            else:
                print "Updated {}".format(uid)
