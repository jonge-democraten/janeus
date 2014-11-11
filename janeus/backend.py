from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
import logging
from janeus import Janeus
from janeus.models import JaneusUser

logger = logging.getLogger(__name__)


class JaneusBackend(object):
    def authenticate(self, username=None, password=None):
        logger.info("Trying to authenticate %s" % (username,))
        j = Janeus()

        # get dn of user
        res = j.by_uid(username)
        if res is None:
            return None
        dn, attrs = res

        # ok we have dn, try to login
        if not j.test_login(dn, password):
            return None

        # ok login works, get groups
        groups = j.groups_of_dn(dn)

        # check if this user has access
        if not settings.JANEUS_AUTH(username, groups):
            return None

        # get or create JaneusUser
        try:
            juser = JaneusUser.objects.get(uid=username)
        except JaneusUser.DoesNotExist:
            juser = JaneusUser(uid=username, user=None)
            juser.save()

        # get or create User
        if juser.user is None:
            model = get_user_model()
            username_field = getattr(model, 'USERNAME_FIELD', 'username')

            kwargs = {
                username_field + '__iexact': username,
                'defaults': {username_field: username.lower()}
            }

            user, created = model.objects.get_or_create(**kwargs)
            if created:
                user.set_unusable_password()
            juser.user = user
            juser.save()

        return juser.reset_from_ldap(attrs=attrs, groups=groups)

    def get_user(self, user_id):
        try:
            return get_user_model().objects.get(pk=user_id)
        except ObjectDoesNotExist:
            return None
