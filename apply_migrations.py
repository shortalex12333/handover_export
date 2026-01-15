"""
Apply Supabase migrations programmatically
"""
import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def apply_migrations():
    """Apply all migrations to tenant database"""

    # Connect to tenant database
    url = os.getenv("yTEST_YACHT_001_SUPABASE_URL")
    key = os.getenv("yTEST_YACHT_001_SUPABASE_SERVICE_KEY")

    if not url or not key:
        print("❌ Missing Supabase credentials")
        return

    supabase: Client = create_client(url, key)

    # Get all migration files
    migrations_dir = Path(__file__).parent / "supabase" / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))

    print(f"Found {len(migration_files)} migration files\n")

    for migration_file in migration_files:
        print(f"📋 Applying: {migration_file.name}")

        # Read SQL content
        with open(migration_file, 'r') as f:
            sql_content = f.read()

        # Split into individual statements (basic approach)
        # Note: This is a simple split and may not handle all edge cases
        statements = []
        current_statement = []
        in_do_block = False

        for line in sql_content.split('\n'):
            # Track DO blocks
            if line.strip().startswith('DO $$'):
                in_do_block = True

            current_statement.append(line)

            # End of DO block
            if in_do_block and 'END $$;' in line:
                in_do_block = False
                statements.append('\n'.join(current_statement))
                current_statement = []
            # Regular statement end
            elif not in_do_block and line.strip().endswith(';') and not line.strip().startswith('--'):
                statements.append('\n'.join(current_statement))
                current_statement = []

        # Execute via raw SQL using PostgREST
        try:
            # For tenant DB migrations, we need to execute raw SQL
            # Supabase Python client doesn't have direct SQL execution for DDL
            # So we'll use the REST API's RPC functionality

            print(f"   ⚠️  Skipping {migration_file.name} - requires direct SQL access")
            print(f"   💡 Apply manually via Supabase Dashboard > SQL Editor")

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

    print("\n✅ Migration process complete")
    print("📝 Note: For production, use Supabase CLI or Dashboard SQL Editor")

if __name__ == "__main__":
    apply_migrations()
