"""fix_gender_enum_values

Revision ID: 20260326_fix_gender_enum
Revises: 20260326_add_rls_policies
Create Date: 2026-03-26

Fixes the Gender enum values to match the model definition:
- MALE -> M
- FEMALE -> F
- OTHER -> O

"""
from alembic import op
import sqlalchemy as sa


revision = "20260326_fix_gender_enum"
down_revision = "20260326_add_rls_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    
    conn.execute(sa.text("""
        ALTER TYPE gender RENAME TO gender_old;
    """))
    
    conn.execute(sa.text("""
        CREATE TYPE gender AS ENUM ('M', 'F', 'O');
    """))
    
    conn.execute(sa.text("""
        ALTER TABLE patients 
        ALTER COLUMN gender TYPE gender 
        USING CASE 
            WHEN gender::text = 'MALE' THEN 'M'::gender
            WHEN gender::text = 'FEMALE' THEN 'F'::gender
            WHEN gender::text = 'OTHER' THEN 'O'::gender
        END;
    """))
    
    conn.execute(sa.text("""
        DROP TYPE gender_old;
    """))
    
    conn.commit()


def downgrade() -> None:
    conn = op.get_bind()
    
    conn.execute(sa.text("""
        ALTER TYPE gender RENAME TO gender_old;
    """))
    
    conn.execute(sa.text("""
        CREATE TYPE gender AS ENUM ('MALE', 'FEMALE', 'OTHER');
    """))
    
    conn.execute(sa.text("""
        ALTER TABLE patients 
        ALTER COLUMN gender TYPE gender 
        USING CASE 
            WHEN gender::text = 'M' THEN 'MALE'::gender
            WHEN gender::text = 'F' THEN 'FEMALE'::gender
            WHEN gender::text = 'O' THEN 'OTHER'::gender
        END;
    """))
    
    conn.execute(sa.text("""
        DROP TYPE gender_old;
    """))
    
    conn.commit()
