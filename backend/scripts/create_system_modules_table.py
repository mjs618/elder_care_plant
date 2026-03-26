"""
Create system_modules table manually.
Run this script to create the table.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import get_settings


CREATE_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS system_modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    slug VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    version VARCHAR(50) DEFAULT '1.0.0' NOT NULL,
    permissions TEXT DEFAULT '' NOT NULL,
    router_prefix VARCHAR(200) NOT NULL,
    is_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    disable_reason TEXT,
    changelog TEXT,
    updated_by VARCHAR(100)
)
'''

CREATE_INDEX_SQL = '''
CREATE INDEX IF NOT EXISTS ix_system_modules_slug ON system_modules(slug)
'''


async def create_table():
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)

    async with engine.connect() as conn:
        # Create table
        await conn.execute(text(CREATE_TABLE_SQL))
        await conn.commit()
        print('system_modules table created')

        # Create index
        await conn.execute(text(CREATE_INDEX_SQL))
        await conn.commit()
        print('index created')

    await engine.dispose()
    print('Done!')


if __name__ == "__main__":
    asyncio.run(create_table())
