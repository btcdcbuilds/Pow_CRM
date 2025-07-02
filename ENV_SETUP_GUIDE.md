# Encrypted .env Setup Guide

**Replaces 99+ GitHub Secrets with 1 Encrypted File + 1 Secret**

## 🎯 **Overview**

Instead of managing 99+ individual GitHub secrets, we now use:
- **1 encrypted .env file** (stored in repository)
- **1 GitHub secret** (encryption password)
- **Easy management** (edit one file vs 99 secrets)

## 📋 **Complete Pool List**

| Pool Name | Pool ID | Group | Credentials Needed |
|-----------|---------|-------|-------------------|
| POWDigital3 | POWDIGITAL3 | BC | ACCESS_KEY, SECRET_KEY, USER_ID |
| PNGMiningEth | PNGMININGETH | BC | ACCESS_KEY, SECRET_KEY, USER_ID |
| PedroEth | PEDROETH | BC | ACCESS_KEY, SECRET_KEY, USER_ID |
| KennDunk | KENNDUNK | BC | ACCESS_KEY, SECRET_KEY, USER_ID |
| YZMining | YZMINING | BC | ACCESS_KEY, SECRET_KEY, USER_ID |
| SVJMining | SVJMINING | BR | ACCESS_KEY, SECRET_KEY, USER_ID |
| ZTuneMining | ZTUNEMINING | BR | ACCESS_KEY, SECRET_KEY, USER_ID |
| BMasterMining | BMASTERMINING | BR | ACCESS_KEY, SECRET_KEY, USER_ID |
| Allin3 | ALLIN3 | BR | ACCESS_KEY, SECRET_KEY, USER_ID |
| Mack81 | MACK81 | BaoHui1 | ACCESS_KEY, SECRET_KEY, USER_ID |
| CanKann2 | CANKANN2 | BR | ACCESS_KEY, SECRET_KEY, USER_ID |
| PedroMining | PEDROMINING | BR | ACCESS_KEY, SECRET_KEY, USER_ID |
| VanMining | VANMINING | BR | ACCESS_KEY, SECRET_KEY, USER_ID |
| LasVegasMining | LASVEGASMINING | BR | ACCESS_KEY, SECRET_KEY, USER_ID |
| CanKann | CANKANN | BR | ACCESS_KEY, SECRET_KEY, USER_ID |
| PNGMining | PNGMINING | BR | ACCESS_KEY, SECRET_KEY, USER_ID |
| Rarcoa | RARCOA | BR | ACCESS_KEY, SECRET_KEY, USER_ID |
| Soltero | SOLTERO | BR | ACCESS_KEY, SECRET_KEY, USER_ID |
| BillMiningBR | BILLMININGBR | BR | ACCESS_KEY, SECRET_KEY, USER_ID |
| POWDigital2 | POWDIGITAL2 | BR | ACCESS_KEY, SECRET_KEY, USER_ID |
| BlackDawn | BLACKDAWN | BR | ACCESS_KEY, SECRET_KEY, USER_ID |
| Manggornmoo | MANGGORNMOO | Stella | ACCESS_KEY, SECRET_KEY, USER_ID |
| Lasvegasmining2 | LASVEGASMINING2 | Stella | ACCESS_KEY, SECRET_KEY, USER_ID |
| 50Shades | FIFTYSHADES | Stella | ACCESS_KEY, SECRET_KEY, USER_ID |
| NsxR | NSXR | Stella | ACCESS_KEY, SECRET_KEY, USER_ID |
| BlockwareSA | BLOCKWARESA | Stella | ACCESS_KEY, SECRET_KEY, USER_ID |
| RarcoaSA | RARCOASA | Stella | ACCESS_KEY, SECRET_KEY, USER_ID |
| VanminingSA | VANMININGSA | Stella | ACCESS_KEY, SECRET_KEY, USER_ID |
| BillminingSA | BILLMININGSA | Stella | ACCESS_KEY, SECRET_KEY, USER_ID |
| Allin2 | ALLIN2 | Stella | ACCESS_KEY, SECRET_KEY, USER_ID |
| TylerDSA | TYLERDSA | Stella | ACCESS_KEY, SECRET_KEY, USER_ID |
| GoldenDawn | GOLDENDAWN | BaoHui2 | ACCESS_KEY, SECRET_KEY, USER_ID |
| POWDigital | POWDIGITAL | Stella | ACCESS_KEY, SECRET_KEY, USER_ID |

**Total: 33 pools × 3 credentials = 99 credentials**

## 🚀 **Quick Setup**

### **Step 1: Create .env File**
```bash
# Copy the template
cp .env.template .env

# Edit with your actual credentials
nano .env
```

### **Step 2: Fill in Credentials**
Edit `.env` file with your actual Antpool API credentials:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_supabase_service_key

# POWDigital3
POWDIGITAL3_ACCESS_KEY=7653a14dbf4a48fa91dde7fdff262341
POWDIGITAL3_SECRET_KEY=75c3fd4dadc44c80ab66cbd9a148ec2f
POWDIGITAL3_USER_ID=POWDigital3

# ... (repeat for all 33 pools)
```

### **Step 3: Encrypt the .env File**
```bash
# Set encryption password
export ENV_ENCRYPTION_KEY="your_strong_password_here"

# Encrypt the .env file
python env_manager.py encrypt .env

# This creates .env.encrypted
```

### **Step 4: Update GitHub Secrets**
Remove all 99+ individual secrets and add just 1:

**GitHub Secret:**
- `ENV_ENCRYPTION_KEY` = `your_strong_password_here`

### **Step 5: Update Workflows**
The workflows will automatically use the encrypted .env file instead of individual secrets.

## 🔧 **Management Commands**

### **Create .env from Current GitHub Secrets**
```bash
# If you already have GitHub secrets set up
python env_manager.py create_from_github
```

### **Encrypt .env File**
```bash
export ENV_ENCRYPTION_KEY="your_password"
python env_manager.py encrypt .env
```

### **Decrypt .env File** (for editing)
```bash
export ENV_ENCRYPTION_KEY="your_password"
python env_manager.py decrypt .env.encrypted
```

### **Test Encrypted Loading**
```bash
export ENV_ENCRYPTION_KEY="your_password"
python -c "from env_manager import EncryptedEnvManager; mgr = EncryptedEnvManager(); mgr.load_encrypted_env('.env.encrypted')"
```

## 📁 **File Structure**

```
Pow_CRM/
├── .env.template          # Template with all pool placeholders
├── .env                   # Your actual credentials (DO NOT COMMIT)
├── .env.encrypted         # Encrypted credentials (safe to commit)
├── env_manager.py         # Encryption/decryption utility
├── POOL_LIST.md          # Complete pool documentation
└── ENV_SETUP_GUIDE.md    # This guide
```

## 🔒 **Security**

### **What's Safe to Commit**
- ✅ `.env.template` - No real credentials
- ✅ `.env.encrypted` - Encrypted with strong password
- ✅ `env_manager.py` - Encryption utility
- ❌ `.env` - Contains real credentials

### **Encryption Details**
- **Algorithm:** AES-256 via Fernet (cryptography library)
- **Key Derivation:** PBKDF2-HMAC-SHA256 with 100,000 iterations
- **Salt:** Fixed salt for consistency across deployments
- **Encoding:** Base64 for safe text storage

## 🎯 **Benefits**

### **Before (GitHub Secrets)**
- ❌ 99+ individual secrets to manage
- ❌ Hit GitHub's 100 secret limit
- ❌ Adding new pool = 3 new secrets
- ❌ Updating credentials = find/edit multiple secrets
- ❌ No easy backup/restore

### **After (Encrypted .env)**
- ✅ 1 encryption key to manage
- ✅ No GitHub limits
- ✅ Adding new pool = edit 1 file
- ✅ Updating credentials = edit 1 file
- ✅ Easy backup/restore/version control

## 🔄 **Adding New Pools**

### **Old Way (GitHub Secrets)**
1. Go to GitHub repository settings
2. Add 3 new secrets: `NEWPOOL_ACCESS_KEY`, `NEWPOOL_SECRET_KEY`, `NEWPOOL_USER_ID`
3. Update workflow YAML files
4. Update account list in code

### **New Way (Encrypted .env)**
1. Edit `.env` file locally
2. Add 3 lines for new pool
3. Re-encrypt: `python env_manager.py encrypt .env`
4. Commit `.env.encrypted`
5. Update account list in code

## 🚨 **Troubleshooting**

### **"ENV_ENCRYPTION_KEY not found"**
- Set the GitHub secret `ENV_ENCRYPTION_KEY`
- Make sure it matches the password used for encryption

### **"Encrypted file not found"**
- Make sure `.env.encrypted` exists in repository
- Re-encrypt your `.env` file if needed

### **"Failed to decrypt"**
- Check that `ENV_ENCRYPTION_KEY` is correct
- Verify `.env.encrypted` file is not corrupted

### **"Missing credentials for pool"**
- Check that pool credentials are in `.env` file
- Verify pool name matches exactly (case sensitive)
- Re-encrypt after making changes

## 📞 **Support**

If you need help:
1. Check the encryption key is set correctly
2. Verify `.env.encrypted` file exists
3. Test decryption locally first
4. Check GitHub Actions logs for specific errors

---

**This system scales to unlimited pools without GitHub secret limits!** 🚀

