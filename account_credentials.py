"""
Account credentials manager for all sub-accounts
Maps account names to their GitHub secret names
"""

import os
from typing import Dict, Tuple

# Account name to secret name mapping
ACCOUNT_CREDENTIALS = {
    'POWDigital3': ('POWDIGITAL3_ACCESS_KEY', 'POWDIGITAL3_SECRET_KEY', 'POWDIGITAL3_USER_ID'),
    'PNGMiningEth': ('PNGMININGETH_ACCESS_KEY', 'PNGMININGETH_SECRET_KEY', 'PNGMININGETH_USER_ID'),
    'PedroEth': ('PEDROETH_ACCESS_KEY', 'PEDROETH_SECRET_KEY', 'PEDROETH_USER_ID'),
    'KennDunk': ('KENNDUNK_ACCESS_KEY', 'KENNDUNK_SECRET_KEY', 'KENNDUNK_USER_ID'),
    'YZMining': ('YZMINING_ACCESS_KEY', 'YZMINING_SECRET_KEY', 'YZMINING_USER_ID'),
    'SVJMining': ('SVJMINING_ACCESS_KEY', 'SVJMINING_SECRET_KEY', 'SVJMINING_USER_ID'),
    'ZTuneMining': ('ZTUNEMINING_ACCESS_KEY', 'ZTUNEMINING_SECRET_KEY', 'ZTUNEMINING_USER_ID'),
    'BMasterMining': ('BMASTERMINING_ACCESS_KEY', 'BMASTERMINING_SECRET_KEY', 'BMASTERMINING_USER_ID'),
    'Allin3': ('ALLIN3_ACCESS_KEY', 'ALLIN3_SECRET_KEY', 'ALLIN3_USER_ID'),
    'Mack81': ('MACK81_ACCESS_KEY', 'MACK81_SECRET_KEY', 'MACK81_USER_ID'),
    'CanKann2': ('CANKANN2_ACCESS_KEY', 'CANKANN2_SECRET_KEY', 'CANKANN2_USER_ID'),
    'PedroMining': ('PEDROMINING_ACCESS_KEY', 'PEDROMINING_SECRET_KEY', 'PEDROMINING_USER_ID'),
    'VanMining': ('VANMINING_ACCESS_KEY', 'VANMINING_SECRET_KEY', 'VANMINING_USER_ID'),
    'LasVegasMining': ('LASVEGASMINING_ACCESS_KEY', 'LASVEGASMINING_SECRET_KEY', 'LASVEGASMINING_USER_ID'),
    'CanKann': ('CANKANN_ACCESS_KEY', 'CANKANN_SECRET_KEY', 'CANKANN_USER_ID'),
    'PNGMining': ('PNGMINING_ACCESS_KEY', 'PNGMINING_SECRET_KEY', 'PNGMINING_USER_ID'),
    'Rarcoa': ('RARCOA_ACCESS_KEY', 'RARCOA_SECRET_KEY', 'RARCOA_USER_ID'),
    'Soltero': ('SOLTERO_ACCESS_KEY', 'SOLTERO_SECRET_KEY', 'SOLTERO_USER_ID'),
    'BillMiningBR': ('BILLMININGBR_ACCESS_KEY', 'BILLMININGBR_SECRET_KEY', 'BILLMININGBR_USER_ID'),
    'POWDigital2': ('POWDIGITAL2_ACCESS_KEY', 'POWDIGITAL2_SECRET_KEY', 'POWDIGITAL2_USER_ID'),
    'BlackDawn': ('BLACKDAWN_ACCESS_KEY', 'BLACKDAWN_SECRET_KEY', 'BLACKDAWN_USER_ID'),
    'Manggornmoo': ('MANGGORNMOO_ACCESS_KEY', 'MANGGORNMOO_SECRET_KEY', 'MANGGORNMOO_USER_ID'),
    'Lasvegasmining2': ('LASVEGASMINING2_ACCESS_KEY', 'LASVEGASMINING2_SECRET_KEY', 'LASVEGASMINING2_USER_ID'),
    '50Shades': ('FIFTYSHADES_ACCESS_KEY', 'FIFTYSHADES_SECRET_KEY', 'FIFTYSHADES_USER_ID'),
    'NsxR': ('NSXR_ACCESS_KEY', 'NSXR_SECRET_KEY', 'NSXR_USER_ID'),
    'BlockwareSA': ('BLOCKWARESA_ACCESS_KEY', 'BLOCKWARESA_SECRET_KEY', 'BLOCKWARESA_USER_ID'),
    'RarcoaSA': ('RARCOASA_ACCESS_KEY', 'RARCOASA_SECRET_KEY', 'RARCOASA_USER_ID'),
    'VanminingSA': ('VANMININGSA_ACCESS_KEY', 'VANMININGSA_SECRET_KEY', 'VANMININGSA_USER_ID'),
    'BillminingSA': ('BILLMININGSA_ACCESS_KEY', 'BILLMININGSA_SECRET_KEY', 'BILLMININGSA_USER_ID'),
    'Allin2': ('ALLIN2_ACCESS_KEY', 'ALLIN2_SECRET_KEY', 'ALLIN2_USER_ID'),
    'TylerDSA': ('TYLERDSA_ACCESS_KEY', 'TYLERDSA_SECRET_KEY', 'TYLERDSA_USER_ID'),
    'GoldenDawn': ('GOLDENDAWN_ACCESS_KEY', 'GOLDENDAWN_SECRET_KEY', 'GOLDENDAWN_USER_ID'),
    'POWDigital': ('POWDIGITAL_ACCESS_KEY', 'POWDIGITAL_SECRET_KEY', 'POWDIGITAL_USER_ID'),
}

def get_account_credentials(account_name: str) -> Tuple[str, str, str]:
    """
    Get API credentials for a specific account
    Returns: (api_key, api_secret, user_id)
    """
    if account_name not in ACCOUNT_CREDENTIALS:
        raise ValueError(f"Unknown account: {account_name}")
    
    key_name, secret_name, user_id_name = ACCOUNT_CREDENTIALS[account_name]
    
    api_key = os.getenv(key_name)
    api_secret = os.getenv(secret_name)
    user_id = os.getenv(user_id_name)
    
    if not all([api_key, api_secret, user_id]):
        missing = []
        if not api_key: missing.append(key_name)
        if not api_secret: missing.append(secret_name)
        if not user_id: missing.append(user_id_name)
        raise ValueError(f"Missing credentials for {account_name}: {missing}")
    
    return api_key, api_secret, user_id

def get_all_account_names():
    """Get list of all account names"""
    return list(ACCOUNT_CREDENTIALS.keys())

