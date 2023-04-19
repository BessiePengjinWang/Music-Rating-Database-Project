
"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver
To run locally:
    python server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
  # accessible as a variable in index.html:
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, session
from datetime import date

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@34.73.36.248/project1
#
# For example, if you had username zy2431 and password 123123, then the following line would be:
#
#     DATABASEURI = "postgresql://zy2431:123123@34.73.36.248/project1"
#
# Modify these with your own credentials you received from TA!
DATABASE_USERNAME = "skb2183"
DATABASE_PASSWRD = "5402"
DATABASE_HOST = "34.148.107.47" # change to 34.28.53.86 if you used database 2 for part 2
DATABASEURI = f"postgresql://{DATABASE_USERNAME}:{DATABASE_PASSWRD}@{DATABASE_HOST}/project1"


#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)




@app.before_request
def before_request():
	"""
	This function is run at the beginning of every web request 
	(every time you enter an address in the web browser).
	We use it to setup a database connection that can be used throughout the request.

	The variable g is globally accessible.
	"""
	try:
		g.conn = engine.connect()
		load_user()
	except:
		print("uh oh, problem connecting to database")
		import traceback; traceback.print_exc()
		g.conn = None

#load user id if it exists
def load_user():
    if "user_id" in session:
        g.user_id = session["user_id"]
    else:
    	g.user_id = '-1'

@app.teardown_request
def teardown_request(exception):
	"""
	At the end of the web request, this makes sure to close the database connection.
	If you don't, the database could run out of memory!
	"""
	try:
		g.conn.close()
	except Exception as e:
		pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: https://flask.palletsprojects.com/en/1.1.x/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
def index():
	print(request.args)
	username = getusername()
	return render_template("index.html", username=username)

def getusername():
	username = ""
	if g.user_id != '-1':
		select_query = """SELECT username FROM site_user WHERE user_id = :user"""
		cursor = g.conn.execute(text(select_query), {'user': g.user_id})
		for result in cursor:
			username = result[0]
		cursor.close()
	return username

@app.route('/search_music', methods=['POST'])
def search_music():
	search_text = request.form['name']
	music = search_music(search_text)
	return render_template("music_search_results.html",music = music)

def search_music(search_text):
	search_text = "%" + search_text + "%"
	search_query = """SELECT music_id, music_name FROM music WHERE music_name LIKE :search"""
	music = []
	cursor = g.conn.execute(text(search_query), {'search': search_text})
	for result in cursor:
		music.append(result)
	cursor.close()
	return music

@app.route('/music/<music_id>')
def music(music_id):
	music_info_query = """SELECT music_id, music_name, artist_name, company_name, date_released, language, artist_id FROM music NATURAL JOIN artist NATURAL JOIN record_label WHERE music_id = :id"""
	music_info = []
	cursor = g.conn.execute(text(music_info_query), {'id': music_id})
	for result in cursor:
		music_info.append(result)
	cursor.close()

	genres_str = ""
	genres_query = """SELECT name FROM describes WHERE music_id = :id"""
	cursor = g.conn.execute(text(genres_query), {'id': music_id})
	for result in cursor:
		genres_str = genres_str + result[0] + ", "
	cursor.close()

	if len(genres_str) > 0:
		genres_str = genres_str[0:len(genres_str)-2]

	avg_rating_query = """SELECT AVG(rating_value) FROM rates WHERE music_id = :id"""
	avg = 0
	cursor = g.conn.execute(text(avg_rating_query), {'id': music_id})
	for result in cursor:
		avg = result[0]
	cursor.close()

	album_song_info = []
	album_query = """SELECT a.music_id, a.music_name, m.song_length FROM (song join music on music_id = song_id) as m join music as a on a.music_id = m.album_id WHERE m.music_id = :id"""
	song_query = """SELECT m.music_id, m.music_name,a.number_songs FROM (album NATURAL JOIN song) AS a JOIN music AS m ON a.song_id = m.music_id WHERE a.album_id = :id"""
	song_length_query = """SELECT song_length FROM song WHERE song_id = :id"""
	isSingle = True
	isAlbum = False
	cursor = g.conn.execute(text(album_query), {'id': music_id})

	#is a song on an album -- send album info to page
	if cursor.rowcount > 0:
		isSingle = False
		for result in cursor:
			album_song_info = result
	else:
		cursor = g.conn.execute(text(song_query), {'id': music_id})
		# is an album -- send song(s) info to page
		if(cursor.rowcount > 0):
			isAlbum = True
			isSingle = False
			for result in cursor:
				album_song_info.append(result)
		else:
			cursor = g.conn.execute(text(song_length_query), {'id': music_id})
			for result in cursor:
				album_song_info = result[0]
	#otherwise, remains a single -- not an album or on an album

	for result in cursor:
		if result[4] == g.user_id:
			user_rating = result
		else:
			ratings.append(result)
	cursor.close()

	ratings = []
	user_rating = None
	ratings_query = """SELECT username, rating_date, rating_value, comment, user_id FROM rates NATURAL JOIN site_user WHERE music_id = :id ORDER BY rating_date"""
	cursor = g.conn.execute(text(ratings_query), {'id': music_id})
	for result in cursor:
		if result[4] == g.user_id:
			user_rating = result
		else:
			ratings.append(result)
	cursor.close()

	similar_music = []
	similar_music_query = """SELECT distinct m.music_id, m.music_name FROM (describes AS d1 JOIN describes AS d2 ON d1.name = d2.name) JOIN music AS m ON m.music_id = d2.music_id WHERE d1.music_id = :id AND d2.music_id != d1.music_id"""
	cursor = g.conn.execute(text(similar_music_query), {'id': music_id})
	for result in cursor:
			similar_music.append(result)
	cursor.close()

	return render_template("music.html",music_info = music_info,avg_rating = avg,ratings = ratings, user_rating = user_rating, genres=genres_str, isAlbum=isAlbum,isSingle=isSingle, album_song_info=album_song_info, similar_music=similar_music)

@app.route('/music/<music_id>/addrating', methods=['POST'])
def addrating(music_id):
	rating_value = request.form['rating_value']
	if not rating_value.isnumeric() or int(rating_value) < 1 or int(rating_value) > 5:
		return redirect('/music/' + music_id)

	comment = request.form['comment']
	today = date.today().strftime("%Y-%m-%d")
	insert_into_rating_query = """INSERT INTO rates(user_id,music_id,rating_date,rating_value,comment) VALUES (:user_id, :music_id, :rating_date, :rating_value, :comment)"""
	# passing params in for each variable into query
	params = {}
	params["user_id"] = g.user_id
	params["music_id"] = music_id
	params["rating_date"] = today
	params["rating_value"] = rating_value
	params["comment"] = comment
	g.conn.execute(text(insert_into_rating_query), params)
	try:
		g.conn.commit()
	except Exception as e:
		g.conn.rollback()

	return redirect('/music/' + music_id)

@app.route('/music/<music_id>/deleterating', methods=['POST'])
def deleterating(music_id):
	delete_rating_query = """DELETE FROM rates WHERE user_id = :user AND music_id = :music"""
	g.conn.execute(text(delete_rating_query), {"user": g.user_id, "music": music_id})
	g.conn.commit()
	try:
		g.conn.commit()
	except Exception as e:
		g.conn.rollback()
	return redirect('/music/' + music_id)

@app.route('/artist/<artist_id>')
def artist(artist_id):
    query = """
    SELECT artist_id, artist_name, artist_language, artist_type
    FROM artist
    WHERE artist_id = :artist_id
    """
    params = {'artist_id': artist_id}
    result = g.conn.execute(text(query), params)
    artist_info = result.fetchone()
    if artist_info is None:
        return render_template('404.html'), 404
    return render_template('artist.html', artist_info=artist_info)


@app.route('/search_artist', methods=['POST'])
def search_artist():
    search_query = request.form['name']
    query = """
    SELECT artist_id, artist_name
    FROM artist
    WHERE UPPER(artist_name) LIKE UPPER(:search_query)
    """
    params = {'search_query': f'%{search_query}%'}
    result = g.conn.execute(text(query), params)
    artists = result.fetchall()
    return render_template('artist_search_results.html', artists=artists)

def handlebadinput(page):
	return render_template('error.html', page = page)


@app.route('/artist/<artist_id>/follow', methods=['POST'])
def follow_artist(artist_id):
    action = request.form['action']
    user_id = g.user_id

    # Check if the user is already following the artist
    check_query = """SELECT 1 FROM follows WHERE user_id = :user_id AND artist_id = :artist_id"""
    params = {'user_id': user_id, 'artist_id': artist_id}
    result = g.conn.execute(text(check_query), params)
    is_following = result.fetchone()

    if action == 'follow' and not is_following:
        insert_query = """INSERT INTO follows(user_id, artist_id) VALUES (:user_id, :artist_id)"""
        g.conn.execute(text(insert_query), params)
        g.conn.commit()
    elif action == 'unfollow' and is_following:
        delete_query = """DELETE FROM follows WHERE user_id = :user_id AND artist_id = :artist_id"""
        g.conn.execute(text(delete_query), params)
        g.conn.commit()
    return redirect('/artist/' + artist_id)





# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
	# accessing form inputs from user
	name = request.form['name']
	
	# passing params in for each variable into query
	params = {}
	params["new_name"] = name
	g.conn.execute(text('INSERT INTO test(name) VALUES (:new_name)'), params)
	g.conn.commit()
	return redirect('/')

# Example of adding new data to the database
@app.route('/createuser', methods=['POST'])
def createuser():
	# accessing form inputs from user
	name = request.form['username']
	password = request.form['password']
	if name == '' or password == '':
		return signup('You must fill in all fields')
	today = date.today().strftime("%Y-%m-%d")
	#possibly built into exception handling with execute and not necessary??
	name_exists_query = "SELECT username from site_user where username = :name"
	cursor = g.conn.execute(text(name_exists_query), {"name": name})
	if cursor.rowcount > 0:
		cursor.close()
		#ie. the username already exists, need error message
		return signup('That username already exists')

	prev_id_query = "SELECT MAX(user_id) from site_user"
	cursor = g.conn.execute(text(prev_id_query))
	prev_id = 0
	for result in cursor:
		prev_id = int(result[0])
	cursor.close()
	
	# passing params in for each variable into query
	params = {}
	params["new_user_id"] = str(prev_id + 1)
	params["new_username"] = name
	params["new_date_joined"] = today
	params["new_password"] = password
	g.conn.execute(text('INSERT INTO site_user(user_id,username,date_joined,password) VALUES (:new_user_id,:new_username,:new_date_joined,:new_password)'), params)
	try:
		g.conn.commit()
	except Exception as e:
		g.conn.rollback()
		return signup('Unknown error adding profile. Please try again.')
	session["user_id"] = params["new_user_id"]
	return redirect('/')

@app.route('/adduser', methods=['POST'])
def adduser():
    return redirect('/')


@app.route('/login')
def login():
	return render_template("login.html")

def login(error_msg):
	return render_template("login.html",error_msg=error_msg)

@app.route('/logout', methods=['POST'])
def logout():
	session["user_id"] = '-1'
	return redirect('/')

@app.route('/loginuser', methods=['POST'])
def loginuser():
	name = request.form['username']
	password = request.form['password']
	if name == '' or password == '':
		return login('You must fill in all fields')
	valid_user_query = "SELECT user_id from site_user where username = :name and password = :password"
	cursor = g.conn.execute(text(valid_user_query), {"name": name, "password": password})
	if cursor.rowcount > 0:
		session["user_id"] = cursor.first()[0]
		cursor.close()
	else:
		return login('Wrong username and/or password. Please try again.')

	return redirect('/')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if g.user_id:
        username = "Unknown"
        select_query = "SELECT username FROM site_user WHERE user_id = :user"
        cursor = g.conn.execute(text(select_query), {'user': g.user_id})
        for result in cursor:
            username = result[0]
        cursor.close()

        liked_genres_query = text("""
            SELECT genre.name FROM likes
            JOIN genre ON likes.name = genre.name
            WHERE likes.user_id = :user
        """)

        followed_artists_query = text("""
            SELECT artist.artist_id, artist.artist_name FROM follows
            JOIN artist ON follows.artist_id = artist.artist_id
            WHERE follows.user_id = :user
        """)

        if request.method == 'POST':
            selected_genre = request.form['genre']

            if request.form['action'] == 'like':
                insert_query = "INSERT INTO likes (user_id, name) VALUES (:user, :name)"
                g.conn.execute(text(insert_query), {'user': g.user_id, 'name': selected_genre})
                g.conn.commit()

            elif request.form['action'] == 'dislike':
                delete_query = "DELETE FROM likes WHERE user_id = :user AND name = :name"
                g.conn.execute(text(delete_query), {'user': g.user_id, 'name': selected_genre})
                g.conn.commit()  

        cursor = g.conn.execute(liked_genres_query, {'user': g.user_id})
        liked_genres = [result[0] for result in cursor]
        cursor.close()
        print("Liked genres:", liked_genres)

        print("Followed artists query:", followed_artists_query)
        cursor = g.conn.execute(followed_artists_query, {'user': g.user_id})
        print("Raw followed artists cursor results:", cursor.fetchall())
        cursor = g.conn.execute(followed_artists_query, {'user': g.user_id})
        followed_artists = [{'artist_id': artist_id, 'artist_name': artist_name} for artist_id, artist_name in cursor]
        cursor.close()
        print("Followed artists:", followed_artists)

        return render_template("like_genre.html", username=username, liked_genres=liked_genres, followed_artists=followed_artists)
    else:
        return redirect('/login')


@app.route('/signup')
def signup():
	return render_template("signup.html")

def signup(error_msg):
	return render_template("signup.html", error_msg=error_msg)


if __name__ == "__main__":
	import click

	@click.command()
	@click.option('--debug', is_flag=True)
	@click.option('--threaded', is_flag=True)
	@click.argument('HOST', default='0.0.0.0')
	@click.argument('PORT', default=8111, type=int)
	def run(debug, threaded, host, port):
		"""
		This function handles command line parameters.
		Run the server using:

			python server.py

		Show the help text using:

			python server.py --help

		"""

		HOST, PORT = host, port
		print("running on %s:%d" % (HOST, PORT))
		app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

run()
