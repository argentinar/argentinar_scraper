import sqlite3

conn = sqlite3.connect('scraped.db')
c = conn.cursor()


c.execute('''CREATE TABLE scraped
             (date_published text,
             date_scraped text,
             source_id text,
             feed_url text,
             post_url text,
             post_id text,
             wp_id text)''')

conn.commit()
conn.close()
