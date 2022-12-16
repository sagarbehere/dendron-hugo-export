import pathlib
import shutil
import logging
import os
import sqlite3
import frontmatter
from datetime import datetime

path = pathlib.Path("/home/sagar/Documents/dendron-notes/") 
destdir = pathlib.Path("notes/") 
exclude_dirs = ['logseq', 'journals', 'pages', '.vscode', 'daily', 'drafts', 'nopublish', 'templates', 'tags'] # relative to destdir
exclude_files = ['drafts.md', 'daily.md', 'scratchpad.md', 'nopublish.md'] # filename to exclude in dotted notation

def exclude_dir(test_path): # return True if test_path needs to be excluded
	for dir in exclude_dirs:
		if test_path.is_relative_to(pathlib.Path(dir)):
			return True
	return False

def exclude_file(filename):
	for f in exclude_files:
		if filename == f:
			return True
	return False

def export_tree(dbconn):
	dbcursor = dbconn.cursor()
	for f in path.iterdir():
		if f.suffix == '.md':
			prune_file = False # By default, don't exclude this file from publishing
			export_fname = f.name # f.name is e.g. pqr.abc.xyz.md
			export_dir = destdir # Pathlike object to represent destdir/pqr/abc/
			dotcount = export_fname.count('.') # Count the number of . in pqr.abc.xyz.md
			if dotcount > 1: # i.e. filename is not just xyz.md but like pqr.abc.xyz.md
				file_path_parts = f.name.split('.', dotcount-1) # ['pqr', 'abc', 'xyz.md']
				export_fname = file_path_parts[-1] # xyz.md
				if exclude_dir(pathlib.Path(*file_path_parts[:-1])): # If pqr/abc/ is in exclude_dirs
					logging.info('Skipping file %s',  f)
					continue
				export_dir = pathlib.Path(destdir, *file_path_parts[:-1]) # export_dir = destdir/pqr/abc/
			if exclude_file(f.name):
					logging.info('Skipping file %s', f)
					continue
			#print (export_dir, export_fname)
			pathlib.Path(export_dir).mkdir(parents=True, exist_ok=True) # create export_dir if it does not exist
			shutil.copy2(f, export_dir.joinpath(export_fname))
			dbcursor.execute('''INSERT INTO files ("dotted_name", "fs_path") VALUES (?, ?)''', (f.name, str(export_dir.joinpath(export_fname))))
			logging.info('Copying %s to %s', f, export_dir.joinpath(export_fname))
	dbconn.commit()
	

def create_index_files(dbconn): # This func moves e.g. foo/bar/baz.md to foo/bar/baz/_index.md if foo/bar/baz exists
	logging.info("\nCreating index files")
	dbcursor = dbconn.cursor()
	for items in os.walk(destdir):
		files = items[2]
		dirs = items[1]
		root = items[0]
		for file in files:
			if file[:-3] in dirs:
				indx = dirs.index(file[:-3])				
				# print(pathlib.Path(root,file), " should be in ", pathlib.Path(root, dirs[indx], '_index.md'))
				logging.info("Moving %s to %s", pathlib.Path(root,file), pathlib.Path(root, dirs[indx], '_index.md'))
				dbcursor.execute('''SELECT * FROM files WHERE "fs_path" = ?''', (str(pathlib.Path(root,file)),))
				if (dbcursor.fetchone() == 'None'):
					# Note that below line prints error if fs_path is not in db, but the shutil.move() is still attempted
					print ("ERROR creating index files. Seems like ", pathlib.Path(root,file), "is not in db")
				dbcursor.execute('''UPDATE files SET "fs_path" = ? WHERE "fs_path" = ?''', (str(pathlib.Path(root, dirs[indx], '_index.md')), str(pathlib.Path(root,file))))
				shutil.move(pathlib.Path(root,file), pathlib.Path(root, dirs[indx], '_index.md'))
	dbconn.commit()
	# Now create _index.md files in all folders that don't have them
	for items in os.walk(destdir):
		files = items[2]
		dirs = items[1]
		root = items[0]
		for dir in dirs:
			indx_file = pathlib.Path(root, dir, '_index.md')
			if not indx_file.exists():
				# print (indx_file, "does not exist")
				logging.info ("%s does not exist. Creating it.", indx_file)
				indx_file.touch()
				post = frontmatter.load(indx_file)
				post['title'] = indx_file.parent.name.capitalize() # explanation: path = pathlib.Path('/folderA/folderB/folderC/file.md'); path.parent.name is 'folderC'
				# NOTE: post['date'] will come later from the add_frontmatter_date() function
				f = open(indx_file, 'wb') # Note the 'wb'. Need to open file for binary writing, else frontmatter.dump() will not work
				frontmatter.dump(post, f)
				f.close()
	logging.info("Finished creating index files")

def root_to_index(): # moves root.md in vault to content/notes/_index.md and modifies frontmatter
	indx_file = pathlib.Path(destdir, '_index.md')
	shutil.move(pathlib.Path(destdir, 'root.md'), indx_file)
	post = frontmatter.load(indx_file)
	post['title'] = 'Notes'
	post['cascade'] = {'type': 'docs'}
	post['menu'] = {'main': {'title': 'Notes', 'weight': '45'}}
	f = open(indx_file, 'wb') # Note the 'wb'. Need to open file for binary writing, else frontmatter.dump() will not work
	frontmatter.dump(post, f)
	f.close()

def add_frontmatter_date(): # add 'date' frontmatter variable because Hugo needs it
	for file in destdir.glob('**/*'):
		if str(file).endswith(".md"):
			post = frontmatter.load(file)
			date_string = '' #datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			if 'updated' in post.keys():
				date_string = datetime.fromtimestamp(int(post['updated'])/1000.0).strftime("%Y-%m-%d %H:%M:%S") # JS timestamp in millisecons
			elif 'created' in post.keys():
				date_string =  datetime.fromtimestamp(int(post['created'])/1000.0).strftime("%Y-%m-%d %H:%M:%S")# JS timestamp in milliseconds
			else:
				date_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S") #Python timestamp is in seconds
			post['date'] = date_string
			f = open(file, 'wb')
			frontmatter.dump(post, f)
			f.close()	

def main():
	pathlib.Path('logs').mkdir(parents=True, exist_ok=True) # Create logs/ dir if it does not exist
	logging.basicConfig(filename='logs/export-hierarchy.log', filemode='w', encoding='utf-8', level=logging.DEBUG)
	logging.info('STARTING export')
	
	# TODO: Grab args and modify path/destdir/exclude_dirs/exclude_files as needed
	# Remember that to modify a global variable in a function, you need to: global x\nx = foo
	
	logging.info('Path to notes vault is %s', path)
	logging.info('Destination dir is %s', destdir)
	logging.info('Exclude dirs are %s', exclude_dirs)
	logging.info('Exclude files are %s', exclude_files)
	
	sqlitedbfilename = 'logs/relations.db'
	dbconn = sqlite3.connect(sqlitedbfilename)
	# TODO: Create table if not exists
	dbconn.execute('''CREATE TABLE IF NOT EXISTS files (id INTEGER UNIQUE NOT NULL PRIMARY KEY AUTOINCREMENT, note_id TEXT, dotted_name TEXT NOT NULL, fs_path TEXT NOT NULL)''')
	dbconn.execute('''DELETE FROM files''')
	dbconn.execute('''DELETE FROM SQLITE_SEQUENCE WHERE name="files"''') # reset the autoincrement id
	dbconn.commit()
	
	shutil.rmtree(destdir, ignore_errors=True)
	export_tree(dbconn)
	create_index_files(dbconn)
	root_to_index()
	add_frontmatter_date()
	dbconn.close()
	logging.info('FINISHED export')

if __name__ == "__main__":
    main()
