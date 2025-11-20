from django.test import TestCase

# Create your tests here.

# Core app has no models, so minimal tests
class CoreTestCase(TestCase):
    def test_core_app_exists(self):
        """Test that core app is properly configured"""
        # This is a placeholder test since core app has no models
        self.assertTrue(True)
