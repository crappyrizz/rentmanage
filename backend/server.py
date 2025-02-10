from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
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

app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'frontend', 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
        # redirect to the login page
        return redirect(url_for('show_login_page'))
    except Exception as e:
    # Show an error message if something goes wrong
        return render_template('Register.html', error=f"Error: {str(e)}")
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
            return redirect(url_for('dashboard'))  # Redirect to dashboard
        else:
            return render_template('login.html', error="Invalid password")  # Show error on login page
    else:
        return render_template('login.html', error="User not found")  # Show error on login page
    

@app.route('/dashboard', methods=['GET'])
def dashboard():
    print(f"Session Data: {session}")  # Debug: Print session data
    if 'user_role' not in session:
        return redirect('/login')  # Redirect to login if user is not authenticated
    user_role = session['user_role']  # Get user role from session
    return render_template('dashboard.html', role=user_role)



@app.route('/chat', methods=['GET', 'POST'])
def chat():
    # Ensure the user is logged in
    if 'user_email' not in session:
        return redirect(url_for('show_login_page'))
    
    # Retrieve the current user's information
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, role FROM users WHERE email = %s", (session['user_email'],))
    user = cursor.fetchone()
    if not user:
        return redirect(url_for('show_login_page'))
    current_user_id, current_role = user[0], user[1]
    
    # Determine conversation mode from GET parameter; default to public if not specified
    conversation = request.args.get('recipient_id', 'public')
    
    if request.method == 'POST':
        # When posting a message, the form will include the recipient value.
        selected_recipient = request.form.get('recipient_id', 'public')
        content = request.form.get('content')
        
        if selected_recipient == 'public':
            is_public = True
            recipient_value = None
        else:
            is_public = False
            try:
                recipient_value = int(selected_recipient)
            except ValueError:
                recipient_value = None  # Fallback if conversion fails
        
        try:
            cursor.execute(
                "INSERT INTO messages (sender_id, content, is_public, recipient_id) VALUES (%s, %s, %s, %s)",
                (current_user_id, content, is_public, recipient_value)
            )
            mysql.connection.commit()
        except Exception as e:
            mysql.connection.rollback()
            print("Error inserting message:", e)
        finally:
            # Redirect back to the chat page for the same conversation
            return redirect(url_for('chat', recipient_id=selected_recipient))
    
    # Retrieve messages based on conversation type
    if conversation == 'public':
        # Public chat: show all messages marked as public
        cursor.execute("""
            SELECT m.content, u.fullname, m.timestamp 
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.is_public = %s
            ORDER BY m.timestamp ASC
        """, (True,))
    else:
        # Private conversation: show messages exchanged only between the current user and the selected user.
        try:
            recipient_id_int = int(conversation)
        except ValueError:
            recipient_id_int = None
        if recipient_id_int is None:
            # Fallback to public chat if recipient_id is invalid
            cursor.execute("""
                SELECT m.content, u.fullname, m.timestamp 
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE m.is_public = %s
                ORDER BY m.timestamp ASC
            """, (True,))
        else:
            cursor.execute("""
                SELECT m.content, u.fullname, m.timestamp 
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE m.is_public = %s 
                AND (
                        (m.sender_id = %s AND m.recipient_id = %s)
                        OR (m.sender_id = %s AND m.recipient_id = %s)
                    )
                ORDER BY m.timestamp ASC
            """, (False, current_user_id, recipient_id_int, recipient_id_int, current_user_id))
    messages = cursor.fetchall()
    
    # Get a list of potential recipients.
    # Here, we list all users except the current user.
    cursor.execute("SELECT id, fullname, role FROM users WHERE id != %s", (current_user_id,))
    potential_recipients = cursor.fetchall()
    cursor.close()
    
    return render_template('chat.html',
                        messages=messages,
                        potential_recipients=potential_recipients,
                        current_recipient=conversation,
                        current_user_id=current_user_id)
                        




@app.route('/profile', methods=['GET', 'POST'])
def profile():
    # Ensure the user is logged in
    if 'user_email' not in session:
        return redirect(url_for('show_login_page'))
    
    cursor = mysql.connection.cursor()
    # Retrieve the current user's info. Adjust the column names as needed.
    cursor.execute("SELECT id, fullname, email, doorno, role, profile_pic FROM users WHERE email = %s", (session['user_email'],))
    user = cursor.fetchone()
    if not user:
        cursor.close()
        return redirect(url_for('show_login_page'))
    
    user_id, fullname, email, doorno, role, profile_pic = user
    message = ""
    
    if request.method == 'POST':
        # Get updated form data; use the current values as defaults if not provided.
        new_fullname = request.form.get('fullname', fullname)
        new_doorno = request.form.get('doorno', doorno)
        
        # Check if a file was uploaded for the profile picture
        file = request.files.get('profile_pic')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Save the file to the upload folder
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            # Store the file path relative to the static folder (e.g., "uploads/filename.jpg")
            profile_pic = 'uploads/' + filename
        
        try:
            cursor.execute("UPDATE users SET fullname=%s, doorno=%s, profile_pic=%s WHERE id=%s",
                        (new_fullname, new_doorno, profile_pic, user_id))
            mysql.connection.commit()
            message = "Profile updated successfully."
            fullname = new_fullname  # update our local variable to reflect the change
            doorno = new_doorno
        except Exception as e:
            mysql.connection.rollback()
            message = "Error updating profile: " + str(e)
        finally:
            cursor.close()
            return render_template('profile.html', fullname=fullname, email=email, doorno=doorno,
                                role=role, profile_pic=profile_pic, message=message)
    
    cursor.close()
    return render_template('profile.html', fullname=fullname, email=email, doorno=doorno,
                        role=role, profile_pic=profile_pic, message=message)



@app.route('/pay', methods=['GET', 'POST'])
def pay_rent():
    # Ensure the user is logged in and is a tenant.
    if 'user_email' not in session or session.get('user_role') != 'tenant':
        return redirect(url_for('show_login_page'))
    
    cursor = mysql.connection.cursor()
    # Retrieve tenant details based on session email.
    cursor.execute("SELECT id, fullname FROM users WHERE email = %s", (session['user_email'],))
    tenant = cursor.fetchone()
    if not tenant:
        cursor.close()
        return redirect(url_for('dashboard'))
    tenant_id, fullname = tenant

    # For simplicity, assume each tenant pays a fixed rent (e.g., 1000).
    rent_amount = 1000  
    message = ''
    
    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        # In a real scenario, you might add additional validation or integrate with a payment gateway.
        try:
            cursor.execute(
                "INSERT INTO payments (tenant_id, amount, payment_method, status) VALUES (%s, %s, %s, %s)",
                (tenant_id, rent_amount, payment_method, 'completed')
            )
            mysql.connection.commit()
            message = 'Payment successful!'
        except Exception as e:
            mysql.connection.rollback()
            message = 'Payment failed: ' + str(e)
        finally:
            cursor.close()
        return render_template('payment_confirmation.html', message=message, rent_amount=rent_amount)
    
    cursor.close()
    return render_template('pay_rent.html', rent_amount=rent_amount, fullname=fullname)


if __name__ == '__main__':
    app.run(debug=True)
