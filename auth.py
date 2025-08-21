from passlib.hash import bcrypt

import bcrypt

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    # Convert password to bytes
    password_bytes = password.encode('utf-8')
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    try:
        # Convert to bytes
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed.encode('utf-8')
        # Check password
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False