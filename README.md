Janeus
===

Janeus implements LDAP-related functionality for sites of the Jonge Democraten, especially an authentication backend that allows users in LDAP to login and get permissions in Django.

The application is open source and licensed with the MIT license.
While the implementation is obviously tailored to the LDAP configuration of the Jonge Democraten,
modifying the source code should be pretty straightforward.

While originally developed for Python 2, we now support and test on Python 3.

Installation
---

Install the application in your virtualenv installation:

`pip install -e git+https://github.com/jonge-democraten/janeus#egg=janeus`

Configuration
---

In your `settings.py` file, you need to set at least `JANEUS_SERVER`,
`JANEUS_DN` (username) and `JANEUS_PASS`.
This allows Janeus to connect to your LDAP server.

If you want to use the authentication backend, you need to add `janeus` to `INSTALLED_APPS` in `settings.py`.
You need to add `janeus.backend.JaneusBackend` to `AUTHENTICATION_BACKENDS`.
You also need to add `janeus.utils.CurrentRequestMiddleware` to `MIDDLEWARE_CLASSES`
The authentication backend requires the django-sites framework (installed and in `INSTALLED_APPS`).
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

Janeus defines two models: JaneusUser and JaneusRole.
The JaneusRole objects must be created in the Django admin to allow LDAP users to login.
Each JaneusRole assigns to 1 LDAP group for either all sites or for a selection of sites,
a number of permissions and group permissions.
The backend only gives access to users that are in LDAP groups that have matching JaneusRole objects.
When a user is given access, Janeus creates a JaneusUser object and a normal User object.
If Mezzanine is installed, Janeus also created SitePermission objects for all sites on which the user has any permissions via Janeus.

By default, Janeus retrieves the current site id from Mezzanine (if installed) or from django.contrib.sites.shortcuts.get_current_site.
This behavior can be overridden by setting `JANEUS_CURRENT_SITE` in `settings.py`.

Instead of a real LDAP server you can also use a fake LDAP server by defining method `JANEUS_FAKE_LDAP` in `settings.py`.
This method takes parameters `username` and `password`, where `password` can be `None` (when called by `janeus_cleanup`, see below).
It must either return `None` or `[]` for no access or a list of groups on authentication success.

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

Maintenance
---

Janeus implements a management command for `manage.py` called `janeus_cleanup`.
This command checks every `User` that was added by Janeus. Users that no longer have access are deleted.
It is not really necessary to run this management command unless there is a high number of Janeus users and you want to keep the database small.
