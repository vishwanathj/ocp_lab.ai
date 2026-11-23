"""Fake credentials and a throwaway-repository helper for the secret-scan tests (issue #8).

Nothing here is a secret. Every token and pull secret is built at run time from random bytes, so the
test files hold no credential and the repository's own history scan never flags them.
"""

import base64
import json
import secrets
import subprocess
import uuid

GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
    "HOME": "/tmp", "PATH": "/usr/local/bin:/usr/bin:/bin",
}


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def fake_offline_token():
    """A random JWT shaped like a Red Hat offline token; it signs nothing and opens nothing.

    Any JWT also matches gitleaks' built-in `jwt` rule, so a test that only checks "blocked" can't
    tell whether the project's own `offline-token` rule works. The tests check the rule ID too.
    """
    header = {"alg": "HS512", "typ": "JWT", "kid": str(uuid.uuid4())}
    payload = {"typ": "Offline", "jti": str(uuid.uuid4()), "sub": secrets.token_hex(16)}
    return ".".join([b64url(json.dumps(header).encode()), b64url(json.dumps(payload).encode()),
                     b64url(secrets.token_bytes(64))])


def fake_pull_secret():
    """A random pull secret: registry logins whose `auth` is base64 of user:password."""
    auth = base64.b64encode(f"user:{secrets.token_urlsafe(48)}".encode()).decode()
    return json.dumps({"auths": {"cloud.openshift.com": {"auth": auth, "email": "user@example.com"}}})


def git(repo, *args, env=GIT_ENV):
    subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)
