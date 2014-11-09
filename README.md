Janeus
===

Janeus implements LDAP-related functionality for sites of the Jonge Democraten, especially a feature that allows users in LDAP to login and get administrator permissions in Django.

The application is open source and licensed with the MIT license.
While the implementation is obviously tailored to the LDAP configuration of the Jonge Democraten,
modifying the source code should be pretty straightforward.

Installation
---

First install the application in your virtualenv installation:

`pip install -e git+https://github.com/jonge-democraten/janeus#egg=janeus`

Configuration
---

In your `settings.py` file, you need to set at least `JANEUS_SERVER` (LDAP server, e.g. `ldap://127.0.0.1:389/`),
`JANEUS_DN` (username) and `JANEUS_PASS`.
This allows the application to connect to your LDAP server.

To configure the authentication backend, you need to add `janeus` to `INSTALLED_APPS` in `settings.py`.
Janeus is compatible with Django 1.7 migrations.
Then, set `JANEUS_AUTH` and `JANEUS_AUTH_PERMISSIONS`. These are both methods
that receive the parameters `user` (uid) and `groups` (array of groups). `JANEUS_AUTH` must return either `True` or `False`.
`JANEUS_AUTH_PERMISSIONS` must return a `Q` object that is a parameter to `Permission.objects.filter()`. Finally, you must add `janeus.backend.JaneusBackend` to `AUTHENTICATION_BACKENDS`.

An example of these settings in `settings.py`:

    JANEUS_SERVER = "ldap://127.0.0.1:389/"
    JANEUS_DN = "dnoftheuser"
    JANEUS_PASS = "thisisaverysecretpassword"
    
    INSTALLED_APPS += ['janeus']
    
    def JANEUS_AUTH(user, groups):
        # Everyone in groups 'ictteam' and 'landelijkbestuur' gets access
        return "ictteam" in groups or "landelijkbestuur" in groups
    
    def JANEUS_AUTH_PERMISSIONS(user, groups):
        # All users get access to 'zues' and 'appolo' permissions
        from django.db.models import Q
        return Q(content_type__app_label='zues') | Q(content_type__app_label='appolo')
    
    AUTHENTICATION_BACKENDS = (
        'janeus.backend.JaneusBackend', 
        'django.contrib.auth.backends.ModelBackend',
    )

Maintenance
---

Janeus implements a management command for `manage.py` called `janeus_cleanup`.
This command checks every `User` that was added by Janeus and resets the permissions. Users that no longer have access are deleted.
