from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
import logging
from janeus import Janeus
from janeus.models import JaneusUser, JaneusRole

logger = logging.getLogger(__name__)


class JaneusBackend(object):
    def real_ldap(self, username, password):
        """Returns attributes, groups, or None, None if access denied."""
        logger.info("Trying to authenticate %s in LDAP" % (username,))
        j = Janeus()

        # get dn of user
        res = j.by_uid(username)
        if res is None:
            return None, None
        dn, attrs = res

        # ok we have dn, try to login
        if not j.test_login(dn, password):
            return None, None

        # ok login works, get groups and roles
        groups = j.groups_of_dn(dn)
        return attrs, groups

    def fake_ldap(self, username, password):
        """Returns list of groups, or None if access denied."""
        groups = settings.JANEUS_FAKE_LDAP(username, password)
        return groups

    def authenticate(self, username=None, password=None):
        # authenticate plus get groups
        if hasattr(settings, 'JANEUS_FAKE_LDAP'):
            groups = self.fake_ldap(username, password)
            attrs = None
        else:
            attrs, groups = self.real_ldap(username, password)

        # if groups is None then authentication failed or user not found
        # if groups is [] then user not in any group (also no access)
        if groups is None or groups == []:
            return None

        # get roles
        roles = JaneusRole.objects.filter(role__in=groups)

        # check if this user has access
        if len(roles) == 0:
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

        return juser.reset_from_ldap(attrs=attrs, roles=roles)

    def get_user(self, user_id):
        try:
            return get_user_model().objects.get(pk=user_id)
        except ObjectDoesNotExist:
            return None
