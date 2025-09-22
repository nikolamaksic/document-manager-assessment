from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from propylon_document_manager.file_versions.models import BaseFile, FileVersion


class FileVersionModelTests(TestCase):

    def test_create_file_version(self):
        """Test creating a file version."""
        user = get_user_model().objects.create_user(
            username="testuser123",
            email="testuser45@example.com",
            password="testpass123"
        )

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

    def test_file_hash_and_cas_path(self):
        u = get_user_model().objects.create_user("u1", "u1@example.com", "p")
        fv = FileVersion.objects.create(
            file_name="a.txt",
            owner=u,
            file_content=SimpleUploadedFile("a.txt", b"abc", content_type="text/plain"),
        )
        self.assertTrue(fv.file_hash)
        self.assertTrue(fv.file_content.name.startswith("cas/"))
        self.assertTrue(default_storage.exists(fv.file_content.name))

    def test_cas_dedup_same_content(self):
        u = get_user_model().objects.create_user("u2", "u2@example.com", "p")
        data = b"same"
        v0 = FileVersion.objects.create(file_name="x.txt", owner=u,
                                        file_content=SimpleUploadedFile("x.txt", data))
        v1 = FileVersion.objects.create(file_name="x.txt", owner=u,
                                        file_content=SimpleUploadedFile("x.txt", data))
        
        bf = v1.base_file
        self.assertEqual(v0.file_hash, v1.file_hash)
        self.assertEqual(v0.file_content.name, v1.file_content.name)
        self.assertEqual(bf.latest_version_number, 2)

    def test_latest_version_number_increments(self):
        u = get_user_model().objects.create_user("u3", "u3@example.com", "p")
        v0 = FileVersion.objects.create(file_name="test.txt", owner=u,
                                        file_content=SimpleUploadedFile("b0.txt", b"1"))
        v1 = FileVersion.objects.create(file_name="test.txt", owner=u,
                                        file_content=SimpleUploadedFile("b1.txt", b"2"))
        v2 = FileVersion.objects.create(file_name="test.txt", owner=u,
                                        file_content=SimpleUploadedFile("b2.txt", b"3"))
        
        bf = v2.base_file
        self.assertEqual([v.version_number for v in bf.versions.all()], [2, 1, 0])
        self.assertEqual(bf.latest_version_number, 3)

    def test_different_content_different_hash(self):
        u = get_user_model().objects.create_user("u4", "u4@example.com", "p")
        v0 = FileVersion.objects.create(file_name="c.txt", owner=u,
                                        file_content=SimpleUploadedFile("c0.txt", b"aaa"))
        v1 = FileVersion.objects.create(file_name="c.txt", owner=u,
                                        file_content=SimpleUploadedFile("c1.txt", b"bbb"))
        self.assertNotEqual(v0.file_hash, v1.file_hash)
        self.assertNotEqual(v0.file_content.name, v1.file_content.name)

    def test_multiple_files_create_distinct_basefiles(self):
        u = get_user_model().objects.create_user("u5", "u5@example.com", "p")
        v0 = FileVersion.objects.create(file_name="f1.txt", owner=u,
                                        file_content=SimpleUploadedFile("f1.txt", b"1"))
        v1 = FileVersion.objects.create(file_name="f2.txt", owner=u,
                                        file_content=SimpleUploadedFile("f2.txt", b"2"))
        self.assertNotEqual(v0.base_file_id, v1.base_file_id)
        self.assertEqual(BaseFile.objects.filter(owner=u).count(), 2)
