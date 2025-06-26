# Pow_CRM - Antpool Mining Data Extraction System

A comprehensive data extraction system for Antpool mining operations, designed for Render.com deployment with automatic scheduling and Supabase storage.

## 🎯 **System Overview**

This system collects mining data from Antpool API across **6000+ devices** using a smart 4-tier collection strategy that respects API rate limits while providing comprehensive dashboard data.

### **4-Tier Collection Strategy**

| Tier | Frequency | Purpose | API Calls | Data Collected |
|------|-----------|---------|-----------|----------------|
| **Tier 1** | Every 10 min | Dashboard essentials | ~5-8 | Pool info, balances, offline devices |
| **Tier 2** | Every hour | Complete worker data | ~50-100 | All workers with hourly/24h hashrates |
| **Tier 3** | Daily 2 AM | Financial & historical | ~20-30 | Earnings, payments, daily summaries |
| **Tier 4** | Daily 3 AM | Data cleanup | 0 | Storage management, old data removal |

## 🚀 **Quick Deploy to Render.com**

### **Prerequisites**
- Antpool API credentials (API Key, Secret, User ID)
- Supabase account and database
- GitHub account
- Render.com account

### **Step 1: Fork & Clone**
```bash
# Fork this repository to your GitHub account
# Then clone it locally (optional, for testing)
git clone https://github.com/YOUR_USERNAME/Pow_CRM.git
cd Pow_CRM
```

### **Step 2: Setup Supabase Database**
1. Go to [supabase.com](https://supabase.com) and create a new project
2. Go to SQL Editor in your Supabase dashboard
3. Copy the entire contents of `supabase_schema.sql`
4. Paste and execute it in the SQL Editor
5. Go to Settings > Database and copy your connection string

### **Step 3: Deploy to Render.com**
1. Go to [render.com](https://render.com) and sign up/login
2. Click "New +" and select "Web Service"
3. Connect your GitHub account and select your forked repository
4. Configure the service:
   - **Name**: `pow-crm-antpool`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python health_check.py && python -c "import time; time.sleep(86400)"`
   - **Plan**: Starter ($7/month)

### **Step 4: Set Environment Variables**
In your Render.com service dashboard, go to Environment and add:

```bash
ANTPOOL_API_KEY=your_api_key_here
ANTPOOL_API_SECRET=your_api_secret_here  
ANTPOOL_USER_ID=your_main_user_id
SUPABASE_CONNECTION_STRING=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
ANTPOOL_EMAIL=your_email@example.com
ANTPOOL_COINS=BTC
```

### **Step 5: Configure Cron Jobs**
In your Render.com dashboard, add these cron jobs:

**Tier 1 - Dashboard Data (Every 10 minutes):**
- Name: `tier1-dashboard`
- Command: `python collect_tier1.py`
- Schedule: `*/10 * * * *`

**Tier 2 - Worker Data (Every hour):**
- Name: `tier2-workers`
- Command: `python collect_tier2.py`
- Schedule: `0 * * * *`

**Tier 3 - Daily Financial (Daily at 2 AM):**
- Name: `tier3-financial`
- Command: `python collect_tier3.py`
- Schedule: `0 2 * * *`

**Tier 4 - Cleanup (Daily at 3 AM):**
- Name: `tier4-cleanup`
- Command: `python collect_tier4.py`
- Schedule: `0 3 * * *`

## 📊 **Data Collection Details**

### **What Gets Collected**

#### **Tier 1 (Every 10 minutes)**
- ✅ Main account balance and earnings
- ✅ Sub-account balances and hashrates
- ✅ Offline device detection and alerts
- ✅ Pool-level statistics
- ✅ Critical status monitoring

#### **Tier 2 (Every hour)**
- ✅ All 6000+ workers from main account
- ✅ All workers from sub-accounts
- ✅ Hourly hashrate per worker
- ✅ 24-hour hashrate per worker
- ✅ Worker status and efficiency
- ✅ Low hashrate detection and alerting

#### **Tier 3 (Daily at 2 AM)**
- ✅ Daily earnings per worker
- ✅ Payment history tracking
- ✅ Daily efficiency calculations
- ✅ Worker performance summaries
- ✅ Pool statistics aggregation

#### **Tier 4 (Daily at 3 AM)**
- ✅ Delete 10-minute data older than 3 days
- ✅ Delete hourly worker data older than 7 days
- ✅ Keep daily summaries forever
- ✅ Database optimization and maintenance

### **Data Retention Policy**

| Data Type | Retention Period | Purpose |
|-----------|------------------|---------|
| 10-minute pool stats | 3 days | Real-time monitoring |
| Hourly worker data | 7 days | Performance tracking |
| Daily summaries | Forever | Historical analysis |
| Financial data | Forever | Accounting and reporting |
| Alerts | 14 days (resolved) | Issue tracking |

## 🏗️ **Database Schema**

The system uses 9 optimized PostgreSQL tables:

- **`accounts`** - Main and sub-accounts with hierarchy
- **`account_balances`** - Financial balances and earnings
- **`hashrates`** - Pool-level hashrate data
- **`workers`** - Individual worker performance data
- **`daily_worker_summaries`** - Aggregated daily worker stats
- **`worker_alerts`** - Offline and low-hashrate alerts
- **`payment_history`** - Payment transactions
- **`pool_stats`** - Pool-level statistics
- **`api_call_logs`** - API usage tracking

## 🔧 **API Usage Optimization**

### **Rate Limit Management**
- **Antpool Limit**: 600 calls per 10 minutes
- **Our Usage**: ~8 calls per 10 minutes (Tier 1)
- **Peak Usage**: ~100 calls per hour (Tier 2)
- **Safety Margin**: 85% under limit at all times

### **Batch Processing**
- Workers collected in efficient batches
- Sub-accounts processed sequentially
- Error handling prevents cascade failures
- Automatic retry with exponential backoff

## 📈 **Dashboard Data Available**

### **Real-time (10-minute updates)**
- Pool balance and earnings
- Total hashrate across all accounts
- Offline device count and alerts
- Sub-account performance summaries

### **Hourly Updates**
- Individual worker performance
- Hashrate trends (1h vs 24h)
- Worker efficiency scores
- Low-performing device alerts

### **Daily Analysis**
- Daily earnings per worker
- Payment history and trends
- Worker efficiency rankings
- Pool performance comparisons

## 🚨 **Monitoring & Alerts**

### **Automatic Alerts**
- **Offline Workers**: Detected every 10 minutes
- **Low Hashrate**: Workers performing <50% of 24h average
- **API Issues**: Failed requests and rate limit warnings
- **Database Issues**: Connection failures and cleanup results

### **Health Monitoring**
- System health checks before each collection
- API rate limit tracking
- Database connection monitoring
- Collection success/failure tracking

## 💰 **Cost Breakdown**

### **Render.com**
- **Web Service**: $7/month (Starter plan)
- **Cron Jobs**: Free (included with web service)

### **Supabase**
- **Free Tier**: Up to 500MB database storage
- **Pro Tier**: $25/month for larger databases

### **Total Monthly Cost**
- **Small Operation**: $7/month (Render + Supabase free)
- **Large Operation**: $32/month (Render + Supabase Pro)

## 🔒 **Security & Best Practices**

### **Environment Variables**
- All credentials stored as environment variables
- No hardcoded secrets in code
- Separate staging and production environments

### **API Security**
- HMAC-SHA256 authentication
- Request signing and timestamp validation
- Rate limit compliance and monitoring

### **Database Security**
- Connection string encryption
- Parameterized queries prevent SQL injection
- Regular security updates and patches

## 🛠️ **Local Development**

### **Setup**
```bash
# Clone the repository
git clone https://github.com/btcdcbuilds/Pow_CRM.git
cd Pow_CRM

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your credentials

# Test connection
python health_check.py

# Run individual tiers
python collect_tier1.py
python collect_tier2.py
python collect_tier3.py
python collect_tier4.py
```

### **Testing**
```bash
# Test API connection
python -c "from antpool_client import AntpoolClient; client = AntpoolClient('key', 'secret', 'user'); print(client.get_rate_limit_status())"

# Test database connection
python -c "from supabase_manager import SupabaseManager; db = SupabaseManager('connection_string'); print(db.test_connection())"

# Run health check
python health_check.py
```

## 📚 **File Structure**

```
Pow_CRM/
├── collect_tier1.py          # Dashboard essentials (10 min)
├── collect_tier2.py          # Worker data (hourly)
├── collect_tier3.py          # Financial data (daily)
├── collect_tier4.py          # Cleanup (daily)
├── health_check.py           # System health validation
├── antpool_auth.py           # API authentication
├── antpool_client.py         # API client with all endpoints
├── supabase_manager.py       # Database operations
├── data_orchestrator.py      # Main coordination logic
├── supabase_schema.sql       # Database schema
├── requirements.txt          # Python dependencies
├── render.yaml              # Render.com configuration
├── .env.example             # Environment template
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## 🤝 **Support & Contributing**

### **Getting Help**
1. Check Render.com service logs for errors
2. Run `python health_check.py` to test connections
3. Verify environment variables are set correctly
4. Check Supabase database schema is properly created

### **Common Issues**
- **API Authentication Failed**: Verify API key and secret
- **Database Connection Failed**: Check Supabase connection string
- **High API Usage**: Review collection frequency settings
- **Missing Data**: Check cron job schedules and logs

### **Contributing**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Built for efficient mining operations with 6000+ devices** 🚀

