from flask import Flask, render_template, request, jsonify, session, redirect

from flask_mysqldb import MySQL
import bcrypt

app = Flask(
    __name__,
    static_folder="../frontend/static",        # Static files (CSS, JS, images)
    template_folder="../frontend/templates"   # Template files (HTML)
)

app.secret_key = 'kaptagat_heights'

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  # Replace with your MySQL username
app.config['MYSQL_PASSWORD'] = 'DOMinica@2194'  # Replace with your MySQL password
app.config['MYSQL_DB'] = 'rent_manage'
mysql = MySQL(app)

# Route to serve the registration page (GET request)
@app.route('/register', methods=['GET'])
def show_register_page():
    return render_template('Register.html')

# Route to handle registration logic (POST request)
@app.route('/register', methods=['POST'])


def register():
    # Get form data
    fullname = request.form['fullname']
    email = request.form['email']
    role = request.form['role']
    doorno = request.form.get('doorno', None)  # Door number is optional
    password = request.form['password']

    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Insert into the database
    cursor = mysql.connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (fullname, email, password, role, doorno) VALUES (%s, %s, %s, %s, %s)",
            (fullname, email, hashed_password, role, doorno)
        )
        mysql.connection.commit()
        return jsonify({"message": "Registration successful!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        
        
# Route to serve the login page (GET request)
@app.route('/login', methods=['GET'])
def show_login_page():
    return render_template('login.html')

# Route to handle login logic (POST request)
@app.route('/login', methods=['POST'])
def login():
    # Get form data
    email = request.form['email']
    password = request.form['password']

    # Query the database for the user
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()

    if user:
        # Validate the password
        if bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):  # Assuming the password is in column 4
            role = user[4]  # Assuming the role is in column 5
            session['user_role'] = role  # Save role in session
            session['user_email'] = email  # Save email in session (if needed)
            return jsonify({"message": "Login successful!", "role": role}), 200
        else:
            return jsonify({"error": "Invalid password"}), 401
    else:
        return jsonify({"error": "User not found"}), 404
    

@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'user_role' not in session:
        return redirect('/login')  # Redirect to login if user is not authenticated
    user_role = session['user_role']  # Get user role from session
    return render_template('dashboard.html', role=user_role)


if __name__ == '__main__':
    app.run(debug=True)
