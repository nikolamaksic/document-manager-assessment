from django.core.management.base import BaseCommand, CommandError
from propylon_document_manager.file_versions.models import FileVersion
from django.core.files.uploadedfile import SimpleUploadedFile

file_versions = [
    'bill_document',
    'amendment_document',
    'act_document',
    'statute_document',
]

class Command(BaseCommand):
    help = "Load basic file version fixtures"

    def handle(self, *args, **options):
        user = get_user_model().objects.create_user(
            username="testuser123",
            email="testuser45@example.com",
            password="testpass123"
        )
        for file_name in file_versions:
            
            uploaded_file = SimpleUploadedFile(
                f"{file_name}.txt", b"file content", content_type="text/plain"
            )
            FileVersion.objects.create(
                file_name=f"{file_name}.txt",
                owner=user,
                file_content=uploaded_file,
            )

        self.stdout.write(
            self.style.SUCCESS('Successfully created %s file versions' % len(file_versions))
        )
