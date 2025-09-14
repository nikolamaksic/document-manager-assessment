from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from propylon_document_manager.file_versions.models import BaseFile, FileVersion


class FileVersionModelTests(TestCase):

    def test_create_file_version(self):
        """Test creating a file version."""
        user = get_user_model().objects.create_user(
            username="testuser123",
            email="testuser45@example.com",
            password="testpass123"
        )

        # Create the BaseFile
        # base_file = BaseFile.objects.create(
        #     latest_version_number=0
        # )

        # Simulate an uploaded file
        uploaded_file = SimpleUploadedFile(
            "test_file.txt", b"file content", content_type="text/plain"
        )
        # Create the FileVersion
        file_version = FileVersion.objects.create(
            file_name="test_file.txt",
            owner=user,
            file_content=uploaded_file,
            version_number=0
        )
        assert BaseFile.objects.count() == 1
        assert FileVersion.objects.count() == 1
        assert file_version.version_number == 0
        assert file_version.base_file.latest_version_number == 1
        assert file_version.base_file.owner == user
        assert file_version.base_file.file_name == "test_file.txt"

    def test_same_file_two_uploads_creates_new_version(self):
        user = get_user_model().objects.create_user(
            username="samefile_user",
            email="samefile_user@example.com",
            password="testpass123",
        )

        # First file version upload
        uploaded_v0 = SimpleUploadedFile("test_file.txt", b"content v0", content_type="text/plain")
        v0 = FileVersion.objects.create(
            file_name="test_file.txt",
            owner=user,
            file_content=uploaded_v0,
        )

        assert BaseFile.objects.count() == 1
        bf = BaseFile.objects.get(owner=user, file_name="test_file.txt")
        assert v0.base_file == bf
        assert v0.version_number == 0
        assert bf.latest_version_number == 1

        # Second upload (same name, same owner)
        uploaded_v1 = SimpleUploadedFile("test_file.txt", b"content v1", content_type="text/plain")
        v1 = FileVersion.objects.create(
            file_name="test_file.txt",
            owner=user,
            file_content=uploaded_v1,
        )

        bf.refresh_from_db()

        assert BaseFile.objects.count() == 1
        assert FileVersion.objects.count() == 2

        assert v1.base_file == bf == v0.base_file

        assert v0.version_number == 0
        assert v1.version_number == 1

        assert bf.latest_version_number == 2

        versions = list(bf.versions.all())
        assert versions[0].version_number == 1
        assert versions[1].version_number == 0
