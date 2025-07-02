#!/usr/bin/env python3
"""
Encrypted Environment Manager for Pow_CRM
Handles encrypted .env files to avoid GitHub secrets limits
"""

import os
import base64
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

class EncryptedEnvManager:
    """Manages encrypted environment variables"""
    
    def __init__(self, password: str = None):
        """Initialize with encryption password"""
        self.password = password or os.getenv('ENV_ENCRYPTION_KEY')
        if not self.password:
            raise ValueError("Encryption password required (ENV_ENCRYPTION_KEY)")
        
        self.fernet = self._create_fernet(self.password)
    
    def _create_fernet(self, password: str) -> Fernet:
        """Create Fernet encryption object from password"""
        password_bytes = password.encode()
        salt = b'pow_crm_salt_2025'  # Fixed salt for consistency
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
        return Fernet(key)
    
    def encrypt_env_file(self, env_file_path: str, output_path: str = None) -> str:
        """Encrypt a .env file"""
        if not os.path.exists(env_file_path):
            raise FileNotFoundError(f"Environment file not found: {env_file_path}")
        
        # Read the .env file
        with open(env_file_path, 'r') as f:
            env_content = f.read()
        
        # Encrypt the content
        encrypted_content = self.fernet.encrypt(env_content.encode())
        
        # Encode as base64 for storage
        encoded_content = base64.b64encode(encrypted_content).decode()
        
        # Save to output file
        output_path = output_path or f"{env_file_path}.encrypted"
        with open(output_path, 'w') as f:
            f.write(encoded_content)
        
        logger.info(f"Environment file encrypted: {output_path}")
        return output_path
    
    def decrypt_env_file(self, encrypted_file_path: str, output_path: str = None) -> str:
        """Decrypt an encrypted .env file"""
        if not os.path.exists(encrypted_file_path):
            raise FileNotFoundError(f"Encrypted file not found: {encrypted_file_path}")
        
        # Read the encrypted file
        with open(encrypted_file_path, 'r') as f:
            encoded_content = f.read()
        
        # Decode from base64
        encrypted_content = base64.b64decode(encoded_content.encode())
        
        # Decrypt the content
        decrypted_content = self.fernet.decrypt(encrypted_content).decode()
        
        # Save to output file
        output_path = output_path or encrypted_file_path.replace('.encrypted', '')
        with open(output_path, 'w') as f:
            f.write(decrypted_content)
        
        logger.info(f"Environment file decrypted: {output_path}")
        return output_path
    
    def load_encrypted_env(self, encrypted_file_path: str) -> dict:
        """Load encrypted .env file directly into environment variables"""
        if not os.path.exists(encrypted_file_path):
            raise FileNotFoundError(f"Encrypted file not found: {encrypted_file_path}")
        
        # Read and decrypt
        with open(encrypted_file_path, 'r') as f:
            encoded_content = f.read()
        
        encrypted_content = base64.b64decode(encoded_content.encode())
        decrypted_content = self.fernet.decrypt(encrypted_content).decode()
        
        # Parse .env content
        env_vars = {}
        for line in decrypted_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
                # Also set in os.environ
                os.environ[key.strip()] = value.strip()
        
        logger.info(f"Loaded {len(env_vars)} environment variables")
        return env_vars
    
    def create_env_from_github_secrets(self, output_path: str = '.env') -> str:
        """Create .env file from current GitHub environment variables"""
        env_content = []
        
        # Supabase credentials
        env_content.append("# Supabase Configuration")
        env_content.append(f"SUPABASE_URL={os.getenv('SUPABASE_URL', '')}")
        env_content.append(f"SUPABASE_SERVICE_KEY={os.getenv('SUPABASE_SERVICE_KEY', '')}")
        env_content.append("")
        
        # All pool credentials
        pools = [
            'POWDIGITAL3', 'PNGMININGETH', 'PEDROETH', 'KENNDUNK', 'YZMINING',
            'SVJMINING', 'ZTUNEMINING', 'BMASTERMINING', 'ALLIN3', 'MACK81',
            'CANKANN2', 'PEDROMINING', 'VANMINING', 'LASVEGASMINING', 'CANKANN',
            'PNGMINING', 'RARCOA', 'SOLTERO', 'BILLMININGBR', 'POWDIGITAL2',
            'BLACKDAWN', 'MANGGORNMOO', 'LASVEGASMINING2', 'FIFTYSHADES', 'NSXR',
            'BLOCKWARESA', 'RARCOASA', 'VANMININGSA', 'BILLMININGSA', 'ALLIN2',
            'TYLERDSA', 'GOLDENDAWN', 'POWDIGITAL'
        ]
        
        env_content.append("# Pool Credentials")
        for pool in pools:
            access_key = os.getenv(f'{pool}_ACCESS_KEY', '')
            secret_key = os.getenv(f'{pool}_SECRET_KEY', '')
            user_id = os.getenv(f'{pool}_USER_ID', '')
            
            env_content.append(f"# {pool}")
            env_content.append(f"{pool}_ACCESS_KEY={access_key}")
            env_content.append(f"{pool}_SECRET_KEY={secret_key}")
            env_content.append(f"{pool}_USER_ID={user_id}")
            env_content.append("")
        
        # Write to file
        with open(output_path, 'w') as f:
            f.write('\n'.join(env_content))
        
        logger.info(f"Environment file created: {output_path}")
        return output_path

def main():
    """CLI interface for env manager"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python env_manager.py encrypt <env_file>")
        print("  python env_manager.py decrypt <encrypted_file>")
        print("  python env_manager.py create_from_github")
        return
    
    command = sys.argv[1]
    
    # Get encryption key
    encryption_key = os.getenv('ENV_ENCRYPTION_KEY')
    if not encryption_key:
        encryption_key = input("Enter encryption password: ")
    
    manager = EncryptedEnvManager(encryption_key)
    
    if command == 'encrypt':
        if len(sys.argv) < 3:
            print("Error: Please specify .env file to encrypt")
            return
        env_file = sys.argv[2]
        encrypted_file = manager.encrypt_env_file(env_file)
        print(f"Encrypted: {encrypted_file}")
    
    elif command == 'decrypt':
        if len(sys.argv) < 3:
            print("Error: Please specify encrypted file to decrypt")
            return
        encrypted_file = sys.argv[2]
        decrypted_file = manager.decrypt_env_file(encrypted_file)
        print(f"Decrypted: {decrypted_file}")
    
    elif command == 'create_from_github':
        env_file = manager.create_env_from_github_secrets()
        print(f"Created .env file: {env_file}")
        
        # Optionally encrypt it
        encrypt = input("Encrypt the .env file? (y/n): ").lower().startswith('y')
        if encrypt:
            encrypted_file = manager.encrypt_env_file(env_file)
            print(f"Encrypted: {encrypted_file}")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()

