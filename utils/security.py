from cryptography.fernet import Fernet
import os
import json
import yaml
from typing import Dict, Any
from pathlib import Path
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class SecurityManager:
    def __init__(self, key_file: str = ".key"):
        self.key_file = key_file
        self.key = self._load_or_create_key()
        self.fernet = Fernet(self.key)
    
    def _load_or_create_key(self) -> bytes:
        """Load existing key or create a new one."""
        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
            return key
    
    def encrypt_value(self, value: str) -> str:
        """Encrypt a string value."""
        return self.fernet.encrypt(value.encode()).decode()
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt an encrypted string value."""
        return self.fernet.decrypt(encrypted_value.encode()).decode()
    
    def secure_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive configuration values."""
        secure_conf = config.copy()
        
        # Encrypt exchange API credentials
        if 'exchange' in secure_conf:
            if 'api_key' in secure_conf['exchange']:
                secure_conf['exchange']['api_key'] = self.encrypt_value(secure_conf['exchange']['api_key'])
            if 'api_secret' in secure_conf['exchange']:
                secure_conf['exchange']['api_secret'] = self.encrypt_value(secure_conf['exchange']['api_secret'])
        
        # Encrypt social media API credentials
        for platform in ['twitter', 'reddit', 'news']:
            if platform in secure_conf:
                for key in secure_conf[platform]:
                    if 'key' in key or 'secret' in key or 'token' in key:
                        secure_conf[platform][key] = self.encrypt_value(secure_conf[platform][key])
        
        # Encrypt database credentials
        if 'data_collection' in secure_conf and 'storage' in secure_conf['data_collection']:
            db = secure_conf['data_collection']['storage'].get('database', {})
            if 'password' in db:
                secure_conf['data_collection']['storage']['database']['password'] = \
                    self.encrypt_value(db['password'])
        
        return secure_conf
    
    def decrypt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive configuration values."""
        decrypted_conf = config.copy()
        
        # Decrypt exchange API credentials
        if 'exchange' in decrypted_conf:
            if 'api_key' in decrypted_conf['exchange'] and decrypted_conf['exchange']['api_key']:
                decrypted_conf['exchange']['api_key'] = self.decrypt_value(decrypted_conf['exchange']['api_key'])
            if 'api_secret' in decrypted_conf['exchange'] and decrypted_conf['exchange']['api_secret']:
                decrypted_conf['exchange']['api_secret'] = self.decrypt_value(decrypted_conf['exchange']['api_secret'])
        
        # Decrypt social media API credentials
        for platform in ['twitter', 'reddit', 'news']:
            if platform in decrypted_conf:
                for key in decrypted_conf[platform]:
                    if ('key' in key or 'secret' in key or 'token' in key) and decrypted_conf[platform][key]:
                        decrypted_conf[platform][key] = self.decrypt_value(decrypted_conf[platform][key])
        
        # Decrypt database credentials
        if 'data_collection' in decrypted_conf and 'storage' in decrypted_conf['data_collection']:
            db = decrypted_conf['data_collection']['storage'].get('database', {})
            if 'password' in db and db['password']:
                decrypted_conf['data_collection']['storage']['database']['password'] = \
                    self.decrypt_value(db['password'])
        
        return decrypted_conf

    @staticmethod
    def generate_key_from_password(password: str, salt: bytes = None) -> bytes:
        """Generate a Fernet key from a password."""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key 