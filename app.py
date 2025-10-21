import os
import random
import string
import time
import csv
import re
from werkzeug.utils import secure_filename
from utils.pdf_generator import generate_receipt
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, jsonify, flash, url_for, send_file, send_from_directory
from functools import wraps
from utils.db import (
    get_user_by_credentials, 
    fetch_vehicle_details,
    add_violation,
    get_violations,
    fetch_violation_types,
    check_username_exists,
    register_user,
    update_violation_status,
    get_dashboard_stats,
    fetch_all_vehicle_numbers,
    get_vehicles_by_admin,
    get_fines_history,
    delete_vehicle,
    get_all_violation_types,
    update_fine_amount,
    get_user_by_vehicle_and_phone,
    update_user_password,
    update_user_profile,
    fetch_all_vehicle_numbers_details
)
from utils.seatbelt_detection import detect_seatbelt_violation

app = Flask(__name__)
app.secret_key = "your_secret_key"


def generate_default_password():
    """Generate a random 8-character password that meets complexity criteria"""
    while True:
        password = ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*()", k=8))
        
        if re.match(r"(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{6,}", password):
            return password


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'user':
            flash('Access denied. User privileges required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def home():
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        owner_name = request.form["owner_name"]
        email = request.form["email"]
        address = request.form["address"]
        phone_number = request.form["phone_number"]

         # Check password complexity
        if not re.match(r"(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W]).{6,}", password):
            flash("Password must be at least 6 characters long, contain an uppercase letter, lowercase letters, number, and special characters.", "danger")
            return redirect("/register")
        
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect("/register")
        
        if check_username_exists(username):
            flash("Vehicle number already registered.", "warning")
            return redirect("/register")

        if register_user(username, password, 'user', owner_name, email, address, phone_number):
            flash("Registration successful! Please log in.", "success")
            return redirect("/login")
        else:
            flash("Registration failed. Please try again.", "danger")

    return render_template("register.html")


@app.route("/admin/register_officer", methods=["GET", "POST"])
@login_required
@admin_required
def register_officer():
        
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect("/admin/register_officer")
        
        if check_username_exists(username):
            flash("Officer ID already exists.", "warning")
            return redirect("/admin/register_officer")

        if register_user(username, password, 'admin'):
            flash("Officer registered successfully.", "success")
            return redirect("/admin/register_officer")
        else:
            flash("Officer registration failed. Please try again.", "danger")

    return render_template("register_officer.html")


@app.route("/admin/register_vehicle", methods=["GET", "POST"])
@login_required
@admin_required
def admin_register_vehicle():
    if request.method == "POST":
        vehicle_number = request.form["username"]
        owner_name = request.form["owner_name"]
        email = request.form["email"]
        address = request.form["address"]
        phone_number = request.form["phone_number"]
        
        if check_username_exists(vehicle_number):
            flash("Vehicle number already registered.", "warning")
            return redirect("/admin/register_vehicle")
        
        default_password = generate_default_password()
        
        admin_id = session["user_id"]
        if register_user(vehicle_number, default_password, 'user', owner_name, email, address, phone_number, admin_id):
            credentials_msg = f"""
                Registration successful! 
                Vehicle credentials:
                Username: {vehicle_number}
                Password: {default_password}
                Please share these credentials with the vehicle owner.
            """
            flash(credentials_msg, "success")
            return redirect("/admin/register_vehicle")
        else:
            flash("Registration failed. Please try again.", "danger")

    return render_template("admin_register_vehicle.html")



@app.route("/admin/user_credentials", methods=["GET", "POST"])
@login_required
@admin_required
def user_credentials():
    admin_id = session.get("user_id")
    vehicles = get_vehicles_by_admin(admin_id)
    
        # Handle search 
    search_term = request.form.get('vehicle_number', '').upper()
    if search_term:
        vehicles = [v for v in vehicles if search_term in v["vehicle_number"].upper()]
    return render_template("user_credentials.html", vehicles=vehicles)

@app.route("/admin/delete_vehicle/<vehicle_number>", methods=["POST"])
@login_required
@admin_required
def delete_vehicle_route(vehicle_number):
    if delete_vehicle(vehicle_number):
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 500


@app.route("/admin/fine_update")
@login_required
@admin_required
def fine_update():
    violation_types = get_all_violation_types()
    return render_template("fine_update.html", violation_types=violation_types)

@app.route("/admin/fine_update", methods=["POST"])
@login_required
@admin_required
def update_fine():
    data = request.get_json()
    violation_id = data.get("fine_id")
    new_amount = data.get("new_amount")
    
    if not violation_id or not new_amount:
        return jsonify({"status": "error", "message": "Violation ID and amount are required"}), 400

    try:
        new_amount = float(new_amount)
        if new_amount <= 0:
            raise ValueError("Fine amount must be positive")
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    if update_fine_amount(violation_id, new_amount):
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Failed to update fine amount"}), 500

# Login page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = get_user_by_credentials(username, password)
        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["username"] = username
            if user["role"] == "admin":
                return redirect("/admin/dashboard")
            elif user["role"] == "user":
                return redirect("/user/dashboard")
        else:
            return "Invalid credentials", 401
    return render_template("login.html")

# Logout route
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# Admin dashboard
@app.route("/admin/dashboard", methods=["GET", "POST"])
@login_required
@admin_required
def admin_dashboard():
    
    violation_types = fetch_violation_types()
    dashboard_stats = get_dashboard_stats()
    if request.method == "POST":
        if 'detection-image' in request.files:
            image = request.files['detection-image']
            
            if image and image.filename:
                try:
                    # Perform detection
                    detection_result = detect_seatbelt_violation(image)
                    return jsonify(detection_result)
                except Exception as e:
                    return jsonify({
                        'status': 'error',
                        'message': str(e),
                        'confidence': 0,
                        'detection_count': 0,
                        'average_confidence': 0,
                        'reason': f'Server error: {str(e)}'
                    }), 500
            
            return jsonify({
                'status': 'error',
                'message': 'No image file provided',
                'confidence': 0,
                'detection_count': 0,
                'average_confidence': 0,
                'reason': 'No image uploaded'
            }), 400
        vehicle_number = request.form.get("vehicle_number")
        violation_type_id = request.form.get("violation_type")
        confidence = request.form.get("confidence", 0)
        image_path = None

        # Handle image upload
        if 'violation_image' in request.files:
            image = request.files['violation_image']
            if image and image.filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"violation_{timestamp}_{secure_filename(image.filename)}"
                
                upload_dir = os.path.join(app.root_path, 'input', 'Detection Images')
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                
                image_path = os.path.join('Detection Images', filename)
                image.save(os.path.join(app.root_path, 'input', image_path))

        vehicle_details = fetch_vehicle_details(vehicle_number)
        if not vehicle_details:
            return "Vehicle not found", 404

        user_id = vehicle_details["user_id"]
        officer_id = session.get("user_id")
        
        if add_violation(vehicle_number, violation_type_id, user_id, officer_id, image_path, confidence):
            return jsonify({"status": "success", "message": f"Fine issued successfully for {vehicle_number}"})
        else:
            return jsonify({"status": "error", "message": "Failed to issue fine"}), 500

    return render_template("admin_dashboard.html", violation_types=violation_types, stats=dashboard_stats)

# Fetch vehicle details via AJAX
@app.route("/admin/fetch_vehicle")
def fetch_vehicle():
    vehicle_number = request.args.get("vehicle_number")
    vehicle_details = fetch_vehicle_details(vehicle_number)
    if vehicle_details:
        return jsonify(vehicle_details)
    return jsonify({"error": "Vehicle not found"}), 404


@app.route("/admin/get_vehicle_numbers")
def get_vehicle_numbers():
    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401
    
    vehicle_numbers = fetch_all_vehicle_numbers()
    return jsonify(vehicle_numbers)


@app.route("/admin/fines_history", methods=["GET", "POST"])
@login_required
@admin_required
def fines_history():
    officer_id = session.get("username")
    view_all = request.form.get("view_all", "false") == "true"
    vehicle_number = request.form.get("vehicle_number", "")
    status_filter = request.args.get("status", None)
    
    if view_all:
        fines = get_fines_history(officer_id=None, vehicle_number=vehicle_number)
    else:
        fines = get_fines_history(officer_id=officer_id, vehicle_number=vehicle_number)
    
    if status_filter and status_filter != 'all':
        fines = [fine for fine in fines if fine["status"].lower() == status_filter.lower()]
    
    return render_template("fine_history.html", 
                         fines=fines, 
                         view_all=view_all, 
                         current_status=status_filter or 'all',
                         vehicle_number=vehicle_number)

# Receipt download Route
@app.route("/admin/download_fines_report", methods=["GET"])
@login_required
@admin_required
def download_fines_report():
    officer_id = session.get("username")
    view_all = request.args.get("view_all", "false") == "true"
    vehicle_number = request.args.get("vehicle_number", "")
    
    if view_all:
        fines = get_fines_history(officer_id=None, vehicle_number=vehicle_number)
    else:
        fines = get_fines_history(officer_id=officer_id, vehicle_number=vehicle_number)
    
    output_file = os.path.join(os.path.expanduser("~"), "Downloads", 'fines_report.csv')
    
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = ['Vehicle Number', 'Issued By', 'Violation Type', 'Fine Amount (LKR)', 'Date & Time', 'Status']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for fine in fines:
            writer.writerow({
                'Vehicle Number': fine['vehicle_number'],
                'Issued By': fine['officer_id'],
                'Violation Type': fine['violation_type'],
                'Fine Amount (LKR)': f"LKR {'%.2f' % fine['fine_amount']}",
                'Date & Time': fine['timestamp'],
                'Status': fine['status']
            })
    
    return send_file(output_file, as_attachment=True, download_name='fines_report.csv')

@app.route("/admin/vehicle_reports", methods=["GET", "POST"])
@login_required
@admin_required
def vehicle_reports():
    vehicles = fetch_all_vehicle_numbers_details()

    # Handle search
    search_term = request.args.get('search', '').upper()
    if search_term:
        vehicles = [v for v in vehicles if search_term in v["vehicle_number"].upper()]

    return render_template("vehicle_reports.html", vehicles=vehicles)



@app.route("/admin/download_vehicle_report", methods=["GET"])
@login_required
@admin_required
def download_vehicle_report():
    vehicles = fetch_all_vehicle_numbers_details()
    
    report_path = os.path.join(os.path.expanduser("~"), "Downloads", 'vehicle_report.csv')
    with open(report_path, 'w', newline='') as csvfile:
        fieldnames = ['Vehicle Number', 'Owner Name', 'Address', 'Email', 'Phone Number']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for vehicle in vehicles:
            writer.writerow({
                'Vehicle Number': vehicle['vehicle_number'],
                'Owner Name': vehicle['owner_name'],
                'Address': vehicle['address'],
                'Email': vehicle['email'],
                'Phone Number': vehicle['phone_number']
            })
    return send_file(report_path, as_attachment=True, download_name='vehicle_report.csv')

# User dashboard
@app.route("/user/dashboard", methods=["GET"])
@login_required
@user_required
def user_dashboard():
    user_id = session.get("user_id")
    vehicle_details = fetch_vehicle_details(session.get("username"))
    violations = get_violations(user_id)
    pending_violations = [violation for violation in violations if violation["status"].lower() == "pending"]
    dashboard_stats = get_dashboard_stats(user_id) or (0, 0, 0, 0, 0, 0)
    return render_template(
        "user_dashboard.html",
        violations=violations,
        pending_violations=pending_violations,
        stats=dashboard_stats,
        vehicle_details=vehicle_details
    )
    
@app.route("/user/pay_fine", methods=["POST"])
@login_required
@user_required
def pay_fine():
    violation_id = request.form.get("violation_id")
    payment_method = request.form.get("payment_method")
    deposit_slip = request.files.get("deposit_slip")
    slip_path = None
    if not violation_id:
        return jsonify({"status": "error", "message": "Violation ID is required"}), 400
    
    if not payment_method:
        flash("Please select a payment method.", "warning")
    
    if payment_method in ['bank_transfer', 'online', 'cash']:
        
        if deposit_slip and deposit_slip.filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                slip_filename = f"violation_{timestamp}_{secure_filename(deposit_slip.filename)}"
                
                upload_dir = os.path.join(app.root_path, 'upload', 'Deposit Slips')
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                
                slip_path = os.path.join('Deposit Slips', slip_filename)
                deposit_slip.save(os.path.join(app.root_path, 'upload', slip_path))
            
    if update_violation_status(violation_id, "Paid", slip_path, payment_method):
        receipt_url = f"/user/receipt/{violation_id}"
        return jsonify({"status": "success", "receipt_url": receipt_url})
    return jsonify({"status": "error", "message": "Failed to process payment"}), 500


@app.route("/user/receipt/<violation_id>")
@login_required
@user_required
def download_receipt(violation_id):
    try:
        receipt_path = generate_receipt(violation_id)

        if not os.path.exists(receipt_path):
            return "Receipt not found", 404

        return send_file(receipt_path, as_attachment=True, download_name=f"receipt_{violation_id}.pdf")
    except Exception as e:
        print(f"Error generating receipt: {e}")
        return "Error generating receipt", 500



@app.route("/user/fines_history")
@login_required
@user_required
def user_fine_history():
    user_id = session.get("user_id")
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status', 'all')
    
    fines = get_violations(user_id)
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        fines = [f for f in fines if (
            datetime.strptime(f['timestamp'], '%Y-%m-%d %H:%M:%S') 
            if isinstance(f['timestamp'], str) 
            else f['timestamp']
        ) >= start_date]
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        fines = [f for f in fines if (
            datetime.strptime(f['timestamp'], '%Y-%m-%d %H:%M:%S') 
            if isinstance(f['timestamp'], str) 
            else f['timestamp']
        ) <= end_date]
    
    if status != 'all':
        fines = [f for f in fines if f['status'].lower() == status.lower()]
    
    for fine in fines:
        if isinstance(fine['timestamp'], datetime):
            fine['timestamp'] = fine['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template("user_fine_history.html", fines=fines)

@app.route("/user/profile", methods=["GET", "POST"])
@login_required
@user_required
def user_profile():
    username = session.get("username")
    vehicle_details = fetch_vehicle_details(username)
    
    if request.method == "POST":
        owner_name = request.form.get("owner_name")
        email = request.form.get("email")
        address = request.form.get("address")
        phone_number = request.form.get("phone_number")
        
        if update_user_profile(username, owner_name, email, address, phone_number):
            flash("Profile updated successfully.", "success")
            return redirect(url_for('user_profile'))
        else:
            flash("Failed to update profile. Please try again.", "danger")
    
    return render_template("user_profile.html", vehicle_details=vehicle_details)


otps = {}
OTP_VALIDITY_SECONDS = 300  # 5 minutes timeout

def generate_otp():
    return ''.join(random.choices('0123456789', k=6))

@app.route("/forgot-password")
def forgot_password():
    return render_template("forgot_password.html")

@app.route("/send_otp", methods=["POST"])
def send_otp():
    data = request.get_json()
    vehicle_number = data.get('vehicle_number')
    phone_number = data.get('phone_number')

    user = get_user_by_vehicle_and_phone(vehicle_number, phone_number)
    if not user:
        return jsonify({"status": "error", "message": "Vehicle number and phone number combination not found."}), 404

    otp = generate_otp()
    otps[phone_number] = {
        'otp': otp,
        'expires_at': time.time() + OTP_VALIDITY_SECONDS
    }

    print(f"OTP for {phone_number}: {otp}")

    return jsonify({"status": "success", "message": f"OTP sent successfully. Your OTP is {otp}."})

@app.route("/reset_password", methods=["POST"])
def reset_password():
    data = request.get_json()
    vehicle_number = data.get('vehicle_number')
    phone_number = data.get('phone_number')
    otp = data.get('otp')
    new_password = data.get('new_password')

    stored_otp_data = otps.get(phone_number)
    if not stored_otp_data:
        return jsonify({"status": "error", "message": "No OTP request found."}), 400

    if time.time() > stored_otp_data['expires_at']:
        del otps[phone_number]
        return jsonify({"status": "error", "message": "OTP has expired."}), 400

    if otp != stored_otp_data['otp']:
        return jsonify({"status": "error", "message": "Invalid OTP."}), 400

    user = get_user_by_vehicle_and_phone(vehicle_number, phone_number)
    if not user:
        return jsonify({"status": "error", "message": "Vehicle number and phone number combination not found."}), 404

    if update_user_password(user['id'], new_password):
        del otps[phone_number]
        return jsonify({"status": "success", "message": "Password reset successful."})
    else:
        return jsonify({"status": "error", "message": "Failed to reset password."}), 500


if __name__ == "__main__":
    app.run(debug=True)