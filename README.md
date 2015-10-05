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

If you are using Python 3, you may want to install a fork of python-ldap first:

`pip install -e git+https://github.com/rbarrois/python-ldap@py3#egg=python-ldap`

Configuration
---

In your `settings.py` file, you need to set at least `JANEUS_SERVER` (LDAP server, e.g. `ldap://127.0.0.1:389/`),
`JANEUS_DN` (username) and `JANEUS_PASS`.
This allows the application to connect to your LDAP server.

To configure the authentication backend, you need to add `janeus` to `INSTALLED_APPS` in `settings.py`.
You must add `janeus.backend.JaneusBackend` to `AUTHENTICATION_BACKENDS`.
Janeus is compatible with Django 1.7 migrations.

An example of these settings in `settings.py`:

    JANEUS_SERVER = "ldap://127.0.0.1:389/"
    JANEUS_DN = "dnoftheuser"
    JANEUS_PASS = "thisisaverysecretpassword"
    
    INSTALLED_APPS += ['janeus']
    
    AUTHENTICATION_BACKENDS = (
        'django.contrib.auth.backends.ModelBackend',
        'janeus.backend.JaneusBackend', 
    )

Instead of a real LDAP server you can also use a fake LDAP server by defining method `JANEUS_FAKE_LDAP` in `settings.py`.
This method takes parameters `username` and `password`, where `password` can be `None` (when called by `janeus_cleanup`, see below).
It must either return `None` for no access or a list of groups (can be empty) on authentication success.

An example of using a fake LDAP server in `settings.py`:

    def JANEUS_FAKE_LDAP(username, password):
        # user "test" with password "1234" has role "default_role"
        # user "admin" with password "admin" has role "admin_role"
        users = {"test": ("1234", ["default_role"]), "admin": ("admin", ["admin_role"])}
        if username not in users:
            return None
        pwd, groups = users[username]
        if password is None or password == pwd:
            return groups
        return None

To manage authentication, add roles in the Janeus admin (in the Django admin).

If you want functioning support for Sites (django-sites), set `JANEUS_CURRENT_SITE` in your `settings.py` to a function that returns the current site id.

Maintenance
---

Janeus implements a management command for `manage.py` called `janeus_cleanup`.
This command checks every `User` that was added by Janeus. Users that no longer have access are deleted.
