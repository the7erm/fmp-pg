
import sys
if "../" not in sys.path:
    sys.path.append("../")

from fmp_utils.db_session import session, Session

def do_commit(*objs):
    for obj in objs:
        _session = Session.object_session(obj)
        if _session:
            _session.commit()
        else:
            session.add(obj)
            session.commit()
