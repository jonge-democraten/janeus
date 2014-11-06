"""janeus implements LDAP-related functionality for sites of de Jonge Democraten.
"""

from contextlib import contextmanager
from django.conf import settings
import ldap
from ldap.filter import filter_format
from janeus.ldappool import LDAPPool

class Janeus(object):
    @contextmanager
    def connection(self):
        with LDAPPool().connection(settings.JANEUS_SERVER, settings.JANEUS_DN, settings.JANEUS_PASS) as conn: yield conn

    def by_uid(self, uid):
        """Opvragen (dn, attrs) van gebruiker met uid, of geeft None terug als niet uniek gevonden"""
        baseDN = "ou=users,dc=jd,dc=nl"
        searchFilter = filter_format('(uid=%s)', (str(uid),))
        with self.connection() as l: result_data = l.search_st(baseDN, ldap.SCOPE_ONELEVEL, searchFilter, timeout=1)
        if len(result_data) != 1: return None
        dn, attrs = result_data[0]
        return dn, attrs

    def by_lidnummer(self, lidnummer):
        """Opvragen (dn, attrs) van gebruiker met lidnummer, of geeft None terug als niet uniek gevonden"""
        baseDN = "cn="+str(int(lidnummer))+",ou=users,dc=jd,dc=nl"
        with self.connection() as l: result_data = l.search_st(baseDN, ldap.SCOPE_BASE, timeout=1)
        if len(result_data) != 1: return None
        dn, attrs = result_data[0]
        return dn, attrs

    def by_email(self, email):
        """Opvragen (dn, attrs) van gebruiker met email"""
        baseDN = "ou=users,dc=jd,dc=nl"
        searchFilter = filter_format('(mail=%s)', (str(email),))
        with self.connection() as l: result_data = list(l.search_st(baseDN, ldap.SCOPE_ONELEVEL, searchFilter, timeout=1))
        return result_data

    def attributes(self, lidnummer):
        """Vraag emailadres en naam van lid met lidnummer op.
        Voorbeeld:
        res = attributes(lidnummer)
        if res != None: email, naam = res
        """
        res = self.by_lidnummer(lidnummer)
        if res == None: return None
        dn, attrs = res
        return attrs['mail'][0], attrs['sn'][0]

    def lidnummers(self, email):
        """Genereert alle lidnummers die bij een emailadres horen.
        Voorbeeld: for lidnummer, naam in lidnummers('email@adr.es'): ...
        """
        for dn, attrs in self.by_email(email): yield int(attrs['cn'][0]), attrs['sn'][0]

    def groups_of_dn(self, dn):
        """Generator van alle groepen (dn) waarvan de gebruiker lid is"""
        baseDN = "ou=groups,dc=jd,dc=nl"
        searchFilter = filter_format('(&(objectClass=groupOfNames)(member=%s))',(str(dn),))
        with self.connection() as l: result_data = list(l.search_st(baseDN, ldap.SCOPE_SUBTREE, searchFilter, timeout=3))
        for dn, attrs in result_data: yield attrs['cn'][0]
               
    def test_login(self, dn, password):
        """Probeert in te loggen met dn+password, True/False indien gelukt/mislukt"""
        try:
            testconn = ldap.initialize(settings.JANEUS_SERVER)
            testconn.simple_bind_s(dn, password)
            return True
        except ldap.INVALID_CREDENTIALS:
            return False

    def chpwd(self, uid, old, new):
        try:
            dn, attrs = self.by_uid(uid)
            conn = ldap.initialize(settings.JANEUS_SERVER)
            conn.simple_bind_s(dn, old)
            return conn.passwd_s(dn, old, new)
        except ldap.INVALID_CREDENTIALS:
            return None
