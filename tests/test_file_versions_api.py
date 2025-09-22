from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from propylon_document_manager.file_versions.models import BaseFile, FileVersion
from propylon_document_manager.file_versions.api.serializers import FileVersionSerializer

from propylon_document_manager.file_versions.models import FileVersion

def doc_url(path: str) -> str:
    # name="documents" in your api_router
    return reverse("file_versions:documents", kwargs={"path": path})

def diff_url(path: str) -> str:
    return reverse("file_versions:documents-diff", kwargs={"path": path})

def mine_url() -> str:
    return reverse("file_versions:documents-mine")


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

    def test_auth_required_on_documents(self):
        res = self.client.get(doc_url("any.txt"))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_on_mine(self):
        res = self.client.get(mine_url())
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_on_diff(self):
        res = self.client.get(diff_url("any.txt"))
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

    
    def test_retrieve_latest_and_specific(self):
        file_path = "/documents/report.txt"
        # v0
        create_file_version(
            self.user,
            file_name=file_path,
            file_content=SimpleUploadedFile("v0.txt", b"# v0"),
        )
        # v1
        create_file_version(
            self.user,
            file_name=file_path,
            file_content=SimpleUploadedFile("v1.txt", b"# v1 UPDATED"),
        )

        # GET latest
        r_latest = self.client.get(doc_url("report.txt"))
        self.assertEqual(r_latest.status_code, status.HTTP_200_OK)
        self.assertTrue(r_latest.has_header("Content-Type"))

        # GET specific revision
        r_v0 = self.client.get(doc_url("report.txt") + "?revision=0")
        self.assertEqual(r_v0.status_code, status.HTTP_200_OK)

        bf = BaseFile.objects.get(owner=self.user, file_name=file_path)
        self.assertEqual(bf.versions.count(), 2)
        self.assertEqual(bf.latest_version_number, 2)

    def test_get_404_when_document_missing(self):
        res = self.client.get(doc_url("nope.txt"))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_404_when_revision_invalid(self):
        file_path = "/documents/num.txt"
        create_file_version(
            self.user, file_name=file_path, file_content=SimpleUploadedFile("v0.txt", b"v0")
        )
        res = self.client.get(doc_url("num.txt") + "?revision=not-a-number")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_404_when_revision_is_missing(self):
        file_path = "/documents/num.txt"
        create_file_version(
            self.user, file_name=file_path, file_content=SimpleUploadedFile("v0.txt", b"v0")
        )
        res = self.client.get(doc_url("num.txt") + "?revision=2")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_diff_html_between_two_revisions(self):
        file_path = "/documents/diffme.txt"
        create_file_version(self.user, file_name=file_path, file_content=SimpleUploadedFile("v0.txt", b"line1\nline2\nsame\n"))
        create_file_version(self.user, file_name=file_path, file_content=SimpleUploadedFile("v1.txt", b"line1\nLINE2 CHANGED\nsame\nADDED\n"))

        res = self.client.get(diff_url("diffme.txt") + "?from=0&to=1")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res["Content-Type"].startswith("text/html"))
        body = res.content.decode("utf-8")
        self.assertIn("Revision 0", body)
        self.assertIn("Revision 1", body)


    def test_user_cannot_access_another_users_file(self):
        
        # Create sedond user and client
        user2 = get_user_model().objects.create_user(
            username="testuser2",
            email="test2@example.com",
            password="testpass1234")
        client2 = APIClient()
        client2.force_authenticate(user2)

        logical_path = "/documents/secret.txt"
        create_file_version(
            self.user,
            file_name=logical_path,
            file_content=SimpleUploadedFile("v0.txt", b"top secret", content_type="text/plain"),
        )

        res = client2.get(doc_url("secret.txt"))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        res_mine = client2.get(mine_url())
        self.assertEqual(res_mine.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_mine.json()), 0)

        res_client = self.client.get(doc_url("secret.txt"))
        self.assertEqual(res_client.status_code, status.HTTP_200_OK)

