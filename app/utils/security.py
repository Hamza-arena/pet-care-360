from urllib.parse import urlsplit

from flask import request


def is_safe_url(target: str | None) -> bool:
    """Validate that the redirect target is local to the application host.

    Prevents Open Redirect vulnerabilities (CWE-601).
    """
    if not target or not isinstance(target, str):
        return False

    # Prevent control characters and whitespaces
    target = target.strip()
    if not target:
        return False

    # Prevent protocol-relative URL bypasses e.g. "//evil.com"
    if target.startswith('//'):
        return False

    # Prevent backslash bypass tricks e.g. "/\\evil.com" or "\\evil.com"
    if '\\' in target:
        return False

    ref_url = urlsplit(request.host_url)
    test_url = urlsplit(target)

    # Disallow schemes other than http/https or empty (relative paths)
    if test_url.scheme and test_url.scheme not in ('http', 'https'):
        return False

    # If netloc is present, it must strictly match the current host
    if test_url.netloc and test_url.netloc != ref_url.netloc:
        return False

    # Must start with '/' to be an internal application path
    return target.startswith('/')
