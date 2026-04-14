"""
Praktisk eksamen forberedelse Copyright (c) 2026 ved Reshetnikov Ivan - alle rettigheter forbeholdt.
"""

import sqlite3
import logging



logger = logging.getLogger("db.py")
logger.setLevel(logging.DEBUG)


sql_connection = None
sql_cursor = None



class Error:
    SUCCESS: int = 0
    FAILED_TO_CREATE_DB: int = 1



class Ticket:
    def __init__():
        self.primary_key: int = -1
    

    def flush(self) -> None:
        global sql_connection
        global sql_cursor

        assert sql_connection != None, "sql_connection is not defined! Cannot save data! Run `db.create_database_sql_file()`!"
        assert sql_cursor != None, "sql_cursor is not defined! Cannot save data! Run `db.create_database_sql_file()`!"
        
        if not sql_connection:
            logger.critical("sql_connection is not defined! Cannot save data! Run `db.create_database_sql_file()`!")
        if not sql_cursor:
            logger.critical("sql_cursor is not defined! Cannot save data! Run `db.create_database_sql_file()`!")

        # TODO(vanya): Backups & recundancy
        # This is an exam assignment, thus,
        # the website does not need nor implements data integrity features of any kind.
        # 
        # In a production environment:
        # 
        # * We need RAID-1 at LEAST!
        #   See: https://en.wikipedia.org/wiki/Standard_RAID_levels
        # 
        # * Ensuring data recoverability AFTER the end-of-life for SQLite3 many years down the line,
        #   by making a copy of the database in a SIMPLE format like .csv
        # 
        # ...would ALL be MANDATORY!

        cursor.execute("INSERT INTO users (solved) VALUES (?)", (True))
        conn.commit()


    @classmethod
    def load(self, p_primary_key: int):
        t = Ticket()

        t.primary_key = p_primary_key

        return t



def create_database_sql_file() -> str:
    try:
        sql_connection = sqlite3.connect("tickets.db")
        sql_cursor = sql_connection.cursor()

        sql_cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            solved BOOLEAN DEFAULT FALSE
        )
        """)
    except sqlite3.Error as e:
        logger.critical(f"Failed to initialise the SQLite3 database! Because of the following error: {e}")
        return Error.FAILED_TO_CREATE_DB

    return Error.SUCCESS


def load_unsolved_ticket_range(p_from: int, p_to: int) -> list[Ticket]:
    pass
