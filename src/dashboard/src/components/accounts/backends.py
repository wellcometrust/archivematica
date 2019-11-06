import json
import re

from django.conf import settings
from django.dispatch import receiver
from django_auth_ldap.backend import LDAPBackend, populate_user
from josepy.jws import JWS
from shibboleth.backends import ShibbolethRemoteUserBackend
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from components.helpers import generate_api_key


class CustomShibbolethRemoteUserBackend(ShibbolethRemoteUserBackend):
    def configure_user(self, user):
        generate_api_key(user)
        return user


class CustomLDAPBackend(LDAPBackend):
    """Customize LDAP config."""

    def __init__(self):
        super(CustomLDAPBackend, self).__init__()
        self._username_suffix = settings.AUTH_LDAP_USERNAME_SUFFIX

    def ldap_to_django_username(self, username):
        # Replaces user creation in get_ldap_users
        return re.sub(self._username_suffix + "$", "", username)

    def django_to_ldap_username(self, username):
        # Replaces user creation in get_ldap_users
        return username + self._username_suffix


@receiver(populate_user)
def ldap_populate_user(sender, user, ldap_user, **kwargs):
    if user.pk is None:
        user.save()
        generate_api_key(user)


class CustomOIDCBackend(OIDCAuthenticationBackend):
    """
    Provide OpenID Connect authentication
    """

    def get_userinfo(self, access_token, id_token, verified_id):
        """
        Extract user details from JSON web tokens
        These map to fields on the user field.
        """
        id_info = json.loads(JWS.from_compact(id_token).payload.decode("utf-8"))
        access_info = json.loads(JWS.from_compact(access_token).payload.decode("utf-8"))

        info = {}

        for oidc_attr, user_attr in settings.OIDC_ACCESS_ATTRIBUTE_MAP.items():
            assert user_attr not in info
            info[user_attr] = access_info[oidc_attr]

        for oidc_attr, user_attr in settings.OIDC_ID_ATTRIBUTE_MAP.items():
            assert user_attr not in info
            info[user_attr] = id_info[oidc_attr]

        return info

    def create_user(self, user_info):
        user = super(CustomOIDCBackend, self).create_user(user_info)
        for attr, value in user_info.items():
            setattr(user, attr, value)
        user.save()
        generate_api_key(user)
        return user
