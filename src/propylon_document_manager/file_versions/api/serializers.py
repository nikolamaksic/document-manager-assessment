# propylon_document_manager/file_versions/api/serializers.py
from rest_framework import serializers
from ..models import BaseFile, FileVersion

class BaseFileSerializer(serializers.ModelSerializer):
    latest_revision_number = serializers.SerializerMethodField()

    class Meta:
        model = BaseFile
        fields = [
            "id",
            "file_name",
            "latest_version_number",
            "latest_revision_number",
        ]

    def get_document_url(self, obj: BaseFile) -> str:
        # Base URL always serves the latest version
        return _normalize_doc_path(obj.file_name)

    def get_latest_revision_number(self, obj: BaseFile) -> int:
        # latest_version_number is the "next" number; latest actual stored is -1
        return max(0, obj.latest_version_number - 1)


class FileVersionSerializer(serializers.ModelSerializer):
    # Read helpers
    file_version_url = serializers.SerializerMethodField()
    file_path = serializers.SerializerMethodField()
    # When reading, pull from BaseFile; when writing, accept plain text
    file_name = serializers.CharField(source="base_file.file_name", required=True, write_only=False)
    # Accept the uploaded file for creation
    file = serializers.FileField(source="file_content", write_only=True)

    class Meta:
        model = FileVersion
        # include all fields you want to expose
        fields = [
            "id",
            "file_name",
            "file",
            "version_number",
            "created_at",
            "updated_at",
            "file_hash",
            "file_version_url",
            "file_path",
        ]
        read_only_fields = (
            "id",
            "version_number",
            "created_at",
            "updated_at",
            "file_hash",
            "file_version_url",
            "file_path",
        )

    def get_file_version_url(self, obj):
        # URL for this exact revision
        return f"{obj.base_file.file_name}?revision={obj.version_number}"

    def get_file_path(self, obj):
        return obj.file_content.name

    def create(self, validated_data):
        """
        Create a new FileVersion using the manager’s custom create().
        The manager expects:
            - file_name  (logical path)
            - owner      (the authenticated user)
            - file_content
        """
        # Pop values prepared by DRF
        base_file_data = validated_data.pop("base_file", {})
        file_name = base_file_data.get("file_name")
        file_content = validated_data.pop("file_content", None)

        if not file_name or not file_content:
            raise serializers.ValidationError(
                {"detail": "Both 'file_name' and 'file' are required."}
            )

        user = self.context["request"].user

        # Use custom manager to handle version bump + BaseFile creation
        return FileVersion.objects.create(
            file_content=file_content,
            file_name=file_name,
            owner=user,
            **validated_data,
        )

def _normalize_doc_path(p: str) -> str:
    p = (p or "").strip()
    if not p.startswith("/"):
        p = "/" + p
    return p
