"""
Migration: Create superadmin_notifications table and indexes.
Run with: python scripts/migrate_superadmin_notifications.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text

RAW_URL = os.environ.get("DATABASE_URL", "")
SYNC_URL = RAW_URL.replace("postgresql+asyncpg", "postgresql")

engine = create_engine(SYNC_URL, echo=False)

DDL = """
CREATE TABLE IF NOT EXISTS superadmin_notifications (
    id                      VARCHAR(36) PRIMARY KEY,
    title                   VARCHAR(300) NOT NULL,
    message                 TEXT NOT NULL,
    category                VARCHAR(50) NOT NULL,
    severity                VARCHAR(20) NOT NULL DEFAULT 'INFO',
    is_read                 BOOLEAN NOT NULL DEFAULT FALSE,
    read_at                 TIMESTAMPTZ,
    related_entity_type     VARCHAR(100),
    related_entity_id       VARCHAR(100),
    related_user_id         VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_superadmin_notifications_category ON superadmin_notifications (category);
CREATE INDEX IF NOT EXISTS ix_superadmin_notifications_severity ON superadmin_notifications (severity);
CREATE INDEX IF NOT EXISTS ix_superadmin_notifications_is_read ON superadmin_notifications (is_read);
CREATE INDEX IF NOT EXISTS ix_superadmin_notifications_created_at ON superadmin_notifications (created_at);
CREATE INDEX IF NOT EXISTS ix_sa_notif_category_is_read ON superadmin_notifications (category, is_read);
CREATE INDEX IF NOT EXISTS ix_sa_notif_severity_created ON superadmin_notifications (severity, created_at);
"""

# Seed some initial demo superadmin notifications if table is empty
SEED_DEMO = """
INSERT INTO superadmin_notifications (id, title, message, category, severity, is_read, created_at)
SELECT 'demo-sa-notif-1', 'Multiple Failed Admin Login Attempts', 'Multiple failed login attempts detected for account admin@chovique.com.', 'SECURITY', 'CRITICAL', FALSE, NOW() - INTERVAL '30 minutes'
WHERE NOT EXISTS (SELECT 1 FROM superadmin_notifications WHERE id = 'demo-sa-notif-1');

INSERT INTO superadmin_notifications (id, title, message, category, severity, is_read, created_at)
SELECT 'demo-sa-notif-2', 'New Admin Account Registered', 'Administrator account for Sarah Jenkins (sarah@chovique.com) was created.', 'ADMIN_MANAGEMENT', 'INFO', FALSE, NOW() - INTERVAL '2 hours'
WHERE NOT EXISTS (SELECT 1 FROM superadmin_notifications WHERE id = 'demo-sa-notif-2');

INSERT INTO superadmin_notifications (id, title, message, category, severity, is_read, created_at)
SELECT 'demo-sa-notif-3', 'Platform Security Configuration Updated', 'Admin session timeout and lockout duration settings were updated.', 'PLATFORM_SYSTEM', 'WARNING', TRUE, NOW() - INTERVAL '1 day'
WHERE NOT EXISTS (SELECT 1 FROM superadmin_notifications WHERE id = 'demo-sa-notif-3');

INSERT INTO superadmin_notifications (id, title, message, category, severity, is_read, created_at)
SELECT 'demo-sa-notif-4', 'Monthly Revenue Target Milestone Reached', 'Store revenue exceeded the ₹500,000 threshold for the current billing cycle.', 'BUSINESS', 'INFO', TRUE, NOW() - INTERVAL '2 days'
WHERE NOT EXISTS (SELECT 1 FROM superadmin_notifications WHERE id = 'demo-sa-notif-4');
"""

def main():
    with engine.connect() as conn:
        print("Creating superadmin_notifications table and indexes...")
        conn.execute(text(DDL))
        conn.execute(text(SEED_DEMO))
        conn.commit()
        print("Done! superadmin_notifications table created and seeded.")

if __name__ == "__main__":
    main()
