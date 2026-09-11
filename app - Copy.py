from flask import Flask, render_template, request, redirect, session, jsonify
import pymysql
import pymysql.cursors
from config import Config

app = Flask(__name__)
app.secret_key = "secret123"

def db():
    return pymysql.connect(
        host=Config.HOST,
        user=Config.USER,
        password=Config.PASSWORD,
        database=Config.DATABASE
    )

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']

        conn = db()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute("SELECT * FROM admin_lib WHERE username=%s AND password=%s", (u, p))
        user = cur.fetchone()
        conn.close()

        if user:
            session['admin'] = True
            return redirect('/')
        return "Invalid Login"

    return render_template("login.html")

# DASHBOARD
@app.route('/')
def dashboard():
    if 'admin' not in session:
        return redirect('/login')

    conn = db()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    cur.execute("SELECT COUNT(*) total FROM books")
    total = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) issued FROM books WHERE status='Issued'")
    issued = cur.fetchone()['issued']

    cur.execute("SELECT COUNT(*) available FROM books WHERE status='Available'")
    available = cur.fetchone()['available']

    conn.close()

    return render_template("dashboard.html", total=total, issued=issued, available=available)

# BOOKS
@app.route('/books')
def books():
    if 'admin' not in session:
        return redirect('/login')

    conn = db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT * FROM books")
    books = cur.fetchall()
    conn.close()

    return render_template("books.html", books=books)

# ADD BOOK
@app.route('/add', methods=['GET','POST'])
def add():
    if 'admin' not in session:
        return redirect('/login')

    if request.method == 'POST':
        t = request.form['title']
        a = request.form['author']

        conn = db()
        cur = conn.cursor()
        cur.execute("INSERT INTO books(title,author) VALUES(%s,%s)", (t, a))
        conn.commit()
        conn.close()

        return redirect('/books')

    return render_template("add.html")

# ISSUE BOOK
@app.route('/issue/<int:id>', methods=['GET','POST'])
def issue(id):
    if 'admin' not in session:
        return redirect('/login')

    conn = db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT * FROM books WHERE id=%s", (id,))
    book = cur.fetchone()

    if request.method == 'POST':
        student = request.form['student']

        cur = conn.cursor()
        cur.execute("INSERT INTO issued_books(student_name,book_title) VALUES(%s,%s)",
                    (student, book['title']))
        cur.execute("UPDATE books SET status='Issued' WHERE id=%s", (id,))
        conn.commit()
        conn.close()

        return redirect('/books')

    conn.close()
    return render_template("issue.html", book=book)

# RETURN BOOK
@app.route('/return/<int:id>')
def return_book(id):
    if 'admin' not in session:
        return redirect('/login')

    conn = db()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    cur.execute("SELECT title FROM books WHERE id=%s", (id,))
    book = cur.fetchone()

    cur.execute("UPDATE books SET status='Available' WHERE id=%s", (id,))
    cur.execute("DELETE FROM issued_books WHERE book_title=%s", (book['title'],))

    conn.commit()
    conn.close()

    return redirect('/books')

# DELETE BOOK
@app.route('/delete/<int:id>')
def delete_book(id):
    if 'admin' not in session:
        return redirect('/login')

    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM books WHERE id=%s", (id,))
    conn.commit()
    conn.close()

    return redirect('/books')

# USER REGISTER
@app.route('/user_register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        
        conn = db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (u, p))
            conn.commit()
        except pymysql.err.IntegrityError:
            conn.close()
            return "Username already exists!"
        conn.close()
        
        return redirect('/user_login')
    return render_template('user_register.html')

# USER LOGIN
@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']

        conn = db()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (u, p))
        user = cur.fetchone()
        conn.close()

        if user:
            session['user'] = user['username']
            return redirect('/user_books')
        return "Invalid Login"
    return render_template("user_login.html")

# USER BOOKS LIST
@app.route('/user_books')
def user_books():
    if 'user' not in session:
        return redirect('/user_login')

    conn = db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    # All books
    cur.execute("SELECT * FROM books")
    books = cur.fetchall()

    # Books taken by THIS user
    cur.execute("SELECT * FROM issued_books WHERE student_name=%s", (session['user'],))
    my_books = cur.fetchall()
    
    conn.close()

    return render_template("user_books.html", books=books, my_books=my_books, user=session['user'])

# USER TAKE BOOK
@app.route('/user_take/<int:id>')
def user_take(id):
    if 'user' not in session:
        return redirect('/user_login')

    conn = db()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT * FROM books WHERE id=%s", (id,))
    book = cur.fetchone()

    if book and book['status'] == 'Available':
        student = session['user']
        cur = conn.cursor()
        cur.execute("INSERT INTO issued_books(student_name,book_title) VALUES(%s,%s)",
                    (student, book['title']))
        cur.execute("UPDATE books SET status='Issued' WHERE id=%s", (id,))
        conn.commit()
    conn.close()

    return redirect('/user_books')

# USER LOGOUT
@app.route('/user_logout')
def user_logout():
    session.pop('user', None)
    return redirect('/user_login')

# LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE,
            password VARCHAR(255)
        )
    """)
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)