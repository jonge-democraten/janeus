from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
import logging
from janeus import Janeus

logger = logging.getLogger(__name__)

class JaneusBackend(object):
    def authenticate(self, username=None, password=None):
        logger.info("Trying to authenticate %s" % (username,))
        j = Janeus()
        # get dn of user
        res = j.by_uid(username)
        if res == None: return None
        dn, attrs = res

        # ok we have dn, try to login
        if not j.test_login(dn, password): return None

        # ok login works, get groups
        groups = [g for g in j.groups_of_dn(dn)]
            
        if not settings.JANEUS_AUTH(username, groups): return None

        # get or create nieuwe User
        model = get_user_model()
        username_field = getattr(model, 'USERNAME_FIELD', 'username')

        kwargs = {
            username_field + '__iexact': username,
            'defaults': {username_field: username.lower()}
        }

        user, created = model.objects.get_or_create(**kwargs)

        if created: user.set_unusable_password()

        setattr(user, 'last_name', attrs['sn'][0]);
        setattr(user, 'email', attrs['mail'][0]);
        setattr(user, 'is_active', True)
        setattr(user, 'is_staff', True)

        for p in Permission.objects.filter(settings.JANEUS_AUTH_PERMISSIONS(username, groups)):
            user.user_permissions.add(p)

        user.save()
        return user
           
    def get_user(self, user_id):
        try:
            return get_user_model().objects.get(pk=user_id)
        except ObjectDoesNotExist:
            return None
