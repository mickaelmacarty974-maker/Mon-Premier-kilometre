import os, sqlite3, secrets
from functools import wraps
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.environ.get('HTTPS_ONLY') == '1', MAX_CONTENT_LENGTH=1024*1024)
DB = os.environ.get('DATABASE', os.path.join(os.path.dirname(__file__), 'forum.sqlite3'))
CATEGORIES = ['Course à pied', 'Débuter le sport', 'Motivation & entraide', 'Équipement', 'Victoires & progrès']

def db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db

@app.teardown_appcontext
def close_db(error):
    conn = g.pop('db', None)
    if conn: conn.close()

def init_db():
    with app.app_context():
        db().executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS topics(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), category TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS replies(id INTEGER PRIMARY KEY, topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE, user_id INTEGER NOT NULL REFERENCES users(id), body TEXT NOT NULL, created_at TEXT NOT NULL);''')
        db().commit()

def now(): return datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M UTC')

def logged_in(fn):
    @wraps(fn)
    def inner(*a, **kw):
        if not session.get('uid'):
            flash('Connecte-toi pour participer.', 'info')
            return redirect(url_for('login'))
        return fn(*a, **kw)
    return inner

@app.before_request
def csrf_check():
    if 'csrf' not in session: session['csrf'] = secrets.token_urlsafe(32)
    if request.method == 'POST' and not secrets.compare_digest(request.form.get('csrf', ''), session['csrf']): abort(400)

@app.context_processor
def shared(): return {'categories': CATEGORIES, 'current_user': session.get('username'), 'csrf': session.get('csrf')}

@app.get('/')
def home():
    category = request.args.get('category', '')
    if category and category not in CATEGORIES: abort(404)
    q = '''SELECT t.*, u.username, (SELECT COUNT(*) FROM replies r WHERE r.topic_id=t.id) reply_count FROM topics t JOIN users u ON u.id=t.user_id'''
    args=[]
    if category: q += ' WHERE t.category=?'; args.append(category)
    q += ' ORDER BY t.id DESC LIMIT 100'
    topics = db().execute(q, args).fetchall()
    return render_template('home.html', topics=topics, category=category)

@app.route('/inscription', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('username','').strip()
        pwd = request.form.get('password','')
        if not 3 <= len(name) <= 24 or not all(c.isalnum() or c in '_-' for c in name): flash('Pseudo : 3 à 24 caractères, lettres, chiffres, tiret ou _.', 'error')
        elif len(pwd) < 10: flash('Choisis un mot de passe d’au moins 10 caractères.', 'error')
        else:
            try:
                cur=db().execute('INSERT INTO users(username,password_hash,created_at) VALUES(?,?,?)', (name,generate_password_hash(pwd),now()))
                db().commit(); session.clear(); session['uid']=cur.lastrowid; session['username']=name; session['csrf']=secrets.token_urlsafe(32)
                return redirect(url_for('home'))
            except sqlite3.IntegrityError: flash('Ce pseudo est déjà utilisé.', 'error')
    return render_template('auth.html', title='Créer mon compte', mode='register')

@app.route('/connexion', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        name=request.form.get('username','').strip(); pwd=request.form.get('password','')
        user=db().execute('SELECT * FROM users WHERE username=?',(name,)).fetchone()
        if user and check_password_hash(user['password_hash'],pwd):
            session.clear(); session['uid']=user['id']; session['username']=user['username']; session['csrf']=secrets.token_urlsafe(32)
            return redirect(url_for('home'))
        flash('Identifiants incorrects.', 'error')
    return render_template('auth.html', title='Connexion', mode='login')

@app.post('/deconnexion')
def logout(): session.clear(); return redirect(url_for('home'))

@app.route('/nouveau-sujet', methods=['GET','POST'])
@logged_in
def new_topic():
    if request.method == 'POST':
        category=request.form.get('category',''); title=request.form.get('title','').strip(); body=request.form.get('body','').strip()
        if category not in CATEGORIES or not 5 <= len(title) <= 120 or not 10 <= len(body) <= 5000: flash('Vérifie la catégorie, le titre (5–120) et le message (10–5000).', 'error')
        else:
            cur=db().execute('INSERT INTO topics(user_id,category,title,body,created_at) VALUES(?,?,?,?,?)',(session['uid'],category,title,body,now()))
            db().commit(); return redirect(url_for('topic',topic_id=cur.lastrowid))
    return render_template('new_topic.html')

@app.route('/sujet/<int:topic_id>', methods=['GET','POST'])
def topic(topic_id):
    topic=db().execute('SELECT t.*,u.username FROM topics t JOIN users u ON u.id=t.user_id WHERE t.id=?',(topic_id,)).fetchone()
    if not topic: abort(404)
    if request.method == 'POST':
        if not session.get('uid'): return redirect(url_for('login'))
        body=request.form.get('body','').strip()
        if not 2 <= len(body) <= 3000: flash('Réponse : entre 2 et 3000 caractères.', 'error')
        else:
            db().execute('INSERT INTO replies(topic_id,user_id,body,created_at) VALUES(?,?,?,?)',(topic_id,session['uid'],body,now()))
            db().commit(); return redirect(url_for('topic',topic_id=topic_id))
    replies=db().execute('SELECT r.*,u.username FROM replies r JOIN users u ON u.id=r.user_id WHERE r.topic_id=? ORDER BY r.id',(topic_id,)).fetchall()
    return render_template('topic.html',topic=topic,replies=replies)

if __name__ == '__main__':
    init_db()
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
