from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
import logging
from janeus import Janeus
from janeus.models import JaneusUser, JaneusRole, janeus_login

logger = logging.getLogger(__name__)


class JaneusBackend(object):
    @staticmethod
    def login(username, password):
        if hasattr(settings, 'JANEUS_FAKE_LDAP'):
            return True if settings.JANEUS_FAKE_LDAP(username, password) is not None else False
        else:
            logger.info('Trying to authenticate {} in LDAP'.format(username))

            # get dn of user
            res = Janeus().by_uid(username)
            if res is None:
                return False
            dn, attrs = res

            # try to login
            return Janeus().test_login(dn, password)

    @staticmethod
    def get_attrs_groups(username):
        if hasattr(settings, 'JANEUS_FAKE_LDAP'):
            return None, settings.JANEUS_FAKE_LDAP(username, None)
        else:
            # get dn of user
            res = Janeus().by_uid(username)
            if res is None:
                return None, None
            dn, attrs = res

            # get groups of dn
            return attrs, Janeus().groups_of_dn(dn)

    @staticmethod
    def current_site_id():
        if hasattr(settings, 'JANEUS_CURRENT_SITE'):
            site = settings.JANEUS_CURRENT_SITE()
            return site.id if isinstance(site, Site) else site
        else:
            from django.contrib.sites.shortcuts import get_current_site
            site = get_current_site()
            return site.id if isinstance(site, Site) else None

    def authenticate(self, username=None, password=None):
        # authenticate
        if not JaneusBackend.login(username, password):
            return None

        # get LDAP attributes and groups of user
        attrs, groups = JaneusBackend.get_attrs_groups(username)
        groups = groups or []
        if len(groups) == 0:
            return None

        # find all roles of this user, if any
        roles = JaneusRole.objects.filter(role__in=groups)
        if len(roles) == 0:
            return None

        # determine the sites user has any access to
        if len(roles.filter(sites=None)) > 0:
            # user has access to all sites
            sites = Site.objects.all()
        else:
            # user has access to some sites
            sites_query = '{}__in'.format(JaneusRole._meta.get_field('sites').related_query_name())
            sites = Site.objects.filter(**{sites_query: roles})

        # find current site
        site = JaneusBackend.current_site_id()
        if site is not None:
            # check if user gets access
            if site not in [s.pk for s in sites]:
                return None
            # restrict roles to roles of the current site
            roles = roles.filter(Q(sites=None) | Q(sites__id__exact=site))

        # get or create JaneusUser object
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
                # created, so set active, staff, unusable password
                juser.user.set_unusable_password()
                juser.user.is_active = True
                juser.user.is_staff = True
                juser.user.save()
            juser.save()

        # now update attributes of user
        if attrs is not None:
            setattr(juser.user, 'last_name', attrs['sn'][0])
            setattr(juser.user, 'email', attrs['mail'][0])
            juser.user.save()

        # add information to User object
        juser.user._janeus_user = juser
        juser.user._janeus_groups = groups
        juser.user._janeus_roles = roles  # all roles of current site
        juser.user._janeus_sites = sites  # all sites with access

        # send signal
        janeus_login.send(sender=self.__class__, user=juser.user, roles=roles, sites=sites)

        return juser.user

    def get_user(self, user_id):
        try:
            return get_user_model().objects.get(pk=user_id)
        except ObjectDoesNotExist:
            return None

    def set_janeus_data(self, user_obj):
        """ Sets _janeus_user, _janeus_groups, _janeus_roles and _janeus_sites in user object """

        # set Janeus user
        if hasattr(user_obj, '_janeus_user'):
            juser = user_obj._janeus_user
        else:
            try:
                juser = JaneusUser.objects.get(user=user_obj)
                user_obj._janeus_user = juser
            except JaneusUser.DoesNotExist:
                return False

        # set Janeus groups
        if hasattr(user_obj, '_janeus_groups'):
            jgroups = user_obj._janeus_groups
        else:
            attrs, jgroups = JaneusBackend.get_attrs_groups(juser.uid)
            if jgroups is None:
                return False
            user_obj._janeus_groups = jgroups

        # set Janeus roles (part 1)
        if hasattr(user_obj, '_janeus_roles'):
            jroles = user_obj._janeus_roles
        else:
            jroles = JaneusRole.objects.filter(role__in=jgroups)

        # set Janeus sites
        if hasattr(user_obj, '_janeus_sites'):
            jsites = user_obj._janeus_sites
        else:
            # determine the sites user has any access to
            if len(jroles.filter(sites=None)) > 0:
                # user has access to all sites
                jsites = Site.objects.all()
            else:
                # user has access to some sites
                sites_query = '{}__in'.format(JaneusRole._meta.get_field('sites').related_query_name())
                jsites = Site.objects.filter(**{sites_query: jroles})
            user_obj._janeus_sites = jsites

        # set Janeus roles (part 2)
        if not hasattr(user_obj, '_janeus_roles'):
            # find current site
            site = JaneusBackend.current_site_id()
            if site is not None:
                # restrict roles to roles of the current site
                jroles = jroles.filter(Q(sites=None) | Q(sites__id__exact=site))
            user_obj._janeus_roles = jroles

        return True

    def get_group_permissions(self, user_obj, obj=None):
        if user_obj.is_anonymous() or obj is not None:
            return set()
        if not hasattr(user_obj, '_janeus_groups_perm_cache'):
            if self.set_janeus_data(user_obj):
                jroles = user_obj._janeus_roles
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
            if self.set_janeus_data(user_obj):
                jroles = user_obj._janeus_roles
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
