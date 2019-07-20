# Janeus Documentation

## What is Janeus?

Janeus 
provides authentication and permission management from LDAP group memberships
to Django web applications.
When a user logs in using their LDAP password, a Django admin user is automatically created.
The permissions are updated based on the LDAP group memberships and the settings of the Janeus roles in the database.
Janeus is compatible with Mezzanine.

## Requirements

Janeus requires Django Admin, Django Sites, and `pyldap>=2.4.20`.
Mezzanine is supported but optional.

## Quick start

* Install `janeus` in the virtual environment, e.g., with `pip`.
* Update `settings.py`:
    - Add `janeus` to `INSTALLED_APPS` in `settings.py`.
    - Add `janeus.backend.JaneusBackend` to `AUTHENTICATION_BACKENDS`.
    - (**If you don't have Mezzanine**) Add `janeus.utils.CurrentRequestMiddleware` to `MIDDLEWARE`.
    - Either implement `JANEUS_FAKE_LDAP` or set `JANEUS_SERVER`, `JANEUS_DN` and `JANEUS_PASS` to appropriate values.
* Run `python manage.py migrate` to update the database.

For maintenance:

* Regularly run the management command `janeus_cleanup`, although this is not strictly necessary.

## Database objects

A **Janeus user** is an object in the database that associates an (automically created) Django admin user with an LDAP user id.
A **Janeus role** associates an LDAP group with sets of Django sites, Django admin groups and Django admin permissions.
If no sites are set for a Janeus role, then the permissions and groups apply to all sites.

## Authentication Backend

The `janeus.backend.JaneusBackend` class implements authentication and permissions management.
To use the backend, add the class string to the `AUTHENTICATION_BACKENDS` list in `settings.py`.
When authenticating and an LDAP user with the username and access rights to the current site exists, 
a Django admin user with the exact same username is automatically created or reused.

The created Django admin users have no stored usable password, meaning that it is safe to delete Janeus users.
Django does not let users without a usable password authenticate.

## LDAP Pool

In order to prevent creating many connections with LDAP, a ``LDAPPool`` **singleton** object manages connections to LDAP. Up to 8 (by default) connections are created and these are used by the ``Janeus`` object when querying user information.

## Middleware

The `janeus.utils.CurrentRequestMiddleware` class is required unless Mezzanine is installed.
Using the middleware is as easy as adding the class string to the `MIDDLEWARE` list in `settings.py`.
This middleware stores the current request in thread local storage, which is needed to
obtain the current site from Django's Sites framework.

## Management commands

There is one management command:

* `python manage.py janeus_cleanup`

For every Janeus user currently in the database,
the command checks if they are still registered in LDAP and if they have any relevant roles that are in the database.
If this is not the case, the Janeus user is deleted from the database.
However, the associated Django admin user is **not** automatically deleted.
It is not recommended to delete the Django admin user, because this also deletes log entries and possibly other information.
If the user still has access and relevant roles, then the name and email address of the associated Django admin user are updated with the values obtained from LDAP.

**It is recommended to setup a cronjob that regularly runs ``janeus_cleanup``, however this is not necessary. User permissions are updated when a user authenticates.**

Notice that if a Django admin user is deleted, as well as the associated Janeus user, then the objects will be created again the next time the user logs in.

## Settings

You can set the following settings in `settings.py` to control the behavior of Janeus:

* `JANEUS_SERVER` - The address of the LDAP server, for example: "ldap://127.00.1:389/"
* `JANEUS_DN` - The username (distinguished name) for the connection.
* `JANEUS_PASS` - The password for the connection.
* `JANEUS_FAKE_LDAP` - Override the authentication backend with a mock LDAP server.
* `JANEUS_CURRENT_SITE` - Override the current site id (number).
* `JANEUS_MEZZANINE_CLEAR_SITEPERMISSION` - Force Janeus to clear all Mezzanine site permissions during authentication; the default setting is `False`.

The `JANEUS_FAKE_LDAP` setting is a function that receives the parameters `username` and `password`.
If `password` is not `None`, then the function must check if the authentication fails, and if so, return `None`.
If `password` is `None` or the authentication succeeds, then the function must return a list of groups that the user is a member of, or `[]` if the user is not a member of any group.

Example:

    def JANEUS_FAKE_LDAP(username, password):
        if username == "james":
            if password is None or password == "bond777":
                return ["license_to_kill", "access_to_q"]
        return None  # default behavior
