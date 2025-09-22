from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

CREATE_USER_URL = reverse('users:create')
USER_TOKEN_URL = reverse('users:token')
USER_PROFILE_URL = reverse('users:profile')

def create_user(**params):
    """Helper function to create a new user."""
    return get_user_model().objects.create_user(**params)

class PublicUserApiTests(TestCase):
    """Test the users API (public)."""

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """Test creating a user is successful."""
        payload = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        res = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(username=payload['username'])
        self.assertTrue(user.check_password(payload['password']))
        # check password is not returned in response
        self.assertNotIn('password', res.data)
    
    def test_user_with_email_exists_error(self):
        """Test creating a user that already exists fails."""
        payload = {
            'username': 'testuser',
            'email': 'test@email.example',
            'password': 'testpass123'
        }
        create_user(**payload)
        res = self.client.post(CREATE_USER_URL, payload)

    def test_password_too_short_error(self):
        """Test creating a user with a too short password fails."""
        payload = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'pw'
        }
        res = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            username=payload['username']
        ).exists()
        self.assertFalse(user_exists)



    def test_create_user_missing_field(self):
        """Test creating a user with missing field fails."""
        payload = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        res = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_for_user(self):
        """Test that a token is created for the user."""
        payload = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        create_user(**payload)
        res = self.client.post(USER_TOKEN_URL, {
            'username': payload['username'],
            'email': payload['email'],
            'password': payload['password']
        })
        self.assertIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
    
    def test_create_token_invalid_credentials(self):
        """Test that token is not created if invalid credentials are given."""
        create_user(
            username='testuser',
            password='goodpass123', 
            email='test@example.com')
        payload = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'badpass123'}
        res = self.client.post(USER_TOKEN_URL, payload)
        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_no_user(self):
        """Test that token is not created if user doesn't exist."""
        payload = {
            'username': 'testuser',
            'email': 'test123@example.com',
            'password': 'testpass123'}
        res = self.client.post(USER_TOKEN_URL, payload)
        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_create_token_blank_password(self):
        """Test that token is not created if password is blank."""
        payload = {
            'username':'testuser',
            'password':'goodpass123',
            'email':"test@example.com"}
        res = self.client.post(USER_TOKEN_URL, payload)
        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retreive_user_unauthorized(self):
        """Test that authentication is required for users."""
        res = self.client.get(USER_PROFILE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateUserApiTests(TestCase):
    """Test API requests that require authentication."""

    def setUp(self):
        self.user = create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def test_retrieve_profile_success(self):
        """Test retrieving profile for logged in user."""
        res = self.client.get(USER_PROFILE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {
            'username': self.user.username,
            'email': self.user.email
        })
    
    def test_update_user_profile(self):
        """Test updating the user profile for authenticated user."""
        payload = {'username': 'updateduser', 'password': 'newpass123'}
        res = self.client.patch(USER_PROFILE_URL, payload)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, payload['username'])
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
