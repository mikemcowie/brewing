from brewing_incubator.testing.resource import BaseTestResourceCrud
from brewing_incubator.testing.user import BaseTestUser
from project_manager.app import Organization


class TestUser(BaseTestUser):
    pass


class TestOrganization(BaseTestResourceCrud[Organization]):
    pass
