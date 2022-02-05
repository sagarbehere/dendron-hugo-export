import regex as re
import os
import io
import pathlib
import sqlite3
import frontmatter
import logging

wikilinks = re.compile(r"\s\[\[(([^\]|]|\](?=[^\]]))*)(\|(([^\]]|\](?=[^\]]))*))?\]\]")
destdir = pathlib.Path("notes/") 

def get_post_title(file):
	post = frontmatter.load(file)
	title = post['title']
	if title:
		return title
	else:
		return 'Unknown title of'+str(file)

def process_wikilink(match, dbconn, file):
	dbcursor = dbconn.cursor()
	
	label = match.group(1).strip()
	if match.group(3):
		url = match.group(4).strip()
	else:
		url = match.group(1).strip()
		
	#title = get_post_title(file)
	title = str(file).replace(".md", "")
	# get file for dotted url
	dbcursor.execute('''SELECT fs_path FROM files WHERE dotted_name = ?''', (url+".md",))
	url_fs_path = dbcursor.fetchone();
	if url_fs_path is None:
		# print ("ERROR BROKEN LINK: Unable to find fs_path for ", url)
		url_fs_path = ("/404.html",)
	dbcursor.execute('''INSERT INTO links ("from", "from_title", "to") VALUES (?, ?, ?)''', (str(file), title, url_fs_path[0]))
	dbconn.commit()
	if url_fs_path[0] == "/404.html":
		newlink = " ["+label+"]("+url_fs_path[0]+")"
	else:
		newlink = " ["+label+"]({{< ref \""+url_fs_path[0]+"\" >}})"
	logging.info("File %s : Found %s and replacing it with %s", str(file), match.group(0), newlink)
	return newlink
	
def main():
	logging.basicConfig(filename='logs/process-wikilinks.log', filemode='w', encoding='utf-8', level=logging.DEBUG)
	logging.info('STARTING processing of wikilinks')
	sqlitedbfilename = 'logs/relations.db'
	dbconn = sqlite3.connect(sqlitedbfilename)
	
	dbconn.execute('''CREATE TABLE IF NOT EXISTS links (id INTEGER UNIQUE NOT NULL PRIMARY KEY AUTOINCREMENT, "from" TEXT NOT NULL, from_title TEXT, "to" TEXT NOT NULL, to_title TEXT)''')
	dbconn.execute('''DELETE FROM links''')
	dbconn.execute('''DELETE FROM SQLITE_SEQUENCE WHERE name="links"''') # reset the autoincrement id
	dbconn.commit()
	
	for file in destdir.glob('**/*'):
		if str(file).endswith(".md"):
			newfiledata = ''
			with open(file, 'r') as f:
				tuples = f.read().rpartition("## Backlinks") # [0] before delimiter [1]delimiter [2] after delimiter OR entire string if no delimiter
				if tuples[0]:
					filedata = tuples[0].strip()
				else:
				    filedata = tuples[2].strip()
				newfiledata = wikilinks.sub(lambda x: process_wikilink(x, dbconn, file), filedata)
				if tuples[0]: # If the file did contain a ## Backlinks section, add it back
					newfiledata += "\n\n"+tuples[1] + tuples[2]
			with open(file, 'w') as f:
				f.write(newfiledata)
				f.close()
	dbconn.close()		
	logging.info('FINISHED processing of wikilinks')

if __name__ == "__main__":
    main()
