import uuid
from pathlib import Path

from flask import abort

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB


def is_allowed_file(filename):
    """Check if file has an allowed image extension."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def validate_and_save_upload(file, upload_folder, allowed_extensions=None, max_size=MAX_FILE_SIZE):
    """Validate and safely persist an uploaded file.

    - Rejects disallowed extensions (.exe, .php, etc.) with HTTP 400.
    - Rejects files larger than max_size (2MB) with HTTP 400.
    - Generates a cryptographically random filename (uuid4) to prevent path traversal.
    """
    if file is None or file.filename == '':
        abort(400, description="No file selected for upload.")

    if allowed_extensions is None:
        allowed_extensions = ALLOWED_EXTENSIONS

    original_filename = file.filename
    if '.' not in original_filename:
        abort(400, description="Invalid file: missing file extension.")

    ext = original_filename.rsplit('.', 1)[1].lower()
    if ext not in allowed_extensions:
        abort(
            400,
            description=f"File extension '.{ext}' is not permitted. Allowed: {', '.join(sorted(allowed_extensions))}.",
        )

    # Check file size (read into memory or check stream)
    file_bytes = file.read()
    if len(file_bytes) > max_size:
        abort(
            400,
            description=f"File exceeds maximum allowed size of {max_size // (1024 * 1024)}MB.",
        )

    if len(file_bytes) == 0:
        abort(400, description="Uploaded file is empty.")

    # Create destination directory if needed
    dest_dir = Path(upload_folder)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Generate collision-free sanitized filename
    secure_name = f"{uuid.uuid4().hex}.{ext}"
    target_path = dest_dir / secure_name

    with open(target_path, 'wb') as f:
        f.write(file_bytes)

    return secure_name
