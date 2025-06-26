-- Antpool Mining Data Database Schema - Optimized for 6000+ Workers
-- Designed for Supabase PostgreSQL with data retention policies
-- Supports main accounts + sub-accounts with proper separation

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
-- ACCOUNT BALANCES - Financial data (keep forever)
-- =====================================================
CREATE TABLE IF NOT EXISTS account_balances (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    coin_type VARCHAR(10) NOT NULL DEFAULT 'BTC',
    balance DECIMAL(20, 8) DEFAULT 0,
    earn_24_hours DECIMAL(20, 8) DEFAULT 0,
    earn_total DECIMAL(20, 8) DEFAULT 0,
    paid_out DECIMAL(20, 8) DEFAULT 0,
    unpaid DECIMAL(20, 8) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for account_balances
CREATE INDEX IF NOT EXISTS idx_account_balances_account_id ON account_balances(account_id);
CREATE INDEX IF NOT EXISTS idx_account_balances_created_at ON account_balances(created_at);
CREATE INDEX IF NOT EXISTS idx_account_balances_coin ON account_balances(coin_type);

-- =====================================================
-- HASHRATES - Pool-level hashrate data (keep forever)
-- =====================================================
CREATE TABLE IF NOT EXISTS hashrates (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    coin_type VARCHAR(10) NOT NULL DEFAULT 'BTC',
    hashrate_10m BIGINT DEFAULT 0,
    hashrate_1h BIGINT DEFAULT 0,
    hashrate_1d BIGINT DEFAULT 0,
    worker_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for hashrates
CREATE INDEX IF NOT EXISTS idx_hashrates_account_id ON hashrates(account_id);
CREATE INDEX IF NOT EXISTS idx_hashrates_created_at ON hashrates(created_at);
CREATE INDEX IF NOT EXISTS idx_hashrates_coin ON hashrates(coin_type);

-- =====================================================
-- WORKERS - Individual worker data (7-day retention for hourly, forever for daily)
-- =====================================================
CREATE TABLE IF NOT EXISTS workers (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    worker_name VARCHAR(255) NOT NULL,
    worker_status VARCHAR(20) DEFAULT 'Unknown',
    hashrate_1h BIGINT DEFAULT 0,
    hashrate_24h BIGINT DEFAULT 0,
    last_share_time TIMESTAMP WITH TIME ZONE,
    reject_rate DECIMAL(5, 2) DEFAULT 0,
    temperature INTEGER,
    fan_speed INTEGER,
    data_type VARCHAR(20) DEFAULT 'hourly' CHECK (data_type IN ('hourly', 'daily')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for workers (optimized for 6000+ workers)
CREATE INDEX IF NOT EXISTS idx_workers_account_id ON workers(account_id);
CREATE INDEX IF NOT EXISTS idx_workers_name ON workers(worker_name);
CREATE INDEX IF NOT EXISTS idx_workers_status ON workers(worker_status);
CREATE INDEX IF NOT EXISTS idx_workers_created_at ON workers(created_at);
CREATE INDEX IF NOT EXISTS idx_workers_data_type ON workers(data_type);
CREATE INDEX IF NOT EXISTS idx_workers_cleanup ON workers(data_type, created_at); -- For cleanup queries

-- =====================================================
-- DAILY WORKER SUMMARIES - Aggregated daily data (keep forever)
-- =====================================================
CREATE TABLE IF NOT EXISTS daily_worker_summaries (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    worker_name VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    avg_hashrate_1h BIGINT DEFAULT 0,
    avg_hashrate_24h BIGINT DEFAULT 0,
    uptime_percentage DECIMAL(5, 2) DEFAULT 0,
    efficiency_score DECIMAL(5, 4) DEFAULT 0,
    total_shares BIGINT DEFAULT 0,
    reject_rate DECIMAL(5, 2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(account_id, worker_name, date)
);

-- Indexes for daily_worker_summaries
CREATE INDEX IF NOT EXISTS idx_daily_summaries_account_id ON daily_worker_summaries(account_id);
CREATE INDEX IF NOT EXISTS idx_daily_summaries_date ON daily_worker_summaries(date);
CREATE INDEX IF NOT EXISTS idx_daily_summaries_worker ON daily_worker_summaries(worker_name);
CREATE INDEX IF NOT EXISTS idx_daily_summaries_efficiency ON daily_worker_summaries(efficiency_score);

-- =====================================================
-- WORKER ALERTS - Low hashrate and offline detection
-- =====================================================
CREATE TABLE IF NOT EXISTS worker_alerts (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    worker_name VARCHAR(255) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    alert_level VARCHAR(20) DEFAULT 'warning' CHECK (alert_level IN ('info', 'warning', 'critical')),
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for worker_alerts
CREATE INDEX IF NOT EXISTS idx_worker_alerts_account_id ON worker_alerts(account_id);
CREATE INDEX IF NOT EXISTS idx_worker_alerts_worker ON worker_alerts(worker_name);
CREATE INDEX IF NOT EXISTS idx_worker_alerts_type ON worker_alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_worker_alerts_level ON worker_alerts(alert_level);
CREATE INDEX IF NOT EXISTS idx_worker_alerts_resolved ON worker_alerts(is_resolved);
CREATE INDEX IF NOT EXISTS idx_worker_alerts_created_at ON worker_alerts(created_at);

-- =====================================================
-- PAYMENT HISTORY - Financial transactions (keep forever)
-- =====================================================
CREATE TABLE IF NOT EXISTS payment_history (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    coin_type VARCHAR(10) NOT NULL DEFAULT 'BTC',
    amount DECIMAL(20, 8) NOT NULL,
    payment_time TIMESTAMP WITH TIME ZONE NOT NULL,
    payment_tx VARCHAR(255),
    payment_status VARCHAR(20) DEFAULT 'completed',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for payment_history
CREATE INDEX IF NOT EXISTS idx_payment_history_account_id ON payment_history(account_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_payment_time ON payment_history(payment_time);
CREATE INDEX IF NOT EXISTS idx_payment_history_coin ON payment_history(coin_type);
CREATE INDEX IF NOT EXISTS idx_payment_history_status ON payment_history(payment_status);

-- =====================================================
-- POOL STATS - Pool-level statistics (3-day retention for 10-min data)
-- =====================================================
CREATE TABLE IF NOT EXISTS pool_stats (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    coin_type VARCHAR(10) NOT NULL DEFAULT 'BTC',
    total_workers INTEGER DEFAULT 0,
    online_workers INTEGER DEFAULT 0,
    offline_workers INTEGER DEFAULT 0,
    offline_percentage DECIMAL(5, 2) DEFAULT 0,
    pool_hashrate BIGINT DEFAULT 0,
    network_difficulty BIGINT DEFAULT 0,
    data_frequency VARCHAR(20) DEFAULT '10min' CHECK (data_frequency IN ('10min', 'hourly', 'daily')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for pool_stats
CREATE INDEX IF NOT EXISTS idx_pool_stats_account_id ON pool_stats(account_id);
CREATE INDEX IF NOT EXISTS idx_pool_stats_created_at ON pool_stats(created_at);
CREATE INDEX IF NOT EXISTS idx_pool_stats_frequency ON pool_stats(data_frequency);
CREATE INDEX IF NOT EXISTS idx_pool_stats_cleanup ON pool_stats(data_frequency, created_at); -- For cleanup

-- =====================================================
-- API CALL LOGS - Rate limiting and monitoring (30-day retention)
-- =====================================================
CREATE TABLE IF NOT EXISTS api_call_logs (
    id SERIAL PRIMARY KEY,
    endpoint VARCHAR(255) NOT NULL,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    response_status INTEGER,
    response_time_ms INTEGER,
    api_calls_remaining INTEGER,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for api_call_logs
CREATE INDEX IF NOT EXISTS idx_api_logs_created_at ON api_call_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_api_logs_endpoint ON api_call_logs(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_logs_status ON api_call_logs(response_status);

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

-- Latest hashrates
CREATE OR REPLACE VIEW latest_hashrates AS
SELECT DISTINCT ON (account_id) 
    h.*,
    a.account_name,
    a.account_type
FROM hashrates h
JOIN accounts a ON h.account_id = a.id
ORDER BY account_id, created_at DESC;

-- Current worker performance (last 24 hours)
CREATE OR REPLACE VIEW current_worker_performance AS
SELECT DISTINCT ON (account_id, worker_name)
    w.*,
    a.account_name,
    a.account_type
FROM workers w
JOIN accounts a ON w.account_id = a.id
WHERE w.created_at > NOW() - INTERVAL '24 hours'
ORDER BY account_id, worker_name, created_at DESC;

-- Active worker alerts
CREATE OR REPLACE VIEW active_worker_alerts AS
SELECT 
    wa.*,
    a.account_name,
    a.account_type
FROM worker_alerts wa
JOIN accounts a ON wa.account_id = a.id
WHERE wa.is_resolved = FALSE
ORDER BY wa.created_at DESC;

-- Daily efficiency summary
CREATE OR REPLACE VIEW daily_efficiency_summary AS
SELECT 
    dws.account_id,
    a.account_name,
    dws.date,
    COUNT(*) as total_workers,
    AVG(dws.efficiency_score) as avg_efficiency,
    SUM(dws.avg_hashrate_24h) as total_hashrate,
    AVG(dws.uptime_percentage) as avg_uptime
FROM daily_worker_summaries dws
JOIN accounts a ON dws.account_id = a.id
GROUP BY dws.account_id, a.account_name, dws.date
ORDER BY dws.date DESC, a.account_name;

-- =====================================================
-- DATA RETENTION FUNCTIONS
-- =====================================================

-- Function to cleanup old pool stats (keep 3 days for 10-min data)
CREATE OR REPLACE FUNCTION cleanup_old_pool_stats()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM pool_stats 
    WHERE data_frequency = '10min' 
    AND created_at < NOW() - INTERVAL '3 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old worker data (keep 7 days for hourly data)
CREATE OR REPLACE FUNCTION cleanup_old_worker_data()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM workers 
    WHERE data_type = 'hourly' 
    AND created_at < NOW() - INTERVAL '7 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old API logs (keep 30 days)
CREATE OR REPLACE FUNCTION cleanup_old_api_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM api_call_logs 
    WHERE created_at < NOW() - INTERVAL '30 days';
    
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
-- INITIAL DATA AND CONFIGURATION
-- =====================================================

-- Insert default configuration if needed
INSERT INTO accounts (account_name, account_type, email, coin_type) 
VALUES ('system', 'main', 'system@antpool.com', 'BTC')
ON CONFLICT (account_name) DO NOTHING;

-- =====================================================
-- PERFORMANCE OPTIMIZATION
-- =====================================================

-- Analyze tables for better query planning
ANALYZE accounts;
ANALYZE account_balances;
ANALYZE hashrates;
ANALYZE workers;
ANALYZE daily_worker_summaries;
ANALYZE worker_alerts;
ANALYZE payment_history;
ANALYZE pool_stats;
ANALYZE api_call_logs;

-- =====================================================
-- COMMENTS FOR DOCUMENTATION
-- =====================================================

COMMENT ON TABLE accounts IS 'Main and sub-accounts with hierarchical structure';
COMMENT ON TABLE account_balances IS 'Account balance history - kept forever';
COMMENT ON TABLE hashrates IS 'Pool-level hashrate data - kept forever';
COMMENT ON TABLE workers IS 'Individual worker data - 7 day retention for hourly, forever for daily';
COMMENT ON TABLE daily_worker_summaries IS 'Daily aggregated worker performance - kept forever';
COMMENT ON TABLE worker_alerts IS 'Worker alerts and notifications - 14 day retention for resolved';
COMMENT ON TABLE payment_history IS 'Payment transactions - kept forever';
COMMENT ON TABLE pool_stats IS 'Pool statistics - 3 day retention for 10-min data';
COMMENT ON TABLE api_call_logs IS 'API usage tracking - 30 day retention';

-- Schema setup complete
SELECT 'Antpool database schema created successfully with data retention policies' as status;

