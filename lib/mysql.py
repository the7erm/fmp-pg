# lib/mysql.py -- Connect to mysql, run queries, fairly thread safe, but can bottle neck
#    Copyright (C) 2012 Eugene Miller <theerm@gmail.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

from warnings import filterwarnings
import sys, traceback, re, time, MySQLdb
filterwarnings('ignore', category = MySQLdb.Warning)

def gtk_wait(msg=None):
	gtk.threads_leave()
	if gtk.events_pending():
		if msg:
			print "pending:",msg
		gtk.main_iteration(False)
		gtk.threads_leave()

class MySql :
	"""
		Mysql class to simplify mysql queries.
	"""
	def __init__ (self, host = "", user = "", passwd = "", db = "", port = 3306):
		# print "Port:",port
		"""
			Initialize the database connection.
		"""
		self.conn = False
		self.cursorType = None
		self.host = host
		self.user = user
		self.port = port
		self.last_error = 0
		self.passwd = passwd
		self.db = db
		self.locked = False
		self.waiting = False
		self.locked_with = ""
		self.locked_with_args = ""
		self.queryNumber = 0
		self.queryCue = []
		self.logFp = None
		self.lastQuery = ""
		self.lastArgs = ()
		self.is_connected = False
		self.connect()
		
		
		
	def log(self,s):
		print "MySql:%s" % s
		return;
		"""
			Log mysql query activity.
		"""
		if not self.logFp:
			self.logFp = open("mysql.log",'a')
		l = "%s %s" % (time.strftime("[%Y-%m-%d %H:%M:%S]") ,s)
		print l
		self.logFp.write(l+"\n")
		self.logFp.flush()

	def connect(self):
		"""
			Connect to mysql server
		"""
		try:
			self.conn = MySQLdb.connect (self.host, self.user, self.passwd, self.db, self.port)
			self.is_connected = True
			self.setCursor(self.cursorType)
		except MySQLdb.Error, e:
			print "Error %d: %s" % (e.args[0], e.args[1])
			return
		
		

	def esc(self,s):
		"""
			Escape string so it's safe.
		"""
		return self.conn.escape_string(str(s))

	def lock(self, q, *args):
		"""
			Lock the object so multiple queries aren't getting sent until the previous
			query is completed.
		"""
		queryNumber = self.queryNumber
		while self.queryCue.count(queryNumber) >= 1:
			print "ALREADY IN LIST:%d" % queryNumber
			queryNumber += 1
			self.queryNumber += 1
		self.queryNumber += 1
		self.queryCue.append(queryNumber)
		# print "QUERY:%d %s args:%s" % (queryNumber, q, args)
		# self.log("QUERY:%d %s args:%s" % (queryNumber, q, args))
		# self.log("Started  query:%d" % queryNumber)
		shown = False
		checkTime = time.time()
		showCnt = 0
		try:
			idx = self.queryCue.index(queryNumber)
			# print "IDX:%s" % idx
			while idx != 0:
				if not shown:
					qLen = len(self.queryCue)
					self.log("WAITING: length:%d queryNumber:%d q:%s args:%s index:%d\nLAST QUERY:%s LAST ARGS:%s" % (qLen, queryNumber, q, args, idx, self.lastQuery, self.lastArgs))
					shown = True
				if checkTime < time.time() - 3:
					shown = False
					showCnt += 1
					checkTime = time.time() #reset the time.
				# time.sleep((0.005 * len(self.queryCue)))
				
				idx = self.queryCue.index(queryNumber)
				
		except ValueError:
			print "WAITING ERROR:%d is no longer in the list" % (queryNumber)
			pass
		self.lastQuery = q
		self.lastArgs = args
		# self.log("EXECUTING:%d:%s %s " % (queryNumber, q, args))
		return
		
	def unlock(self):
		"""
			Unlock the query.
		"""
		queryNumber = self.queryCue.pop(0)
		# print "mysql pop:%d" % queryNumber
		# self.log("Finished query:%d" % queryNumber)


	def query(self, q, *args):
		# print "q:",q
		"""
			Execute a query locking before hand
		"""
		self.lock(q, *args)
		self.ex(q, *args)
		self.unlock()

	def ex(self, q, *args):
		"""
			Execute a query, wrapped in error handling.
		"""
		try:
			# show = True
			# print q
			# print "db.ex q:%s args:%s" % (q, args)
			self.cursor.execute (q, *args)
			self.conn.commit()
			self.last_error = 0
		except MySQLdb.Error, e:
			"""
			Query: SELECT pos, plid FROM playlist ORDER BY pos

			Unhandled exception in thread started by
			Error in sys.excepthook:
			"""
			# Error 2014: Commands out of sync; you can't run this command now
			# Error 2013: Lost connection to MySQL server during query
			# Error 2006: MySQL server has gone away
			if e.args[0] in (2006, 2013, 2014):
				if e.args[0] == self.last_error:
					self.log("QUERY ERROR SAME AS LAST:%s Args:%s\nError %d: %s" % (q, args, e.args[0], e.args[1]))
					self.unlock()
					sys.exit(1)
				self.last_error = e.args[0]
				self.log("SLEEPING FOR A SECOND AND TRYING AGAIN")
				time.sleep(1)


				try:
					self.connect()
					self.cursor.execute (q, *args)
					self.conn.commit()
					self.ex(q,*args)
					return 
				except MySQLdb.Error, e:
					self.log("FAILED AFTER SLEEPING")
					self.log("QUERY ERROR:%s Args:%s\nError %d: %s" % (q, args, e.args[0], e.args[1]))
					sys.exit(1)
				self.last_error = 0
				
			else:
				self.log("QUERY ERROR:%s Args:%s\nError %d: %s" % (q, args, e.args[0], e.args[1]))
				self.unlock()
				sys.exit(1)
		# except:
		#	print "MAJOR ERROR EXECUTING !!! %s %s" % (q, args)
		#	traceback.print_stack()
			


	def getVar(self, q, *args):
		"""
			Get a signle variable.
		"""
		row = self.getRow(q, *args)
		if row:
			return row[0]
		else:
			return ''

	def setCursor(self, cursor=None):
		if not cursor:
			cursor=MySQLdb.cursors.Cursor
		if not self.conn:
			print "NO CONNECTION! User:", self.user, "Host:", self.host, "db:", self.db
			return
		self.cursor = self.conn.cursor(cursor)
		self.cursorType = cursor
	

	def getRow(self, q, *args):
		"""
			Get a row of data
		"""
		self.lock(q,*args)
		self.setCursor(MySQLdb.cursors.Cursor)
		self.ex(q, *args)
		row = self.cursor.fetchone()
		self.unlock()
		return row

	def getRows(self, q, *args):
		"""
			Get a list of data
		"""
		self.lock(q,*args)
		self.setCursor(MySQLdb.cursors.Cursor)
		self.ex(q, *args)
		rows = self.cursor.fetchall()
		self.unlock()
		return rows


	def getRowsList(self, q, *args):
		"""
			Get a list of lists of data.
		"""
		self.lock(q,*args)
		self.setCursor(MySQLdb.cursors.Cursor)
		self.ex(q, *args)
		rows = self.cursor.fetchall()

		rowsList = []
		for r in rows:
			newRow = []
			for c in r:
				newRow.append(c)
			rowsList.append(newRow)
		self.unlock()
		return rowsList

	def getAssoc(self, q, *args):
		"""
			Get a row of data in assoicative format
		"""
		self.lock(q,*args)
		self.setCursor(MySQLdb.cursors.DictCursor)
		self.ex(q, *args)
		row = self.cursor.fetchone()
		self.unlock()
		return row

	def getRowsAssoc(self, q, *args):
		"""
			Get a list of assoicative rows.
		"""
		self.lock(q,*args)
		self.setCursor(MySQLdb.cursors.DictCursor)
		self.ex(q, *args)
		rows = self.cursor.fetchall()
		self.unlock()
		return rows

	def page(self, q, start = 0, limit = 10, *args):
		"""
			Pager
		"""
		start = int(start)
		uq = q.upper()
		if uq.find("SQL_CALC_FOUND_ROWS") == -1:
			p = re.compile( 'SELECT (.*?) FROM', re.IGNORECASE)
			q = p.sub(r'SELECT SQL_CALC_FOUND_ROWS \1 FROM ', q)

		rows = self.getRowsAssoc(q + " LIMIT " + self.esc(start) + "," + self.esc(limit) , *args)
		total = self.getVar("SELECT FOUND_ROWS()")
		return {"total": total, "rows": rows}

	def __del__(self):
		"""
			Close the door behind us, and turn off the lights.
		"""
		if (self.conn):
			self.conn.commit()
			self.conn.close()
			self.conn = False

	def close(self):
		"""
			Close the db connection.
		"""
		if (self.conn):
			self.conn.commit()
			self.conn.close()
			self.conn = False



