import os
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

ROOT_DIR = Path.cwd().parent
load_dotenv(ROOT_DIR / '.env')
load_dotenv(Path.cwd() / '.env', override=True)

conn_str = os.getenv('DATABASE_URL')
print('Using DB URL:', conn_str)
engine = create_engine(conn_str)

print('Current state before deletion:')
with engine.connect() as conn:
    count = conn.execute(text('SELECT COUNT(*) FROM projects')).scalar()
    ids = [r[0] for r in conn.execute(text('SELECT id FROM projects ORDER BY id')).fetchall()]
    print(f'Total projects: {count}')
    print(f'Project IDs: {ids}')

print('\nDeleting all dependent rows...')
with engine.begin() as conn:
    child_tables = [
        'delay_predictions',
        'cost_estimates',
        'equipment',
        'safety_findings',
        'employees',
        'purchase_orders',
        'transactions',
        'project_documents',
    ]
    for table in child_tables:
        result = conn.execute(text(f"DELETE FROM {table} WHERE project_id IN (SELECT id FROM projects)"))
        print(f'Deleted from {table}: {result.rowcount}')

    print('Deleting all projects...')
    result = conn.execute(text('DELETE FROM projects'))
    print(f'Deleted projects: {result.rowcount}')

print('\nState after deletion (same transaction):')
with engine.connect() as conn:
    count = conn.execute(text('SELECT COUNT(*) FROM projects')).scalar()
    ids = [r[0] for r in conn.execute(text('SELECT id FROM projects ORDER BY id')).fetchall()]
    print(f'Total projects: {count}')
    print(f'Project IDs: {ids}')
