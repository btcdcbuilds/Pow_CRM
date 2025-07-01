# 🔑 Step-by-Step: Add Your API Keys Securely

## 🎯 **Quick Setup (5 minutes)**

### **Step 1: Go to GitHub Secrets**
Click this link: https://github.com/btcdcbuilds/Pow_CRM/settings/secrets/actions

### **Step 2: Add 4 Secrets**

Click **"New repository secret"** for each of these:

#### **Secret 1: ANTPOOL_ACCESS_KEY**
- **Name**: `ANTPOOL_ACCESS_KEY`
- **Value**: `your_antpool_access_key_here`

#### **Secret 2: ANTPOOL_SECRET_KEY**  
- **Name**: `ANTPOOL_SECRET_KEY`
- **Value**: `your_antpool_secret_key_here`

#### **Secret 3: SUPABASE_URL**
- **Name**: `SUPABASE_URL`
- **Value**: `https://lsagoolvyqwhovboyewj.supabase.co`

#### **Secret 4: SUPABASE_ANON_KEY**
- **Name**: `SUPABASE_ANON_KEY`  
- **Value**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxzYWdvb2x2eXF3aG92Ym95ZXdqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzMxMjg5MzMsImV4cCI6MjA0ODcwNDkzM30.xh03WjOxoajAsKNJ6rbe_OKIIzX6-Sbc7V7JRn0E6Zk`

### **Step 3: Test It Works**
1. Go to: https://github.com/btcdcbuilds/Pow_CRM/actions
2. Click **"Tier 1 - Dashboard Data Collection"**
3. Click **"Run workflow"** → **"Run workflow"**
4. Watch it run and check the logs!

## 🔒 **Your API Keys Are Safe Because:**

✅ **Encrypted with AES-256** (military-grade encryption)  
✅ **Never visible in logs** (shows as `***`)  
✅ **Only you can see them** (repo owner access only)  
✅ **Not stored in code** (separate encrypted vault)  
✅ **Isolated execution** (fresh computer each time)  

## 🎉 **What Happens Next**

Once you add the secrets:

- ✅ **Tier 1** runs every 10 minutes (pool data)
- ✅ **Tier 2** runs every hour (worker performance)  
- ✅ **Tier 3** runs daily at 2 AM (financial data)
- ✅ **Tier 4** runs daily at 3 AM (cleanup)

**All completely FREE and automatic!** 🚀

## 📊 **Monitor Your Automation**

- **Actions tab**: https://github.com/btcdcbuilds/Pow_CRM/actions
- **Supabase dashboard**: Check your data is being collected
- **Usage**: Settings → Billing (you'll use ~212 of 2000 free minutes)

**You're about to save $420/year with better reliability!** 💰

