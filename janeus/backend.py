from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
import logging
from janeus import Janeus
from janeus.models import JaneusUser, JaneusRole, janeus_login

logger = logging.getLogger(__name__)


class JaneusBackend(object):
    @staticmethod
    def real_ldap(username, password):
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

    @staticmethod
    def fake_ldap(username, password):
        """Returns list of groups, or None if access denied."""
        groups = settings.JANEUS_FAKE_LDAP(username, password)
        return groups

    @staticmethod
    def login(username, password):
        if hasattr(settings, 'JANEUS_FAKE_LDAP'):
            return None, JaneusBackend.fake_ldap(username, password)
        else:
            return JaneusBackend.real_ldap(username, password)

    @staticmethod
    def get_attrs_groups(username):
        if hasattr(settings, 'JANEUS_FAKE_LDAP'):
            groups = settings.JANEUS_FAKE_LDAP(username, None)
            if groups is None or groups == []:
                return None, None
            else:
                return None, groups
        else:
            res = Janeus().by_uid(username)
            if res is None:
                return None, None
            dn, attrs = res
            groups = Janeus().groups_of_dn(dn)
            return attrs, groups

    def authenticate(self, username=None, password=None):
        # authenticate plus get groups
        attrs, groups = JaneusBackend.login(username, password)

        # find all roles of this user, if any
        if groups is None:
            return None

        roles = JaneusRole.objects.filter(role__in=groups)

        # find current site
        if hasattr(settings, 'JANEUS_CURRENT_SITE'):
            site = settings.JANEUS_CURRENT_SITE()
        else:
            site = None
        if site is not None:
            roles = roles.filter(Q(sites=None) | Q(sites__id__exact=site))

        # if no roles, no access
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

            juser.user, created = model.objects.get_or_create(**kwargs)
            if created:
                juser.user.set_unusable_password()
                juser.user.is_active = True
                juser.user.is_staff = True
                juser.user.save()
            juser.save()

        if attrs is not None:
            setattr(juser.user, 'last_name', attrs['sn'][0])
            setattr(juser.user, 'email', attrs['mail'][0])
            juser.user.save()
        juser.user.save()

        juser.user._janeus_user = juser
        juser.user._janeus_groups = groups

        # send signal
        roles = JaneusRole.objects.filter(role__in=groups)
        janeus_login.send(sender=self.__class__, user=juser.user, roles=roles)

        return juser.user

    def get_user(self, user_id):
        try:
            return get_user_model().objects.get(pk=user_id)
        except ObjectDoesNotExist:
            return None

    def get_user_groups(self, user_obj):
        # find Janeus user
        if isinstance(user_obj, JaneusUser):
            juser = user_obj
        else:
            juser = getattr(user_obj, '_janeus_user', None)
        if juser is None:
            try:
                juser = JaneusUser.objects.get(user=user_obj)
            except JaneusUser.DoesNotExist:
                pass
        if juser is None:
            return None, None

        jgroups = getattr(user_obj, '_janeus_groups', None)
        if jgroups is None:
            attrs, jgroups = JaneusBackend.get_attrs_groups(juser.uid)
        if jgroups is None:
            return None, None

        user_obj._janeus_user = juser
        user_obj._janeus_groups = jgroups

        return juser, jgroups

    def get_group_permissions(self, user_obj, obj=None):
        if user_obj.is_anonymous() or obj is not None:
            return set()
        if not hasattr(user_obj, '_janeus_groups_perm_cache'):
            juser, jgroups = self.get_user_groups(user_obj)
            if jgroups is not None:
                jroles = JaneusRole.objects.filter(role__in=jgroups)
                # find current site
                if hasattr(settings, 'JANEUS_CURRENT_SITE'):
                    site = settings.JANEUS_CURRENT_SITE()
                else:
                    site = None
                if site is not None:
                    jroles = jroles.filter(Q(sites=None) | Q(sites__id__exact=site))
            else:
                jroles = set()
            if len(jroles):
                gperms_query = 'group__{}__in'.format(JaneusRole._meta.get_field('groups').related_query_name())
                gperms = Permission.objects.filter(**{gperms_query: jroles})
                gperms = gperms.values_list('content_type__app_label', 'codename').order_by()
                gperms = set("%s.%s" % (ct, name) for ct, name in gperms)
                user_obj._janeus_groups_perm_cache = gperms
            else:
                user_obj._janeus_groups_perm_cache = set()
        return user_obj._janeus_groups_perm_cache

    def get_all_permissions(self, user_obj, obj=None):
        if user_obj.is_anonymous() or obj is not None:
            return set()
        if not hasattr(user_obj, '_janeus_perm_cache'):
            juser, jgroups = self.get_user_groups(user_obj)
            if jgroups is not None:
                jroles = JaneusRole.objects.filter(role__in=jgroups)
                # find current site
                if hasattr(settings, 'JANEUS_CURRENT_SITE'):
                    site = settings.JANEUS_CURRENT_SITE()
                else:
                    site = None
                if site is not None:
                    jroles = jroles.filter(Q(sites=None) | Q(sites__id__exact=site))
            if len(jroles):
                jperms_query = '{}__in'.format(JaneusRole._meta.get_field('groups').related_query_name())
                jperms = Permission.objects.filter(**{jperms_query: jroles})
                jperms = jperms.values_list('content_type__app_label', 'codename').order_by()
                jperms = set("%s.%s" % (ct, name) for ct, name in jperms)
                user_obj._janeus_perm_cache = jperms.union(self.get_group_permissions(user_obj, obj))
            else:
                user_obj._janeus_perm_cache = set()
        return user_obj._janeus_perm_cache

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_active:
            return False
        return perm in self.get_all_permissions(user_obj, obj)

    def has_module_perms(self, user_obj, app_label):
        if not user_obj.is_active:
            return False
        for perm in self.get_all_permissions(user_obj):
            if perm[:perm.index('.')] == app_label:
                return True
        return False
