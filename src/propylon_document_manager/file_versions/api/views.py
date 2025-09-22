# propylon_document_manager/file_versions/api/views.py
from urllib.parse import unquote

from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from rest_framework.decorators import action
from rest_framework import status, permissions, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from django.db.models import Max

from ..models import FileVersion, BaseFile
from .serializers import FileVersionSerializer


def _normalize_doc_path(p: str) -> str:
    p = (p or "").strip()
    if not p.startswith("/"):
        p = "/" + p
    # Optional: enforce prefix, forbid "..", etc.
    if p[-1] == "/":
        p = p[:-1]
    return p


from difflib import HtmlDiff
import io

def _read_text_or_none(fh):
    data = fh.read()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None

def _get_revision(bf, rev_str):
    try:
        rev = int(rev_str)
    except (TypeError, ValueError):
        return None
    return bf.versions.filter(version_number=rev).first()


class FileVersionViewSet(viewsets.ModelViewSet):
    
    serializer_class = FileVersionSerializer
    queryset = FileVersion.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def list_available_files(self, request):
        qs = (FileVersion.objects
            .filter(base_file__owner=request.user)
            .select_related("base_file")
            .order_by("base_file__file_name", "-version_number"))
        ser = FileVersionSerializer(qs, many=True, context={"request": request})
        return Response(ser.data)


    def diff_file_versions(self, request, path=None):
        """
        GET /documents/<file-path>/diff?from=<int>&to=<int>
        Returns an HTML side-by-side diff of the file *contents only*
        for two UTF-8 text versions.
        """
        logical_path = _normalize_doc_path("/documents/" + unquote(path))
        bf = get_object_or_404(BaseFile, file_name=logical_path, owner=request.user)

        # Validate query params
        rev_from = request.query_params.get("from")
        rev_to   = request.query_params.get("to")
        if rev_from is None or rev_to is None:
            return Response({"detail": "Provide ?from=<int>&to=<int>."}, status=400)

        fv_a = _get_revision(bf, rev_from)
        fv_b = _get_revision(bf, rev_to)
        if not fv_a or not fv_b:
            return Response({"detail": "One or both revisions not found."}, status=404)

        # Read *only* the raw contents
        with fv_a.file_content.open("rb") as fa, fv_b.file_content.open("rb") as fb:
            try:
                text_a = fa.read().decode("utf-8")
                text_b = fb.read().decode("utf-8")
            except UnicodeDecodeError:
                return Response(
                    {"detail": "Diff only supported for UTF-8 text files."},
                    status=415
                )

        # Build HTML diff of contents only
        html = HtmlDiff(wrapcolumn=800).make_file(
            text_a.splitlines(),
            text_b.splitlines(),
            fromdesc=f"Revision {fv_a.version_number}",
            todesc=f"Revision {fv_b.version_number}",
            context=False,
        )
        return HttpResponse(html, content_type="text/html")

    @transaction.atomic
    def create_document_version(self, request, path=None):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "'file' is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        logical_path = _normalize_doc_path("/documents/" + unquote(path))
        fv = FileVersion.objects.create(
            file_content=uploaded,
            file_name=logical_path,
            owner=request.user,
        )

        return Response(
            {
                "id": fv.id,
                "file_name": logical_path,
                "version_number": fv.version_number,
                "document_url": logical_path,
                "file_version_url": f"{logical_path}?revision={fv.version_number}",
                "created_at": fv.created_at,
            },
            status=status.HTTP_201_CREATED,
        )

    def retrieve_document(self, request, path=None):
        logical_path = _normalize_doc_path("/documents/" + unquote(path))
        bf = get_object_or_404(BaseFile, file_name=logical_path, owner=request.user)

        rev = request.query_params.get("revision")
        if rev is not None:
            try:
                rev_num = int(rev)
            except (TypeError, ValueError):
                raise Http404("Invalid revision")
            fv = bf.versions.filter(version_number=rev_num).first()
        else:
            fv = bf.versions.first()

        if not fv or not fv.file_content:
            raise Http404("Requested revision not found")

        return FileResponse(fv.file_content.open("rb"), as_attachment=False)

    @transaction.atomic
    def delete_document_version(self, request, path=None):
        logical_path = _normalize_doc_path("/documents/" + unquote(path))
        bf = get_object_or_404(BaseFile, file_name=logical_path, owner=request.user)

        # choose which revision to delete
        rev = request.query_params.get("revision")
        if rev is not None:
            try:
                rev_num = int(rev)
            except (TypeError, ValueError):
                raise Http404("Invalid revision")
            fv = bf.versions.filter(version_number=rev_num).first()
        else:
            fv = bf.versions.first()

        if not fv:
            raise Http404("Requested revision not found")

        hash_to_check = fv.file_hash
        cas_name = fv.file_content.name
        # delete the chosen version
        fv.delete()
        # if no more versions remain for this BaseFile, delete the BaseFile too
        remaining_qs = bf.versions.all()
        if not remaining_qs.exists():
            bf.delete()
        else:
            # keep latest_version_number = next free (max + 1)
            max_ver = remaining_qs.aggregate(Max("version_number"))["version_number__max"]
            bf.latest_version_number = (max_ver + 1) if max_ver is not None else 0
            bf.save(update_fields=["latest_version_number"])
        # Delete CAS blob if no more FileVersions reference it
        if hash_to_check:
            still_used = FileVersion.objects.filter(file_hash=hash_to_check).exists()
            if (not still_used) and cas_name:
                try:
                    if default_storage.exists(cas_name):
                        default_storage.delete(cas_name)
                except Exception as e:
                    print(f"Warning: failed to delete CAS file {cas_name}: {e}")
                    pass

        return Response(status=status.HTTP_204_NO_CONTENT)
