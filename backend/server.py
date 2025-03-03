from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import bcrypt
import base64
import requests
from datetime import datetime
from weasyprint import HTML




def generate_password(short_code, passkey, timestamp):
    # Concatenate short_code, passkey, and timestamp, then Base64 encode the result.
    data_to_encode = f"{short_code}{passkey}{timestamp}"
    encoded_string = base64.b64encode(data_to_encode.encode()).decode()
    return encoded_string

# Global MPESA Credentials
business_short_code = '174379'
passkey = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'



app = Flask(
    __name__,
    static_folder="../frontend/static",        # Static files (CSS, JS, images)
    template_folder="../frontend/templates"   # Template files (HTML)
)

app.secret_key = 'kaptagat_heights'

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  
app.config['MYSQL_PASSWORD'] = 'DOMinica@2194'  
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

    # using fixed amount  for now
    rent_amount = 1  
    message = ''
    
    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        # In a real scenario, you might add additional validation or integrate with a payment gateway.
        
        
        if payment_method == 'mpesa':
            # You need to supply the proper phone number and account reference.
            # Assume you have tenant phone number stored (or you can add a field for it)
            tenant_phone = "254796412978"  # Replace with the actual tenant phone number in international format
            account_reference = "Tenant" + str(tenant_id)  # For example, use the tenant ID as reference
            transaction_desc = "Rent Payment"
            
            # Call the MPESA integration function.
            stk_response = initiate_stk_push(tenant_phone, rent_amount, account_reference, transaction_desc)
            message = f"MPESA STK Push initiated: {stk_response.get('ResponseDescription', 'No response description')}"
            # Optionally, you may want to insert a payment record with a status of 'pending'.
        else:
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
        cursor.close()
        return render_template('payment_confirmation.html', message=message, rent_amount=rent_amount)
    
    cursor.close()
    return render_template('pay_rent.html', rent_amount=rent_amount, fullname=fullname)



def get_mpesa_access_token():
    consumer_key = 'Yuw5sIah4WWMKHFywAXWo2NmcZePtmRhRR6RiDfcP4GIDrfW'
    consumer_secret = 'XgiaDwFHzxGFMZQrpI3wbwCUYGMbPk0sZ6ECf5HZVeP87ckyeLUIZLxguD61gyrE'
    # Daraja OAuth endpoint for sandbox
    api_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    
    # Prepare the credentials string and encode it in base64
    credentials = f"{consumer_key}:{consumer_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {encoded_credentials}'
    }
    
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()  # Raise an error if the request failed
    access_token = response.json().get('access_token')
    return access_token

# Example usage:






def generate_timestamp():
    # Generate current timestamp in the required format
    return datetime.now().strftime('%Y%m%d%H%M%S')




# Example usage:


def initiate_stk_push(phone_number, amount, account_reference, transaction_desc):
    access_token = get_mpesa_access_token()
    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    
    # Generate required parameters
    timestamp = generate_timestamp()
    password = generate_password(business_short_code, passkey, timestamp)
    
    # Set the callback URL to your public ngrok URL plus your callback route.
    callback_url = " https://7fc1-41-90-44-148.ngrok-free.app/mpesa/callback"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "BusinessShortCode": business_short_code,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,         # Must be a string in international format, e.g., "254796412978"
        "PartyB": business_short_code,  # Your Business Short Code
        "PhoneNumber": phone_number,
        "CallBackURL": callback_url,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_desc
    }
    
    print("Timestamp:", timestamp)
    print("Password:", password)

    response = requests.post(api_url, json=payload, headers=headers)
    response.raise_for_status()  # Raise an error if the request failed
    return response.json()






@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    callback_data = request.get_json()
    # Log or process the callback data as needed.
    # For example, check if the payment was successful and update your database.
    print("Callback received:", callback_data)
    
    # You might want to extract fields such as:
    # callback_data['Body']['stkCallback']['ResultCode']
    # callback_data['Body']['stkCallback']['ResultDesc']
    # callback_data['Body']['stkCallback']['CallbackMetadata']
    
    # Respond with a success status to Daraja
    return "Callback received", 200






@app.route('/analytics', methods=['GET'])
def analytics():
    # Ensure only admins can access analytics
    if 'user_role' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('dashboard'))
    
    cursor = mysql.connection.cursor()
    
    # Example Query 1: Count the number of tenants
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'tenant'")
    tenant_count = cursor.fetchone()[0]
    # Assume each tenant is expected to pay 1000 Ksh.
    expected_revenue = tenant_count * 1000

    # Example Query 2: Sum the total of completed payments from the payments table.
    cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'completed'")
    actual_revenue = cursor.fetchone()[0]
    
    # Example Query 3 (Optional): Count on-time vs. late payments.
    # (This assumes you have an 'on_time' field in your payments table.)
    cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'completed' AND on_time = 1")
    on_time_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'completed' AND on_time = 0")
    late_count = cursor.fetchone()[0]
    
    cursor.close()
    
    # Package the data into a dictionary to pass to the template.
    analytics_data = {
        'expected_revenue': expected_revenue,
        'actual_revenue': actual_revenue,
        'on_time_count': on_time_count,
        'late_count': late_count
    }
    
    return render_template('analytics.html', data=analytics_data)



@app.route('/admin/generate_receipt/<int:payment_id>', methods=['GET'])
def generate_receipt(payment_id):
    # Ensure only admin users can access this route.
    if 'user_email' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('show_login_page'))
    
    cursor = mysql.connection.cursor()
    
    # Retrieve payment details (join with users to get tenant's name, etc.)
    query = """
        SELECT p.payment_id, p.amount, p.payment_method, p.created_at, p.account_reference,
        u.fullname as tenant_name
        FROM payments p
        JOIN users u ON p.tenant_id = u.id
        WHERE p.payment_id = %s
    """
    cursor.execute(query, (payment_id,))
    payment = cursor.fetchone()
    cursor.close()
    
    if not payment:
        return "Payment not found", 404

    # Build a dictionary for template data.
    payment_data = {
        "payment_id": payment[0],
        "amount": payment[1],
        "payment_method": payment[2],
        "created_at": payment[3],
        "account_reference": payment[4],
        "tenant_name": payment[5]
    }
    
    # Render the HTML using your receipt template.
    rendered_html = render_template('receipt.html', payment=payment_data)
    
    # Generate the PDF from the rendered HTML.
    pdf = HTML(string=rendered_html).write_pdf()
    
    # Save the PDF in a designated receipts folder.
    receipts_folder = os.path.join(os.getcwd(), 'frontend', 'static', 'receipts')
    if not os.path.exists(receipts_folder):
        os.makedirs(receipts_folder)
    
    receipt_filename = f"receipt_{payment_id}.pdf"
    receipt_path = os.path.join(receipts_folder, receipt_filename)
    with open(receipt_path, 'wb') as f:
        f.write(pdf)
    
    # Update the payment record with the receipt URL (relative to the static folder).
    receipt_url = f"receipts/{receipt_filename}"
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE payments SET receipt_url = %s WHERE payment_id = %s", (receipt_url, payment_id))
    mysql.connection.commit()
    cursor.close()
    
    return f"Receipt generated successfully. <a href='{url_for('static', filename=receipt_url)}' download>Download Receipt</a>"




if __name__ == '__main__':
    app.run(debug=True)
