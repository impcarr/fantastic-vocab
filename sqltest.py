import sqlite3

conn = sqlite3.connect('vocab.db')
c = conn.cursor()

# Sample data (replace with your actual values)
filepath = '/path/to/file.txt'
title = 'This is a File Title'
author = 'John Doe'
date = '2024-05-05'

# Prepare the statement with placeholders
sql = """INSERT OR REPLACE INTO library (filepath, title, author, date)
           VALUES (?, ?, ?, ?);"""

# Bind values to the placeholders
c.execute(sql, (filepath, title, author, date))

conn.commit()
conn.close()