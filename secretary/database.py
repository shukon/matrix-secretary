from mautrix.util.async_db import UpgradeTable, Connection

# Database
upgrade_table = UpgradeTable()


@upgrade_table.register(description="Initial revision")
async def upgrade_v1(conn: Connection) -> None:
    await conn.execute(
        """CREATE TABLE rooms (
            policy_key        TEXT,
            room_key  TEXT,
            matrix_room_id   TEXT,
            PRIMARY KEY (policy_key, room_key)
         )""")
    await conn.execute(
        """CREATE TABLE policies ( 
            policy_key        TEXT,
            policy_json       TEXT, 
            PRIMARY KEY (policy_key)
        )"""
    )


def get_upgrade_table():
    return upgrade_table
