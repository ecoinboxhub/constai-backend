import sys
import os
import time
import psutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

print('Python executable:', sys.executable)
print('Starting import test...')

p = psutil.Process()
print('Before import app.main: RSS MB=', round(p.memory_info().rss / 1024 / 1024, 2))
start = time.time()
from app.main import app
end = time.time()
print('After import app.main: RSS MB=', round(p.memory_info().rss / 1024 / 1024, 2))
print('Import time:', round(end - start, 2), 's')

# Trigger lifespan startup manually by entering context
import asyncio
async def run_lifespan_test():
    startup_start = time.time()
    async with app.router.lifespan_context(app):
        print('Within lifespan context: RSS MB=', round(p.memory_info().rss / 1024 / 1024, 2))
    startup_end = time.time()
    print('Lifespan elapsed:', round(startup_end - startup_start, 2), 's')

asyncio.run(run_lifespan_test())
print('Done')
