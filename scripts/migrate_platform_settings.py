"""
Migration: Create platform_settings table and seed singleton row.
Run with: python scripts/migrate_platform_settings.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text, inspect

RAW_URL = os.environ.get("DATABASE_URL", "")
SYNC_URL = RAW_URL.replace("postgresql+asyncpg", "postgresql")

engine = create_engine(SYNC_URL, echo=False)

DDL = """
CREATE TABLE IF NOT EXISTS platform_settings (
    id                              VARCHAR(36)   PRIMARY KEY,

    -- Store Configuration
    store_front_name                VARCHAR(200)  NOT NULL DEFAULT 'Chovique Luxury Chocolates',
    support_email                   VARCHAR(255)  NOT NULL DEFAULT 'support@chovique.com',
    support_phone                   VARCHAR(30)   NOT NULL DEFAULT '+91 98765 43210',
    store_address                   TEXT                   DEFAULT '',
    city                            VARCHAR(100)           DEFAULT '',
    state                           VARCHAR(100)           DEFAULT '',
    country                         VARCHAR(100)  NOT NULL DEFAULT 'India',
    pincode                         VARCHAR(20)            DEFAULT '',
    base_currency                   VARCHAR(10)   NOT NULL DEFAULT 'INR',
    timezone                        VARCHAR(60)   NOT NULL DEFAULT 'Asia/Kolkata',
    business_status                 VARCHAR(20)   NOT NULL DEFAULT 'active',

    -- Payment & Shipping
    cod_enabled                     BOOLEAN       NOT NULL DEFAULT TRUE,
    gst_rate                        FLOAT         NOT NULL DEFAULT 18.0,
    platform_fee                    FLOAT         NOT NULL DEFAULT 0.0,
    standard_shipping_charge        FLOAT         NOT NULL DEFAULT 50.0,
    free_shipping_min_order         FLOAT         NOT NULL DEFAULT 500.0,
    maximum_cod_order_value         FLOAT         NOT NULL DEFAULT 5000.0,

    -- Customer & Order Settings
    customer_registration_enabled   BOOLEAN       NOT NULL DEFAULT TRUE,
    guest_checkout_enabled          BOOLEAN       NOT NULL DEFAULT TRUE,
    minimum_order_value             FLOAT         NOT NULL DEFAULT 100.0,
    order_cancellation_enabled      BOOLEAN       NOT NULL DEFAULT TRUE,
    cancellation_time_limit         INTEGER       NOT NULL DEFAULT 24,
    return_refund_enabled           BOOLEAN       NOT NULL DEFAULT TRUE,

    -- System & Security
    maintenance_mode                BOOLEAN       NOT NULL DEFAULT FALSE,
    admin_session_timeout           INTEGER       NOT NULL DEFAULT 60,
    max_login_attempts              INTEGER       NOT NULL DEFAULT 5,
    account_lockout_duration        INTEGER       NOT NULL DEFAULT 30,
    require_admin_password_change   BOOLEAN       NOT NULL DEFAULT FALSE,

    -- Audit
    created_at                      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_by                      VARCHAR(36)   REFERENCES users(id) ON DELETE SET NULL
);
"""

SEED = """
INSERT INTO platform_settings (
    id, store_front_name, support_email, support_phone,
    store_address, city, state, country, pincode,
    base_currency, timezone, business_status,
    cod_enabled, gst_rate, platform_fee, standard_shipping_charge,
    free_shipping_min_order, maximum_cod_order_value,
    customer_registration_enabled, guest_checkout_enabled,
    minimum_order_value, order_cancellation_enabled, cancellation_time_limit,
    return_refund_enabled, maintenance_mode, admin_session_timeout,
    max_login_attempts, account_lockout_duration, require_admin_password_change
) VALUES (
    'singleton', 'Chovique Luxury Chocolates', 'support@chovique.com', '+91 98765 43210',
    '', '', '', 'India', '',
    'INR', 'Asia/Kolkata', 'active',
    TRUE, 18.0, 0.0, 50.0,
    500.0, 5000.0,
    TRUE, TRUE,
    100.0, TRUE, 24,
    TRUE, FALSE, 60,
    5, 30, FALSE
) ON CONFLICT (id) DO NOTHING;
"""

def main():
    with engine.connect() as conn:
        print("Creating platform_settings table...")
        conn.execute(text(DDL))
        conn.execute(text(SEED))
        conn.commit()
        print("Done! platform_settings table created and singleton row seeded.")

if __name__ == "__main__":
    main()
