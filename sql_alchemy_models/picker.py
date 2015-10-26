from db_session import session
from file import User, UserFileInfo, File
from sqlalchemy.sql import not_, and_, text

user = session.query(User).filter(User.name == "erm").first()

if not user:
    user = User()
    user.name = "erm"
    session.add(user)
    session.commit()

print (user)
"""
dbsession.query( TableOne, TableTwo ).join( TableTwo ).filter( TableOne.id == TableTwo.id ).filter( TableTwo.id == 1 )
"""

"""
# This will get everything
# I want to restrict to only rows for specific user_ids
for f in session.query(File)\
                     .filter(File.user_file_info == None)\
                     .all():
    print("f:", f)
    # print("ufi:", ufi)
"""

def get_random_unplayed_for_user_id(user_id):
    result = session.query(File).from_statement(
        text("""SELECT f.*
           FROM files f
           LEFT JOIN user_file_info usi ON user_id = :user_id AND
                                           usi.file_id = f.id
           WHERE usi.file_id IS NULL
           ORDER BY random()
           LIMIT 1 """))\
        .params(user_id=user_id)
    return result.first()

f = get_random_unplayed_for_user_id(1)
print (f)