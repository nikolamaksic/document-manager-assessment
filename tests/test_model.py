from django.test import TestCase
from django.contrib.auth import get_user_model

class UserModelTests(TestCase):

    def test_create_user_with_username_successful(self):
        """Test creating a user with a username is successful."""
        username= 'testuser'
        email = 'test@example.com'
        password = 'testpass123'
        user = get_user_model().objects.create_user(
            username=username,
            email=email,
            password=password
        )
        self.assertEqual(user.email, email)
        self.assertEqual(user.username, username)
        self.assertTrue(user.check_password(password))

    def test_new_user_without_username_raises_error(self):
        """Test creating user without username raises error."""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', "something@example.com" 'testpass123')

    def test_create_superuser(self):
        """Test creating a superuser."""
        user = get_user_model().objects.create_superuser(
            'testsuperuser',
            'test@example.com',
            'testpass123',)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
