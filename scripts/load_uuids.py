import asyncio
import sys
sys.path.append(".")

from database.db import init_db, load_uuids_to_pool


async def main():
    await init_db()

    with open("uuids.txt") as f:
        uuids = [line.strip() for line in f if line.strip()]

    await load_uuids_to_pool(uuids, "germany")
    print(f"Загружено {len(uuids)} UUID в пул germany")


asyncio.run(main())