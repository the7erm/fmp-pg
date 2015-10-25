from db_session import session
from file import User, UserFileInfo, File
from sqlalchemy.sql import not_, and_

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
result = session.query(File).from_statement(
    """SELECT f.*
       FROM files f
       LEFT JOIN user_file_info usi ON user_id = :user_id AND
                                       usi.file_id = f.id
       WHERE usi.file_id IS NULL""")\
    .params(user_id='1')
for r in result.all():
    print("r:",r)