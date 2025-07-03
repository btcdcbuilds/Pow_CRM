-- Raw Data Storage Schema for Antpool API Responses
-- Industry Standard: Store raw responses first, parse later

-- Table for storing raw API responses
CREATE TABLE IF NOT EXISTS raw_api_responses (
    id SERIAL PRIMARY KEY,
    account_id INTEGER,
    account_name TEXT NOT NULL,
    api_endpoint TEXT NOT NULL,
    request_params JSONB,
    raw_response TEXT NOT NULL,
    response_size INTEGER,
    worker_count INTEGER DEFAULT 0,
    api_call_duration_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE,
    processing_error TEXT,
    retry_count INTEGER DEFAULT 0
);

-- Index for efficient querying
CREATE INDEX IF NOT EXISTS idx_raw_api_responses_account ON raw_api_responses(account_name);
CREATE INDEX IF NOT EXISTS idx_raw_api_responses_endpoint ON raw_api_responses(api_endpoint);
CREATE INDEX IF NOT EXISTS idx_raw_api_responses_processed ON raw_api_responses(processed);
CREATE INDEX IF NOT EXISTS idx_raw_api_responses_created_at ON raw_api_responses(created_at);

-- Table for tracking processing status
CREATE TABLE IF NOT EXISTS raw_data_processing_log (
    id SERIAL PRIMARY KEY,
    batch_id UUID DEFAULT gen_random_uuid(),
    raw_response_id INTEGER REFERENCES raw_api_responses(id),
    processing_step TEXT,
    status TEXT CHECK (status IN ('started', 'completed', 'failed', 'skipped')),
    records_processed INTEGER DEFAULT 0,
    error_message TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- View for unprocessed raw data
CREATE OR REPLACE VIEW unprocessed_raw_data AS
SELECT 
    id,
    account_name,
    api_endpoint,
    raw_response,
    worker_count,
    created_at,
    retry_count
FROM raw_api_responses 
WHERE processed = FALSE 
ORDER BY created_at ASC;

-- View for processing statistics
CREATE OR REPLACE VIEW raw_data_stats AS
SELECT 
    account_name,
    api_endpoint,
    COUNT(*) as total_responses,
    SUM(worker_count) as total_workers,
    COUNT(CASE WHEN processed = TRUE THEN 1 END) as processed_responses,
    COUNT(CASE WHEN processed = FALSE THEN 1 END) as pending_responses,
    COUNT(CASE WHEN processing_error IS NOT NULL THEN 1 END) as error_responses,
    MAX(created_at) as last_fetch,
    AVG(api_call_duration_ms) as avg_api_duration_ms
FROM raw_api_responses 
GROUP BY account_name, api_endpoint
ORDER BY account_name, api_endpoint;

-- Function to mark raw data as processed
CREATE OR REPLACE FUNCTION mark_raw_data_processed(
    p_raw_response_id INTEGER,
    p_records_processed INTEGER DEFAULT 0,
    p_error_message TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE raw_api_responses 
    SET 
        processed = CASE WHEN p_error_message IS NULL THEN TRUE ELSE FALSE END,
        processed_at = NOW(),
        processing_error = p_error_message
    WHERE id = p_raw_response_id;
    
    -- Log the processing result
    INSERT INTO raw_data_processing_log (
        raw_response_id,
        processing_step,
        status,
        records_processed,
        error_message,
        processing_time_ms
    ) VALUES (
        p_raw_response_id,
        'parse_workers',
        CASE WHEN p_error_message IS NULL THEN 'completed' ELSE 'failed' END,
        p_records_processed,
        p_error_message,
        0
    );
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Function to get processing statistics
CREATE OR REPLACE FUNCTION get_processing_stats()
RETURNS TABLE (
    total_raw_responses BIGINT,
    processed_responses BIGINT,
    pending_responses BIGINT,
    error_responses BIGINT,
    total_workers BIGINT,
    processing_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_raw_responses,
        COUNT(CASE WHEN processed = TRUE THEN 1 END) as processed_responses,
        COUNT(CASE WHEN processed = FALSE AND processing_error IS NULL THEN 1 END) as pending_responses,
        COUNT(CASE WHEN processing_error IS NOT NULL THEN 1 END) as error_responses,
        COALESCE(SUM(worker_count), 0) as total_workers,
        CASE 
            WHEN COUNT(*) > 0 THEN 
                ROUND((COUNT(CASE WHEN processed = TRUE THEN 1 END) * 100.0 / COUNT(*)), 2)
            ELSE 0 
        END as processing_rate
    FROM raw_api_responses;
END;
$$ LANGUAGE plpgsql;

