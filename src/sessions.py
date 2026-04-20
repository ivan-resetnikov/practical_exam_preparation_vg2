import urllib.parse
import datetime
import secrets
import logging

from .db import User



logger = logging.getLogger("sessions.py")
logger.setLevel(logging.DEBUG)



class SessionValidity:
    OK: int = 0
    NOT_FOUND: int = 1
    INCORRECT: int = 2
    EXPIRED: int = 3



class Session:
    def __init__(self):
        self.id: str = ""
        self.expiration_datetime: datetime.datetime = datetime.datetime.fromtimestamp(0)



def search_session_id(p_id: str) -> Session|None:
    global sessions
    
    for session in sessions:
        if session.id == p_id:
            return session
    return None


def check_session_id_validity(p_session_id: str) -> SessionValidity:
    global sessions

    if not p_session_id:
        return SessionValidity.INCORRECT
    
    found_session: Session|None = search_session_id(p_session_id)

    if not found_session:
        return SessionValidity.NOT_FOUND

    if found_session.expiration_datetime < datetime.datetime.now():
        logger.debug(f"Session `{found_session.id}` expired, removing.")
        sessions.remove(found_session)
        return SessionValidity.EXPIRED

    return SessionValidity.OK


def begin_session(p_user: db.User, p_duration_minutes: int=15) -> Session:
    global sessions
    
    new_session = Session()
    new_session.id = secrets.token_urlsafe(32)
    new_session.expiration_datetime = datetime.datetime.now() + datetime.timedelta(minutes=p_duration_minutes)

    sessions.append(new_session)
    return new_session



sessions: list[Session] = []
