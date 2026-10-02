"""
Cryptographic Non-Repudiation Signature Engine
Conforms to IEEE 1016-2009 SDD §5.3 and SRS §6.3, §7.2.
Provides Canonical JSON SHA-256 hashing and ECDSA signature generation & verification.
"""

import json
import hashlib
import base64
from typing import Dict, Any, List, Union
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

class SecurityGatingError(Exception):
    """Raised when an unauthorized or improperly signed critical action is attempted."""
    pass

def canonical_json(data: Any) -> str:
    """
    Produces deterministic, canonical JSON representation with sorted keys and minimal whitespace.
    """
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    elif hasattr(data, "dict"):
        data = data.dict()
        
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str)

def compute_plan_sha256(tactical_actions: Union[List[Any], Dict[str, Any]]) -> str:
    """
    Hash_plan = SHA256(CanonicalJSON(draft_iap))
    """
    c_json = canonical_json(tactical_actions)
    return hashlib.sha256(c_json.encode('utf-8')).hexdigest()

class CommanderCryptoKeyManager:
    """
    Manages Commander cryptographic keypairs (ECDSA SECP256R1).
    Used for non-repudiation audit trails and dispatch gate validation.
    """
    def __init__(self):
        # Generate persistent in-memory commander keypair for incident command
        self._private_key = ec.generate_private_key(ec.SECP256R1())
        self._public_key = self._private_key.public_key()
        
        # Pre-export public key in PEM format
        self.public_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
    def sign_plan_hash(self, plan_hash: str) -> str:
        """
        Signs the plan SHA-256 hex string using ECDSA with SHA-256.
        Returns base64 encoded signature.
        """
        signature = self._private_key.sign(
            plan_hash.encode('utf-8'),
            ec.ECDSA(hashes.SHA256())
        )
        return base64.b64encode(signature).decode('utf-8')

    def verify_signature(self, plan_hash: str, signature_b64: str) -> bool:
        """
        Verifies ECDSA signature of plan_hash against commander public key.
        """
        if not signature_b64:
            return False
        try:
            signature_bytes = base64.b64decode(signature_b64)
            self._public_key.verify(
                signature_bytes,
                plan_hash.encode('utf-8'),
                ec.ECDSA(hashes.SHA256())
            )
            return True
        except (InvalidSignature, Exception):
            return False

# Global Commander Key Manager Singleton
commander_key_mgr = CommanderCryptoKeyManager()
