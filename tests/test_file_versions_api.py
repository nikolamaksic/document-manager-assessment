from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from propylon_document_manager.file_versions.api.serializers import FileVersionSerializer

from propylon_document_manager.file_versions.models import FileVersion

def file_version_url(file_path, version_number=None):
    if version_number is None:
        return f"{file_path}"
    return f"{file_path}?revision={version_number}"

FILE_VERSION_URL = reverse("api:fileversion-list")

def create_file_version(user, **params):
    """Helper function to create a FileVersion instance."""
    f_name = params.get("file_name", "test_file.txt")
    uploaded_file = SimpleUploadedFile(
            f_name, b"file content", content_type="text/plain"
    )
    defaults = {
        "version_number": 0,
        "file_content": uploaded_file,
        "file_name": f_name,
        "owner": user,
    }
    defaults.update(params)
    return FileVersion.objects.create(**defaults)

class PublicFileVersionAPITests(TestCase):
    """Test unauthenticated file version API access."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required to access the endpoint."""
        res = self.client.get(reverse("api:fileversion-list"))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
    
class PrivateFileVersionAPITests(TestCase):
    """Test authenticated file version API access."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        # self.file_version = create_file_version(user=self.user)

    def test_retrieve_file_versions(self):
        """Test retrieving a list of file versions."""
        create_file_version(user=self.user)
        create_file_version(user=self.user, version_number=1, file_name="another_file.txt")

        res = self.client.get(FILE_VERSION_URL)
        file_versions = FileVersion.objects.all().order_by("-id")
        serializer = FileVersionSerializer(file_versions, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)