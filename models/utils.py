
import sys
if "../" not in sys.path:
    sys.path.append("../")

from fmp_utils.db_session import Session, session_scope

def do_commit(*objs):
    with session_scope() as session:
        for obj in objs:
            _session = Session.object_session(obj)
            if _session:
                _session.commit()
            else:
                session.add(obj)
                session.commit()
