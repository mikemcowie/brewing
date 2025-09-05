from __future__ import annotations


class Endpoints:
    USERS_REGISTER = "/users/register"
    USERS_LOGIN = "/users/login"
    USERS_PROFILE = "/users/me/profile"
    ORGANIZATIONS = "/organizations/"
    ORGANIZATIONS_ONE = "/organizations/{organization_id}"
    ORGANIZATIONS_ONE_ACCESS = "/organizations/{organization_id}/access/"
    ORGANIZATIONS_ONE_ACCESS_ONE = "/organizations/{organization_id}/access/{user_id}"
