-- Antpool Mining Data Database Schema - CLEANED VERSION
-- Aligned with actual Antpool API capabilities
-- Designed for 33 accounts with 600 API calls per 10 minutes limit

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- ACCOUNTS TABLE - Main and Sub-accounts
-- =====================================================
CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    account_name VARCHAR(255) UNIQUE NOT NULL,
    account_type VARCHAR(20) NOT NULL CHECK (account_type IN ('main', 'sub')),
    email VARCHAR(255),
    coin_type VARCHAR(10) DEFAULT 'BTC',
    parent_account_id INTEGER REFERENCES accounts(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Indexes for accounts
CREATE INDEX IF NOT EXISTS idx_accounts_name ON accounts(account_name);
CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts(account_type);
CREATE INDEX IF NOT EXISTS idx_accounts_parent ON accounts(parent_account_id);

-- =====================================================
-- ACCOUNT BALANCES - From /api/account.htm
-- =====================================================
CREATE TABLE IF NOT EXISTS account_balances (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    coin_type VARCHAR(10) NOT NULL DEFAULT 'BTC',
    balance DECIMAL(20, 8) DEFAULT 0,
    earn_24_hours DECIMAL(20, 8) DEFAULT 0,
    earn_total DECIMAL(20, 8) DEFAULT 0,
    paid_out DECIMAL(20, 8) DEFAULT 0,
    unpaid_amount DECIMAL(20, 8) DEFAULT 0,
    settle_time DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for account_balances
CREATE INDEX IF NOT EXISTS idx_account_balances_account_id ON account_balances(account_id);
CREATE INDEX IF NOT EXISTS idx_account_balances_created_at ON account_balances(created_at);
CREATE INDEX IF NOT EXISTS idx_account_balances_coin ON account_balances(coin_type);

-- =====================================================
-- HASHRATES - From /api/hashrate.htm
-- =====================================================
CREATE TABLE IF NOT EXISTS hashrates (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    coin_type VARCHAR(10) NOT NULL DEFAULT 'BTC',
    hashrate_10m BIGINT DEFAULT 0,
    hashrate_1h BIGINT DEFAULT 0,
    hashrate_1d BIGINT DEFAULT 0,
    accepted_shares BIGINT DEFAULT 0,
    stale_shares BIGINT DEFAULT 0,
    duplicate_shares BIGINT DEFAULT 0,
    other_shares BIGINT DEFAULT 0,
    total_workers INTEGER DEFAULT 0,
    active_workers INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for hashrates
CREATE INDEX IF NOT EXISTS idx_hashrates_account_id ON hashrates(account_id);
CREATE INDEX IF NOT EXISTS idx_hashrates_created_at ON hashrates(created_at);
CREATE INDEX IF NOT EXISTS idx_hashrates_coin ON hashrates(coin_type);

-- =====================================================
-- ACCOUNT OVERVIEW - From /api/accountOverview.htm
-- =====================================================
CREATE TABLE IF NOT EXISTS account_overview (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    coin_type VARCHAR(10) NOT NULL DEFAULT 'BTC',
    hashrate_10m BIGINT DEFAULT 0,
    hashrate_1h BIGINT DEFAULT 0,
    hashrate_1d BIGINT DEFAULT 0,
    total_workers INTEGER DEFAULT 0,
    active_workers INTEGER DEFAULT 0,
    inactive_workers INTEGER DEFAULT 0,
    invalid_workers INTEGER DEFAULT 0,
    total_amount DECIMAL(20, 8) DEFAULT 0,
    unpaid_amount DECIMAL(20, 8) DEFAULT 0,
    yesterday_amount DECIMAL(20, 8) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for account_overview
CREATE INDEX IF NOT EXISTS idx_account_overview_account_id ON account_overview(account_id);
CREATE INDEX IF NOT EXISTS idx_account_overview_created_at ON account_overview(created_at);
CREATE INDEX IF NOT EXISTS idx_account_overview_coin ON account_overview(coin_type);

-- =====================================================
-- WORKERS - From /api/workers.htm and /api/userWorkerList.htm
-- =====================================================
CREATE TABLE IF NOT EXISTS workers (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    coin_type VARCHAR(10) NOT NULL DEFAULT 'BTC',
    worker_name VARCHAR(255) NOT NULL,
    worker_status VARCHAR(20) DEFAULT 'unknown' CHECK (worker_status IN ('online', 'offline', 'invalid', 'unknown')),
    hashrate_10m BIGINT DEFAULT 0,
    hashrate_1h BIGINT DEFAULT 0,
    hashrate_1d BIGINT DEFAULT 0,
    accepted_shares BIGINT DEFAULT 0,
    stale_shares BIGINT DEFAULT 0,
    duplicate_shares BIGINT DEFAULT 0,
    other_shares BIGINT DEFAULT 0,
    reject_rate DECIMAL(5, 2) DEFAULT 0,
    last_share_time TIMESTAMP WITH TIME ZONE,
    data_type VARCHAR(20) DEFAULT 'detailed' CHECK (data_type IN ('summary', 'detailed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for workers
CREATE INDEX IF NOT EXISTS idx_workers_account_id ON workers(account_id);
CREATE INDEX IF NOT EXISTS idx_workers_name ON workers(worker_name);
CREATE INDEX IF NOT EXISTS idx_workers_status ON workers(worker_status);
CREATE INDEX IF NOT EXISTS idx_workers_created_at ON workers(created_at);
CREATE INDEX IF NOT EXISTS idx_workers_data_type ON workers(data_type);

-- =====================================================
-- PAYMENT HISTORY - From /api/paymentHistoryV2.htm
-- =====================================================
CREATE TABLE IF NOT EXISTS payment_history (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    coin_type VARCHAR(10) NOT NULL DEFAULT 'BTC',
    payment_type VARCHAR(20) NOT NULL CHECK (payment_type IN ('payout', 'earnings')),
    amount DECIMAL(20, 8) NOT NULL,
    payment_time TIMESTAMP WITH TIME ZONE NOT NULL,
    wallet_address VARCHAR(255),
    tx_id VARCHAR(255),
    hashrate_value BIGINT,
    hashrate_unit VARCHAR(50),
    pps_amount DECIMAL(20, 8) DEFAULT 0,
    pplns_amount DECIMAL(20, 8) DEFAULT 0,
    solo_amount DECIMAL(20, 8) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for payment_history
CREATE INDEX IF NOT EXISTS idx_payment_history_account_id ON payment_history(account_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_payment_time ON payment_history(payment_time);
CREATE INDEX IF NOT EXISTS idx_payment_history_coin ON payment_history(coin_type);
CREATE INDEX IF NOT EXISTS idx_payment_history_type ON payment_history(payment_type);

-- =====================================================
-- POOL STATS - From /api/poolStats.htm (limited data)
-- =====================================================
CREATE TABLE IF NOT EXISTS pool_stats (
    id SERIAL PRIMARY KEY,
    coin_type VARCHAR(10) NOT NULL DEFAULT 'BTC',
    pool_hashrate BIGINT DEFAULT 0,
    active_worker_number INTEGER DEFAULT 0,
    pool_status VARCHAR(20) DEFAULT 'Unknown',
    network_difficulty BIGINT DEFAULT 0,
    estimate_time INTEGER DEFAULT 0,
    current_round INTEGER DEFAULT 0,
    total_share_number BIGINT DEFAULT 0,
    total_block_number BIGINT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for pool_stats
CREATE INDEX IF NOT EXISTS idx_pool_stats_created_at ON pool_stats(created_at);
CREATE INDEX IF NOT EXISTS idx_pool_stats_coin ON pool_stats(coin_type);

-- =====================================================
-- API CALL LOGS - Rate limiting and monitoring
-- =====================================================
CREATE TABLE IF NOT EXISTS api_call_logs (
    id SERIAL PRIMARY KEY,
    endpoint VARCHAR(255) NOT NULL,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    response_status INTEGER,
    response_time_ms INTEGER,
    api_calls_in_window INTEGER DEFAULT 1,
    window_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for api_call_logs
CREATE INDEX IF NOT EXISTS idx_api_logs_created_at ON api_call_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_api_logs_endpoint ON api_call_logs(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_logs_window ON api_call_logs(window_start);

-- =====================================================
-- WORKER ALERTS - Simple offline/performance alerts
-- =====================================================
CREATE TABLE IF NOT EXISTS worker_alerts (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    worker_name VARCHAR(255) NOT NULL,
    alert_type VARCHAR(50) NOT NULL CHECK (alert_type IN ('offline', 'low_hashrate', 'high_reject_rate')),
    message TEXT NOT NULL,
    alert_level VARCHAR(20) DEFAULT 'warning' CHECK (alert_level IN ('info', 'warning', 'critical')),
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for worker_alerts
CREATE INDEX IF NOT EXISTS idx_worker_alerts_account_id ON worker_alerts(account_id);
CREATE INDEX IF NOT EXISTS idx_worker_alerts_type ON worker_alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_worker_alerts_resolved ON worker_alerts(is_resolved);
CREATE INDEX IF NOT EXISTS idx_worker_alerts_created_at ON worker_alerts(created_at);

-- =====================================================
-- USEFUL VIEWS FOR DASHBOARD
-- =====================================================

-- Latest account balances
CREATE OR REPLACE VIEW latest_account_balances AS
SELECT DISTINCT ON (account_id) 
    ab.*,
    a.account_name,
    a.account_type
FROM account_balances ab
JOIN accounts a ON ab.account_id = a.id
ORDER BY account_id, created_at DESC;

-- Latest account overview
CREATE OR REPLACE VIEW latest_account_overview AS
SELECT DISTINCT ON (account_id) 
    ao.*,
    a.account_name,
    a.account_type
FROM account_overview ao
JOIN accounts a ON ao.account_id = a.id
ORDER BY account_id, created_at DESC;

-- Latest hashrates
CREATE OR REPLACE VIEW latest_hashrates AS
SELECT DISTINCT ON (account_id) 
    h.*,
    a.account_name,
    a.account_type
FROM hashrates h
JOIN accounts a ON h.account_id = a.id
ORDER BY account_id, created_at DESC;

-- Current worker status (last 24 hours)
CREATE OR REPLACE VIEW current_worker_status AS
SELECT DISTINCT ON (account_id, worker_name)
    w.*,
    a.account_name,
    a.account_type
FROM workers w
JOIN accounts a ON w.account_id = a.id
WHERE w.created_at > NOW() - INTERVAL '24 hours'
ORDER BY account_id, worker_name, created_at DESC;

-- Active alerts
CREATE OR REPLACE VIEW active_alerts AS
SELECT 
    wa.*,
    a.account_name,
    a.account_type
FROM worker_alerts wa
JOIN accounts a ON wa.account_id = a.id
WHERE wa.is_resolved = FALSE
ORDER BY wa.created_at DESC;

-- API rate limiting view (last 10 minutes)
CREATE OR REPLACE VIEW api_rate_status AS
SELECT 
    COUNT(*) as calls_in_last_10min,
    600 - COUNT(*) as calls_remaining,
    MIN(created_at) as window_start,
    MAX(created_at) as last_call
FROM api_call_logs 
WHERE created_at > NOW() - INTERVAL '10 minutes';

-- =====================================================
-- DATA RETENTION FUNCTIONS
-- =====================================================

-- Function to cleanup old worker data (keep 7 days for detailed data)
CREATE OR REPLACE FUNCTION cleanup_old_worker_data()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM workers 
    WHERE data_type = 'detailed' 
    AND created_at < NOW() - INTERVAL '7 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old API logs (keep 7 days)
CREATE OR REPLACE FUNCTION cleanup_old_api_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM api_call_logs 
    WHERE created_at < NOW() - INTERVAL '7 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup resolved alerts (keep 14 days)
CREATE OR REPLACE FUNCTION cleanup_old_alerts()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM worker_alerts 
    WHERE is_resolved = TRUE 
    AND resolved_at < NOW() - INTERVAL '14 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to check API rate limit
CREATE OR REPLACE FUNCTION check_api_rate_limit()
RETURNS INTEGER AS $$
DECLARE
    current_calls INTEGER;
BEGIN
    SELECT COUNT(*) INTO current_calls
    FROM api_call_logs 
    WHERE created_at > NOW() - INTERVAL '10 minutes';
    
    RETURN 600 - current_calls;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- TRIGGERS FOR AUTOMATIC TIMESTAMPS
-- =====================================================

-- Function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for accounts table
CREATE TRIGGER update_accounts_updated_at 
    BEFORE UPDATE ON accounts 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- COMMENTS FOR DOCUMENTATION
-- =====================================================

COMMENT ON TABLE accounts IS 'Main and sub-accounts with hierarchical structure';
COMMENT ON TABLE account_balances IS 'Account balance data from /api/account.htm';
COMMENT ON TABLE hashrates IS 'Hashrate data from /api/hashrate.htm';
COMMENT ON TABLE account_overview IS 'Overview data from /api/accountOverview.htm';
COMMENT ON TABLE workers IS 'Worker data from /api/workers.htm and /api/userWorkerList.htm';
COMMENT ON TABLE payment_history IS 'Payment data from /api/paymentHistoryV2.htm';
COMMENT ON TABLE pool_stats IS 'Pool statistics from /api/poolStats.htm';
COMMENT ON TABLE api_call_logs IS 'API usage tracking for rate limiting';
COMMENT ON TABLE worker_alerts IS 'Simple worker alerts based on actual data';

-- Schema cleanup complete
SELECT 'Cleaned Antpool database schema created successfully' as status;

