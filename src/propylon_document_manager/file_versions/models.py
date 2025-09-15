import hashlib
from django.db import models, transaction
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.db.models import CharField, EmailField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    def _create_user(self, username, email, password, **extra_fields):
        if not username:
            raise ValueError("The given username must be set")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(username, email, password, **extra_fields)

class User(AbstractUser, PermissionsMixin):
    """
    Default custom user model for Propylon Document Manager.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    username = CharField(_("Name of User"), max_length=150, unique=True, null=True, blank=True)
    first_name = None  # type: ignore
    last_name = None  # type: ignore
    email = EmailField(_("email address"), unique=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("user:detail", kwargs={"pk": self.id})

def user_directory_path(instance, filename):
    # File will be uploaded to 
    # MEDIA_ROOT/uploads/user_<id>/<filename>
    user = instance.base_file.owner.username
    ver = instance.version_number
    basename, ext = instance.base_file.file_name.rsplit('.', 1)
    return f'uploads/user_{user}/{basename}_v{ver}.{ext}'


def _sha256_stream(fileobj, chunk_size=1024 * 1024):
    pos = fileobj.tell()
    fileobj.seek(0)
    h = hashlib.sha256()
    for chunk in iter(lambda: fileobj.read(chunk_size), b""):
        h.update(chunk)
    fileobj.seek(pos)
    return h.hexdigest()

class FileVersionManager(models.Manager):
    @transaction.atomic
    def create(self, *args, **kwargs):
        base_file = kwargs.get("base_file")

        if base_file is None:
            # Pop flat arguments used for BaseFile creation
            file_name = kwargs.pop("file_name", None)
            owner = kwargs.pop("owner", None)

            if not file_name or not owner:
                raise ValueError(
                    "Provide either 'base_file' or both 'file_name' and 'owner'."
                )

            # Create or get the BaseFile
            base_file, created = BaseFile.objects.get_or_create(
                owner=owner,
                file_name=file_name,
            )
            
        bf = BaseFile.objects.select_for_update().get(pk=base_file.pk)

        # 3) Enforce policy: version = current latest, then bump latest
        version_number = bf.latest_version_number
        kwargs["base_file"] = bf
        kwargs["version_number"] = version_number  # override any provided value

        obj = super().create(*args, **kwargs)

        bf.latest_version_number = version_number + 1
        bf.save(update_fields=["latest_version_number"])

        return obj

class BaseFile(models.Model):
    file_name = models.fields.CharField(max_length=512)
    latest_version_number = models.fields.IntegerField(default=0)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="base_files")

    def __str__(self):
        return f"{self.file_name} (v{self.latest_version_number}) by {self.owner.username}"

class FileVersion(models.Model):
    base_file = models.ForeignKey(BaseFile, on_delete=models.CASCADE, related_name="versions")
    file_content = models.FileField(upload_to=user_directory_path)
    version_number = models.fields.IntegerField()
    created_at = models.fields.DateTimeField(auto_now_add=True)
    file_hash = models.CharField(max_length=64, db_index=True, editable=False)
    updated_at = models.fields.DateTimeField(auto_now=True)

    objects = FileVersionManager()

    def __str__(self):
        return f"{self.base_file.file_name} v{self.version_number}"

    class Meta:
        unique_together = ('base_file', 'version_number')
        ordering = ['-version_number']

    @property
    def cas_path(self) -> str:
        # deterministic path for the blob (no extension, content-addressed)
        return f"cas/{self.content_hash[:2]}/{self.content_hash[2:4]}/{self.content_hash}"

    def _ensure_cas_storage(self):
        """
        Ensure the file is stored at its CAS path and self.file_content points to it.
        If a blob with the same hash already exists, we just repoint without writing again.
        """
        if default_storage.exists(self.cas_path):
            # De-dup: blob already present, just repoint
            self.file_content.name = self.cas_path
            return
        f = self.file_content
        if not f.closed:
            f.open()  # no-op if in-memory
        f.seek(0)
        # Save under CAS path
        default_storage.save(self.cas_path, ContentFile(f.read()))
        # Point the FileField to the CAS path (now content-addressed)
        self.file_content.name = self.cas_path

    def save(self, *args, **kwargs):
        # Require base_file
        if not self.base_file_id:
            raise ValueError("base_file must be provided when creating a FileVersion.")

        with transaction.atomic():
            # Compute content hash from current file object (new or existing)
            f = self.file_content
            if not f:
                raise ValueError("file_content is required.")
            if not f.closed:
                f.open()
            self.content_hash = _sha256_stream(f)
            # Move/point storage to CAS location (de-duplication)
            self._ensure_cas_storage()
            super().save(*args, **kwargs)