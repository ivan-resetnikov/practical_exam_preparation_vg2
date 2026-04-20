"""
Praktisk eksamen forberedelse Copyright (c) 2026 ved Reshetnikov Ivan - alle rettigheter forbeholdt.

db.py - SQLite3-powered database, managed by defined abstractions.
"""

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

import logging
import sqlite3
import enum
import datetime



logger = logging.getLogger("db.py")
logger.setLevel(logging.DEBUG)


sql_connection = None
sql_cursor = None



class Error:
    SUCCESS: int = 0
    FAILED_TO_CREATE_DB: int = 1



class TicketState(enum.Enum):
    NOT_STARTED: int = 0
    DEALING_WITH: int = 1
    SOLVED: int = 2
    FAILED: int = 3



class UserLoginStatus(enum.Enum):
    OK: int = 0
    EMAIL_NOT_FOUND: int = 1
    INCORRECT_PASSWORD: int = 2



class Ticket:
    def __init__(self):
        self.primary_key: int = -1

        self.state: TicketState = TicketState.NOT_STARTED
        self.reporter_name: str = ""
        self.reporter_summary: str = ""
        self.registration_time: datetime.datetime = datetime.datetime.fromtimestamp(0)
    

    @classmethod
    def create(self, p_reporter_name: str, p_reporter_summary: str, p_registration_time: datetime.datetime=datetime.datetime.now()):
        t = Ticket()

        t.state = TicketState.NOT_STARTED
        t.reporter_name = p_reporter_name
        t.reporter_summary = p_reporter_summary
        t.registration_time = p_registration_time

        # TODO(vanya): Flush to SQL and gain a primary key
        sql_cursor.execute(
            """
            INSERT INTO tickets (state, reporter_name, reporter_summary, registration_time) VALUES (?, ?, ?, ?)
            """,
            (self.state.value, self.reporter_name, self.reporter_summary, self.registration_time)
        )

        t.primary_key = sql_cursor.lastrowid

        logger.info(f"Created new ticket. reporter_name={p_reporter_name}, reporter_summary={p_reporter_summary}")

        return t
    

    @classmethod
    def load_from_sql_row(cls, p_sql_row: tuple):
        t = Ticket()

        t.primary_key = p_sql_row[0]

        t.state = TicketState(p_sql_row[1])
        t.reporter_name = p_sql_row[2]
        t.reporter_summary = p_sql_row[3]
        t.registration_time = p_sql_row[4]

        return t


    def flush_to_database(self) -> None:
        global sql_connection
        global sql_cursor

        assert sql_connection != None, "sql_connection is not defined! Cannot save data! Run `db.init()`!"
        assert sql_cursor != None, "sql_cursor is not defined! Cannot save data! Run `db.init()`!"
        
        if not sql_connection:
            logger.critical("sql_connection is not defined! Cannot save data! Run `db.init()`!")
        if not sql_cursor:
            logger.critical("sql_cursor is not defined! Cannot save data! Run `db.init()`!")

        sql_cursor.execute(
            """
            UPDATE tickets
            SET state = ?, reporter_name = ?, reporter_summary = ?, registration_time = ?
            WHERE id = ?
            """,
            (self.state.value, self.reporter_name, self.reporter_summary, self.registration_time, self.primary_key)
        )

        sql_connection.commit()



class User:
    def __init__(self):
        self.primary_key: int = -1
        self.email: str = ""
        self.password: str = ""
    

    @classmethod
    def load_from_sql_row(self, p_sql_row: tuple):
        new_user: User = User()

        new_user.primary_key = int(p_sql_row[0])
        new_user.email = p_sql_row[1]
        new_user.password = p_sql_row[2]

        return new_user


    @classmethod
    def load_all_users(self) -> list:
        global sql_cursor

        sql_cursor.execute(
            """
            SELECT * FROM users
            """
        )

        rows = sql_cursor.fetchall()
        output_users: list[User] = []

        for row in rows:
            output_users.append(User.load_from_sql_row(row))

        return output_users
    

    @classmethod
    def create(self, p_email: str, p_password: str):
        new_user: User = User()

        new_user.email = p_email
        new_user.password = p_password

        # TODO(vanya): Flush to SQL and gain a primary key
        sql_cursor.execute(
            """
            INSERT INTO users (email, password) VALUES (?, ?)
            """,
            (self.email, self.password)
        )

        new_user.primary_key = sql_cursor.lastrowid

        return new_user 
    

    def flush_to_database(self) -> None:
        global sql_connection
        global sql_cursor

        assert sql_connection != None, "sql_connection is not defined! Cannot save data! Run `db.init()`!"
        assert sql_cursor != None, "sql_cursor is not defined! Cannot save data! Run `db.init()`!"
        
        if not sql_connection:
            logger.critical("sql_connection is not defined! Cannot save data! Run `db.init()`!")
        if not sql_cursor:
            logger.critical("sql_cursor is not defined! Cannot save data! Run `db.init()`!")

        sql_cursor.execute(
            """
            UPDATE users
            SET email = ?, password = ?
            WHERE id = ?
            """,
            (self.email, self.password, self.primary_key)
        )

        sql_connection.commit()



def init() -> str:
    global sql_connection
    global sql_cursor

    try:
        logger.info("Initialized database module")

        sql_connection = sqlite3.connect("tickets.db")
        sql_cursor = sql_connection.cursor()

        sql_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state INTEGER NOT NULL DEFAULT 0,
                reporter_name TEXT NOT NULL,
                reporter_summary TEXT,
                registration_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        sql_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                password TEXT NOT NULL
            )
            """
        )
    except sqlite3.Error as e:
        logger.critical(f"Failed to initialise the SQLite3 database! Because of the following error: {e}")
        return Error.FAILED_TO_CREATE_DB

    return Error.SUCCESS


def load_all_tickets() -> list[Ticket]:
    global sql_cursor

    assert sql_cursor != None, "sql_cursor is not defined! Cannot save data! Run `db.init()`!"

    if not sql_cursor:
        logger.critical("sql_cursor is not defined! Cannot save data! Run `db.init()`!")

    sql_cursor.execute(
        """
        SELECT * FROM tickets
        """
    )

    rows = sql_cursor.fetchall()
    output_tickets: list[Ticket] = []

    for row in rows:
        output_tickets.append(Ticket.load_from_sql_row(row))

    return output_tickets


def load_all_assigned_tickets() -> list[Ticket]:
    global sql_cursor

    assert sql_cursor != None, "sql_cursor is not defined! Cannot save data! Run `db.init()`!"

    if not sql_cursor:
        logger.critical("sql_cursor is not defined! Cannot save data! Run `db.init()`!")

    sql_cursor.execute(
        f"""
        SELECT * FROM tickets
            WHERE state = {TicketState.DEALING_WITH.value}
        """
    )

    rows = sql_cursor.fetchall()
    output_tickets: list[Ticket] = []

    for row in rows:
        output_tickets.append(Ticket.load_from_sql_row(row))

    return output_tickets


def load_not_started_ticket_range(p_from: int, p_to: int) -> list[Ticket]:
    global sql_cursor

    assert sql_cursor != None, "sql_cursor is not defined! Cannot save data! Run `db.init()`!"

    if not sql_cursor:
        logger.critical("sql_cursor is not defined! Cannot save data! Run `db.init()`!")

    sql_cursor.execute(
        f"""
        SELECT *
            FROM tickets
            WHERE id BETWEEN ? AND ?
                AND state = {TicketState.NOT_STARTED.value}
        """, (p_from, p_to)
    )

    rows = sql_cursor.fetchall()
    output_tickets: list[Ticket] = []

    for row in rows:
        output_tickets.append(Ticket.load_from_sql_row(row))

    return output_tickets


def attempt_login(p_email: str, p_password: str) -> tuple[User, UserLoginStatus]:
    # NOTE(vanya): Potential friction point beacuse we a are re-loading all the users every call

    for user in User.load_all_users():
        if user.email == p_email:
            if user.password == p_password:
                return (user, UserLoginStatus.OK)
            
            return (user, UserLoginStatus.INCORRECT_PASSWORD)
    
    return (None, UserLoginStatus.EMAIL_NOT_FOUND)
