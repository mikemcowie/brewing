from cauldron.testing.resource import BaseTestResourceCrud
from cauldron.testing.user import BaseTestUser
from project_manager.app import Organization


class TestUser(BaseTestUser):
    pass


class TestOrganization(BaseTestResourceCrud[Organization]):
    pass
