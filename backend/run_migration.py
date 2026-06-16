import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.core.config import settings
from sqlalchemy import create_engine, text

engine = create_engine(settings.database_url)
with engine.connect() as conn:
    for table, col in [('projects','client_uuid'),('project_documents','client_uuid'),('workforce','client_uuid')]:
        try:
            conn.execute(text('ALTER TABLE %s ADD COLUMN %s VARCHAR(64)' % (table, col)))
            conn.commit()
            print('Added %s to %s' % (col, table))
        except Exception as e:
            conn.rollback()
            print('%s.%s: %s' % (table, col, str(e).split('\n')[0]))
print('Migration check complete.')
