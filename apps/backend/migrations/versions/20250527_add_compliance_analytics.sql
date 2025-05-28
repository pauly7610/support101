-- Add CCPA opt-out column
ALTER TABLE users ADD COLUMN IF NOT EXISTS data_sale_optout BOOLEAN DEFAULT FALSE;

-- Create escalation tracking table
CREATE TABLE IF NOT EXISTS escalations (
    id UUID PRIMARY KEY,
    ticket_id UUID REFERENCES tickets(id),
    escalation_time INTERVAL,
    created_at TIMESTAMP DEFAULT NOW()
);
