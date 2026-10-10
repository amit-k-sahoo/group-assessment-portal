"""Built-in admin account. Stores only a salted PBKDF2 hash, never the password.

An [admin] block in the app's Secrets (login_id + password) overrides this if present.
To change the password: python admin_config.py "new password"  (paste the output over the values below).
"""

import hashlib
import hmac
import secrets
import sys

LOGIN_ID = "portal.admin"
SALT = "dcbdaf333acec994aea2deea74bf3988"
ITERATIONS = 600000
PW_HASH = "9b9f5b88e11c958a1d75140bd1049206d1ab48d849578fd7b626059ef5e7f627"


def check(password: str) -> bool:
    got = hashlib.pbkdf2_hmac("sha256", password.strip().encode(), bytes.fromhex(SALT), ITERATIONS).hex()
    return hmac.compare_digest(got, PW_HASH)


if __name__ == "__main__":
    salt = secrets.token_bytes(16)
    print(f'SALT = "{salt.hex()}"')
    print(f'PW_HASH = "{hashlib.pbkdf2_hmac("sha256", sys.argv[1].encode(), salt, ITERATIONS).hex()}"')
