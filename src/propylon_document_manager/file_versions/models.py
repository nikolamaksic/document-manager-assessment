from django.db import models, transaction
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
    basename, ext = filename.rsplit('.', 1)
    return f'uploads/user_{user}/{basename}_v{ver}.{ext}'

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
    updated_at = models.fields.DateTimeField(auto_now=True)

    objects = FileVersionManager()

    def __str__(self):
        return f"{self.base_file.file_name} v{self.version_number}"

    class Meta:
        unique_together = ('base_file', 'version_number')
        ordering = ['-version_number']
