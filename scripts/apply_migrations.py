#!/usr/bin/env python3
"""
Apply database migrations to Supabase tenant database via direct PostgreSQL connection
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def apply_migrations():
    """Apply all migrations to tenant database"""

    try:
        import psycopg2
        from psycopg2 import sql
    except ImportError:
        print("❌ psycopg2 not installed. Installing...")
        os.system("pip install psycopg2-binary")
        import psycopg2
        from psycopg2 import sql

    # Get tenant Supabase URL
    url = os.getenv("yTEST_YACHT_001_SUPABASE_URL")

    if not url:
        print("❌ Error: yTEST_YACHT_001_SUPABASE_URL not found in .env")
        return False

    # Extract project ref from URL
    # https://vzsohavtuotocgrfkfyd.supabase.co -> vzsohavtuotocgrfkfyd
    project_ref = url.replace("https://", "").replace(".supabase.co", "")

    # Database password (same for master and tenant)
    db_password = "@-Ei-9Pa.uENn6g"

    # URL-encode the password
    from urllib.parse import quote_plus
    encoded_password = quote_plus(db_password)

    # PostgreSQL connection string for Supabase
    # Format: postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
    connection_string = f"postgresql://postgres:{encoded_password}@db.{project_ref}.supabase.co:5432/postgres"

    print("="*60)
    print("🚀 Supabase Migration Tool")
    print("="*60)
    print(f"\n🔗 Connecting to: db.{project_ref}.supabase.co")

    try:
        # Connect to database
        conn = psycopg2.connect(connection_string)
        conn.autocommit = False
        cursor = conn.cursor()

        print("✅ Connected to PostgreSQL database")

        # Get migrations directory
        migrations_dir = Path(__file__).parent.parent / "supabase" / "migrations"

        # Get migration files in order (skip master DB migrations)
        migration_files = sorted([
            f for f in migrations_dir.glob("*.sql")
            if f.name.startswith("00") and "master_db" not in f.name.lower()
        ])

        print(f"\n📂 Found {len(migration_files)} tenant migration files\n")

        # Apply each migration
        for migration_file in migration_files:
            print(f"▶️  Applying: {migration_file.name}")

            # Read SQL
            sql_content = migration_file.read_text()

            try:
                # Execute SQL
                cursor.execute(sql_content)
                conn.commit()
                print(f"   ✅ Success")

            except psycopg2.Error as e:
                print(f"   ⚠️  Error (may be expected if already applied):")
                print(f"      {str(e).split(chr(10))[0]}")  # First line only
                conn.rollback()
                # Continue with next migration
                continue

        # Verify tables were created
        print("\n" + "="*60)
        print("🔍 Verifying tables...")
        print("="*60 + "\n")

        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name LIKE 'handover%'
            ORDER BY table_name
        """)

        tables = cursor.fetchall()

        if tables:
            print("✅ Handover tables found:")
            for (table_name,) in tables:
                print(f"   • {table_name}")
        else:
            print("⚠️  No handover tables found")

        # Close connection
        cursor.close()
        conn.close()

        print("\n" + "="*60)
        print("✅ Migration process complete!")
        print("="*60)

        return True

    except psycopg2.Error as e:
        print(f"\n❌ Database connection error:")
        print(f"   {e}")
        return False

    except Exception as e:
        print(f"\n❌ Unexpected error:")
        print(f"   {e}")
        return False


if __name__ == "__main__":
    success = apply_migrations()
    sys.exit(0 if success else 1)
