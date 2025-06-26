
# Pow_CRM Deployment Instructions

## 🎯 You're Ready to Deploy!

Your GitHub repository is created and ready: https://github.com/btcdcbuilds/Pow_CRM

## 📋 Next Steps:

### 1. Setup Supabase Database
```sql
-- Go to your Supabase dashboard: https://lsagoolvyqwhovboyewj.supabase.co
-- Go to SQL Editor
-- Copy and paste the entire contents of supabase_schema.sql
-- Execute the SQL to create all tables and functions
```

### 2. Get Your Database Password
```
1. In Supabase dashboard, go to Settings > Database
2. Copy the connection string or reset the database password
3. Your connection string format:
   postgresql://postgres.lsagoolvyqwhovboyewj:[PASSWORD]@aws-0-us-west-1.pooler.supabase.com:6543/postgres
```

### 3. Deploy to Render.com
```
1. Go to render.com and create new Web Service
2. Connect to GitHub repository: btcdcbuilds/Pow_CRM
3. Use these settings:
   - Build Command: pip install -r requirements.txt
   - Start Command: python health_check.py && python -c "import time; time.sleep(86400)"
   - Plan: Starter ($7/month)
```

### 4. Set Environment Variables in Render.com
```
ANTPOOL_API_KEY=your_actual_api_key
ANTPOOL_API_SECRET=your_actual_api_secret
ANTPOOL_USER_ID=your_actual_user_id
SUPABASE_CONNECTION_STRING=postgresql://postgres.lsagoolvyqwhovboyewj:[PASSWORD]@aws-0-us-west-1.pooler.supabase.com:6543/postgres
ANTPOOL_EMAIL=your_email@example.com
ANTPOOL_COINS=BTC
```

### 5. Configure Cron Jobs in Render.com
```
Tier 1: */10 * * * * python collect_tier1.py
Tier 2: 0 * * * * python collect_tier2.py  
Tier 3: 0 2 * * * python collect_tier3.py
Tier 4: 0 3 * * * python collect_tier4.py
```

## 🎉 That's It!

Your system will automatically:
- ✅ Collect pool data every 10 minutes
- ✅ Collect all 6000+ worker data every hour
- ✅ Process daily earnings at 2 AM
- ✅ Clean up old data at 3 AM
- ✅ Stay within API rate limits
- ✅ Handle sub-accounts automatically
- ✅ Alert on offline/low-performing workers

Total cost: $7/month (Render.com) + $0-25/month (Supabase)
