import os
import json
import argparse
import rethinkdb
from rethinkdb.errors import RqlRuntimeError, RqlDriverError
from flask import Flask, jsonify, render_template, g, request, abort


RDB_HOST = os.environ.get('RDB_HOST') or 'localhost'
RDB_PORT = os.environ.get('RDB_PORT') or 28015
TODO_DB = 'to_do_list'

def dbSetup():
	r = rethinkdb.RethinkDB()
	connection = r.connect(host=RDB_HOST, port=RDB_PORT)
	try:
		r.db_create(TODO_DB).run(connection)
		r.db(TODO_DB).table_create('todos').run(connection)
		print('Database setup completed')
	except RqlRuntimeError:
	    print('Database already exists')
	finally:
		connection.close()

app = Flask(__name__)
app.config.from_object(__name__)

@app.before_request
def before_request():
	try:
		g.rdb_conn = r.connect(host=RDB_HOST, port=RDB_PORT, db=TODO_DB)
	except RqlDriverError:
		abort(503, 'No database connection could be established.')

@app.teardown_request
def teardown_request():
	try:
		g.rdb_conn.close()
	except AttributeError:
		pass

@app.route("/todos", method=['GET'])
def get_todos():
	selection = list(r.table('todos').run(g.rdb_conn))
	return json.dumps(selection)

@app.route("/todos", method=['POST'])
def new_todo():
	inserted = r.table('todos').insert(request.json).run(g.rdb_conn)	
	return jsonify(id=inserted['generated_keys'][0])

@app.route("/todos/<string:todo_id>", method=['GET'])
def get_todos(todo_id):
	todo = r.table('todos').get(todo_id).run(g.rdb_conn)
	return json.dumps(todo)

@app.route("/todos/<string:todo_id>", method=['PUT'])
def update_todo(todo_id):
	return jsonify(r.table('todos').get(todo_id).replace(request.json).run(g.rdb_conn))

@app.route("/todos/<string:todo_id>", method=['PATCH'])
def patch_todo(todo_id):
	return jsonify(r.table('todos').get(todo_id).update(request.json).run(g.rdb_conn))

@app.route("/todos/<string:todo_id>", method=['DELETE'])
def delete_todo(todo_id):
	return jsonify(r.table('todos').get(todo_id).delete().run(g.rdb_conn))

@app.route("/")
def show_todos():
	return render_template('todo.html')

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Run the Flask todo app')
	parser.add_argument('--setup', dest='run_setup', action='store_true')
	args = parser.parse_args
	if args.run_setup:
		dbSetup()
	else:
		app.run(debug=True)
		
