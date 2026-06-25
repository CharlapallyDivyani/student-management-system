from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from database import Database
from config import SECRET_KEY, SESSION_TIMEOUT
from datetime import datetime, timedelta
from functools import wraps
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=SESSION_TIMEOUT)

# Initialize database
db = Database()
db.create_tables()

# ========== DECORATORS FOR PROTECTION ==========

def login_required(f):
    """Decorator to check if admin is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_admin_info():
    """Get current logged-in admin info"""
    if 'admin_id' in session:
        admin = db.get_admin_by_id(session['admin_id'])
        return admin
    return None

# ========== AUTHENTICATION ROUTES ==========

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    print("Login route accessed")
    
    if request.method == 'POST':
        print("POST request received")
        username = request.form.get('username')
        password = request.form.get('password')
        
        print(f"Trying to login with username: {username}")
        
        # Verify credentials
        admin = db.verify_admin_password(username, password)
        
        if admin:
            print(f"Login successful for {username}")
            # Create session
            session.permanent = True
            session['admin_id'] = admin['id']
            session['username'] = admin['username']
            session['full_name'] = admin['full_name']
            
            # Update last login
            db.update_admin_last_login(admin['id'])
            
            # Log activity
            ip_address = request.remote_addr
            db.log_activity(admin['id'], 'LOGIN', f'Logged in from {ip_address}', ip_address)
            
            return redirect(url_for('index'))
        else:
            print(f"Login failed for {username}")
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Admin registration page"""
    print("🔹 Register route accessed")
    
    if request.method == 'POST':
        print("📝 POST request for registration")
        
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        full_name = request.form.get('full_name', '').strip()
        
        # Validation
        errors = []
        
        if not username:
            errors.append('Username is required')
        elif len(username) < 3:
            errors.append('Username must be at least 3 characters')
        
        if not password:
            errors.append('Password is required')
        elif len(password) < 6:
            errors.append('Password must be at least 6 characters')
        
        if password != confirm_password:
            errors.append('Passwords do not match')
        
        if not full_name:
            errors.append('Full name is required')
        
        if not email:
            errors.append('Email is required')
        
        # Check if username exists
        if not errors:
            existing_admin = db.get_admin_by_username(username)
            if existing_admin:
                errors.append('Username already exists')
        
        if errors:
            print(f"❌ Validation errors: {errors}")
            return render_template('register.html', errors=errors)
        
        # Create admin
        print(f"➕ Creating admin with username: {username}")
        admin_data = {
            'username': username,
            'email': email,
            'password': password,
            'full_name': full_name
        }
        
        admin_id = db.add_admin(admin_data)
        
        if admin_id:
            print(f"✅ Admin created successfully with ID: {admin_id}")
            return redirect(url_for('login'))
        else:
            errors = ['Error creating admin account. Please try again.']
            print("❌ Error creating admin")
            return render_template('register.html', errors=errors)
    
    print("✅ Rendering register.html template")
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Logout admin"""
    if 'admin_id' in session:
        admin_id = session['admin_id']
        ip_address = request.remote_addr
        db.log_activity(admin_id, 'LOGOUT', f'Logged out from {ip_address}', ip_address)
    
    session.clear()
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    """Admin profile page"""
    admin = get_admin_info()
    activity_logs = db.get_activity_logs(admin['id'], limit=20)
    return render_template('profile.html', admin=admin, activity_logs=activity_logs)

# ========== STUDENT ROUTES (PROTECTED) ==========

@app.route('/')
def index():
    """Dashboard - Show all students"""
    # Check if user is logged in
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    admin = get_admin_info()
    students = db.get_all_students()
    
    # Log activity
    db.log_activity(admin['id'], 'VIEW_DASHBOARD', 'Viewed dashboard')
    
    return render_template('index.html', students=students, admin=admin)

@app.route('/add-student', methods=['GET', 'POST'])
def add_student():
    """Add new student"""
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    admin = get_admin_info()
    
    if request.method == 'POST':
        student_data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'enrollment_number': request.form.get('enrollment_number'),
            'course': request.form.get('course'),
            'dob': request.form.get('dob') or None
        }
        
        student_id = db.add_student(student_data)
        
        if student_id:
            # Log activity
            db.log_activity(admin['id'], 'ADD_STUDENT', 
                          f'Added student: {student_data["name"]} ({student_data["enrollment_number"]})')
            
            return redirect(url_for('view_student', student_id=student_id))
    
    return render_template('add_student.html', admin=admin)

@app.route('/student/<int:student_id>')
def view_student(student_id):
    """View student details"""
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    admin = get_admin_info()
    student = db.get_student(student_id)
    grades = db.get_student_grades(student_id)
    attendance = db.get_student_attendance(student_id)
    
    if not student:
        return "Student not found", 404
    
    # Log activity
    db.log_activity(admin['id'], 'VIEW_STUDENT', f'Viewed student: {student["name"]}')
    
    return render_template('view_student.html', 
                         student=student, 
                         grades=grades,
                         attendance=attendance,
                         admin=admin)

@app.route('/student/<int:student_id>/edit', methods=['GET', 'POST'])
def edit_student(student_id):
    """Edit student"""
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    admin = get_admin_info()
    student = db.get_student(student_id)
    
    if request.method == 'POST':
        student_data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'course': request.form.get('course'),
            'dob': request.form.get('dob') or None
        }
        
        db.update_student(student_id, student_data)
        
        # Log activity
        db.log_activity(admin['id'], 'EDIT_STUDENT', 
                      f'Edited student: {student_data["name"]}')
        
        return redirect(url_for('view_student', student_id=student_id))
    
    return render_template('edit_student.html', student=student, admin=admin)

@app.route('/student/<int:student_id>/delete', methods=['POST'])
def delete_student(student_id):
    """Delete student"""
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    admin = get_admin_info()
    student = db.get_student(student_id)
    
    if student:
        db.delete_student(student_id)
        
        # Log activity
        db.log_activity(admin['id'], 'DELETE_STUDENT', 
                      f'Deleted student: {student["name"]}')
    
    return redirect(url_for('index'))

# ========== GRADES ROUTES ==========

@app.route('/api/grades', methods=['POST'])
def add_grade():
    """Add grade for student"""
    if 'admin_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    try:
        admin = get_admin_info()
        data = request.json
        result = db.add_grade(
            int(data['student_id']),
            data['subject'],
            float(data['marks'])
        )
        
        if result:
            db.log_activity(admin['id'], 'ADD_GRADE', 
                          f'Added grade for student ID: {data["student_id"]}, Subject: {data["subject"]}')
        
        return jsonify({'success': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ========== ATTENDANCE ROUTES ==========

@app.route('/attendance')
def attendance():
    """Attendance page"""
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    admin = get_admin_info()
    students = db.get_all_students()
    return render_template('attendance.html', students=students, admin=admin)

@app.route('/api/attendance', methods=['POST'])
def mark_attendance():
    """Mark attendance"""
    if 'admin_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    try:
        admin = get_admin_info()
        data = request.json
        result = db.mark_attendance(
            int(data['student_id']),
            data['date'],
            data['status']
        )
        
        if result:
            db.log_activity(admin['id'], 'MARK_ATTENDANCE', 
                          f'Marked attendance for student ID: {data["student_id"]}, Status: {data["status"]}')
        
        return jsonify({'success': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ========== SEARCH ROUTES ==========

@app.route('/api/search')
def search():
    """Search students"""
    if 'admin_id' not in session:
        return jsonify([])
    
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    results = db.search_students(query)
    return jsonify(results)

# ========== ERROR HANDLERS ==========

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error_code=404, message="Page not found"), 404

@app.errorhandler(500)
def server_error(error):
    print(f"Server error: {error}")
    return render_template('error.html', error_code=500, message="Internal server error"), 500

if __name__ == '__main__':
    print("Starting Student Management System...")
    print("Open your browser and go to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)