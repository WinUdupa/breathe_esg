import hashlib
import os
from django.conf import settings
from .models import IngestionBatch
from apps.parsers.sap_parser import parse_sap
from apps.parsers.utility_parser import parse_utility
from apps.parsers.travel_parser import parse_travel
from apps.normalization.pipeline import run_normalization


def compute_hash(file_bytes):
    return hashlib.sha256(file_bytes).hexdigest()


def save_file(file_bytes, client_id, batch_id, filename):
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', str(client_id))
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(filename)[1]
    file_path = os.path.join(upload_dir, f"{batch_id}{ext}")
    with open(file_path, 'wb') as f:
        f.write(file_bytes)
    return file_path


def run_ingestion_pipeline(batch, file_bytes, client):
    parser_map = {
        'SAP': parse_sap,
        'UTILITY': parse_utility,
        'TRAVEL': parse_travel,
    }
    parser = parser_map.get(batch.source_type)
    if not parser:
        batch.status = 'FAILED'
        batch.error_log = [f"Unknown source type: {batch.source_type}"]
        batch.save()
        return

    success = parser(batch, file_bytes)
    if not success:
        return

    run_normalization(batch, client)
    batch.status = 'PENDING_REVIEW'
    batch.save()
