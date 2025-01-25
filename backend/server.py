from flask import Flask, render_template, request, jsonify

from flask_mysqldb import MySQL
import bcrypt

app = Flask(
    __name__,
    static_folder="../frontend\\global",  # Path to static files
    template_folder="../frontend\\global"  # Path to HTML files
)

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

if __name__ == '__main__':
    app.run(debug=True)
