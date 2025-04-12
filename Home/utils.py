from pymongo import MongoClient
from cryptography.fernet import Fernet

# Example key generation (store this key securely and use the same for encryption/decryption)
# key = Fernet.generate_key()

def get_db_handle(db_name, host, port, username, password):
    client = MongoClient(
        host=host,
        port=int(port),
        username=username,
        password=password
    )
    db_handle = client[db_name]
    return db_handle, client

def decrypt_employee_id(encrypted_id, key):
    """
    Decrypts the given encrypted employee id using Fernet symmetric encryption.
    Args:
        encrypted_id (str): The encrypted employee id.
        key (bytes): The secret key used for decryption.
    Returns:
        str: The decrypted employee id.
    """
    f = Fernet(key)
    decrypted = f.decrypt(encrypted_id.encode())
    return decrypted.decode()
