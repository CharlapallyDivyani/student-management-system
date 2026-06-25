import mysql.connector
from mysql.connector import Error
from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, MYSQL_PORT
from werkzeug.security import generate_password_hash, check_password_hash

class Database:
    def __init__(self):
        """Initialize database connection"""
        self.host = MYSQL_HOST
        self.user = MYSQL_USER
        self.password = MYSQL_PASSWORD
        self.database = MYSQL_DATABASE
        self.port = MYSQL_PORT
        self.test_connection()
    
    def test_connection(self):
        """Test if database connection works"""
        try:
            conn = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                port=self.port
            )
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()
            print("✓ MySQL connection successful!")
            return True
        except Error as e:
            print(f"✗ MySQL connection failed: {e}")
            return False
    
    def get_connection(self):
        """Get a new database connection"""
        try:
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port
            )
            return connection
        except Error as e:
            print(f"✗ Error connecting to database: {e}")
            return None
    
    def execute_query(self, query, params=None):
        """Execute query (INSERT, UPDATE, DELETE)"""
        connection = self.get_connection()
        if not connection:
            return None
        
        cursor = None
        try:
            cursor = connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            connection.commit()
            return cursor
        except Error as e:
            if connection:
                connection.rollback()
            print(f"✗ Database error: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def fetch_query(self, query, params=None):
        """Fetch query results"""
        connection = self.get_connection()
        if not connection:
            return []
        
        cursor = None
        try:
            cursor = connection.cursor(dictionary=True)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            results = cursor.fetchall()
            return results
        except Error as e:
            print(f"✗ Database error: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def fetch_one(self, query, params=None):
        """Fetch single record"""
        connection = self.get_connection()
        if not connection:
            return None
        
        cursor = None
        try:
            cursor = connection.cursor(dictionary=True)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchone()
            return result
        except Error as e:
            print(f"✗ Database error: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def create_tables(self):
        """Create all necessary tables"""
        print("\n🔄 Creating tables...")
        
        self.execute_query('''
            CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE,
                phone VARCHAR(15),
                enrollment_number VARCHAR(50) UNIQUE NOT NULL,
                course VARCHAR(100),
                dob DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_enrollment (enrollment_number),
                INDEX idx_email (email)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')
        print("  ✓ Students table created")
        
        self.execute_query('''
            CREATE TABLE IF NOT EXISTS grades (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                subject VARCHAR(100) NOT NULL,
                marks DECIMAL(5,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                INDEX idx_student (student_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')
        print("  ✓ Grades table created")
        
        self.execute_query('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                date DATE NOT NULL,
                status VARCHAR(20) DEFAULT 'Present',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                UNIQUE KEY unique_attendance (student_id, date),
                INDEX idx_student (student_id),
                INDEX idx_date (date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')
        print("  ✓ Attendance table created")
        
        self.execute_query('''
            CREATE TABLE IF NOT EXISTS admins (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(100),
                role VARCHAR(50) DEFAULT 'admin',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL,
                INDEX idx_username (username),
                INDEX idx_email (email)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')
        print("  ✓ Admins table created")
        
        self.execute_query('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                admin_id INT NOT NULL,
                action VARCHAR(255),
                description TEXT,
                ip_address VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE,
                INDEX idx_admin (admin_id),
                INDEX idx_date (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')
        print("  ✓ Activity logs table created")
        
        print("✓ All tables created successfully!\n")
    
    # ========== STUDENT OPERATIONS ==========
    
    def add_student(self, student_data):
        """Add new student"""
        cursor = self.execute_query(
            '''INSERT INTO students (name, email, phone, enrollment_number, course, dob)
               VALUES (%s, %s, %s, %s, %s, %s)''',
            (student_data['name'], student_data['email'], student_data['phone'],
             student_data['enrollment_number'], student_data['course'], student_data['dob'])
        )
        return cursor.lastrowid if cursor else None
    
    def get_all_students(self):
        """Get all students"""
        results = self.fetch_query('SELECT * FROM students ORDER BY name')
        return results if results else []
    
    def get_student(self, student_id):
        """Get student by ID"""
        result = self.fetch_one('SELECT * FROM students WHERE id = %s', (student_id,))
        return result
    
    def update_student(self, student_id, student_data):
        """Update student"""
        self.execute_query(
            '''UPDATE students SET name = %s, email = %s, phone = %s, course = %s, dob = %s
               WHERE id = %s''',
            (student_data['name'], student_data['email'], student_data['phone'],
             student_data['course'], student_data['dob'], student_id)
        )
    
    def delete_student(self, student_id):
        """Delete student"""
        self.execute_query('DELETE FROM students WHERE id = %s', (student_id,))
    
    def search_students(self, query):
        """Search students by name or enrollment number"""
        search_query = f'%{query}%'
        results = self.fetch_query(
            '''SELECT * FROM students 
               WHERE name LIKE %s OR enrollment_number LIKE %s OR email LIKE %s
               ORDER BY name''',
            (search_query, search_query, search_query)
        )
        return results if results else []
    
    # ========== GRADE OPERATIONS ==========
    
    def add_grade(self, student_id, subject, marks):
        """Add grade for student"""
        cursor = self.execute_query(
            'INSERT INTO grades (student_id, subject, marks) VALUES (%s, %s, %s)',
            (student_id, subject, marks)
        )
        return True if cursor else False
    
    def get_student_grades(self, student_id):
        """Get all grades for student"""
        results = self.fetch_query(
            'SELECT * FROM grades WHERE student_id = %s ORDER BY created_at DESC',
            (student_id,)
        )
        return results if results else []
    
    # ========== ATTENDANCE OPERATIONS ==========
    
    def mark_attendance(self, student_id, date, status):
        """Mark attendance for student"""
        connection = self.get_connection()
        if not connection:
            return False
        
        cursor = None
        try:
            cursor = connection.cursor()
            cursor.execute(
                'SELECT id FROM attendance WHERE student_id = %s AND date = %s',
                (student_id, date)
            )
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute(
                    'UPDATE attendance SET status = %s WHERE student_id = %s AND date = %s',
                    (status, student_id, date)
                )
            else:
                cursor.execute(
                    'INSERT INTO attendance (student_id, date, status) VALUES (%s, %s, %s)',
                    (student_id, date, status)
                )
            
            connection.commit()
            return True
        except Error as e:
            connection.rollback()
            print(f"✗ Database error: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def get_student_attendance(self, student_id):
        """Get attendance for student"""
        results = self.fetch_query(
            'SELECT * FROM attendance WHERE student_id = %s ORDER BY date DESC',
            (student_id,)
        )
        return results if results else []
    
    def get_attendance_by_date(self, date):
        """Get all attendance for a specific date"""
        results = self.fetch_query(
            'SELECT * FROM attendance WHERE date = %s',
            (date,)
        )
        return results if results else []
    
    # ========== ADMIN OPERATIONS ==========
    
    def add_admin(self, admin_data):
        """Add new admin user"""
        print(f"\n🔐 Creating admin: {admin_data['username']}")
        
        password = admin_data['password']
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        
        print(f"   Password entered: {password}")
        print(f"   Password hashed: {password_hash[:50]}...")
        
        cursor = self.execute_query(
            '''INSERT INTO admins (username, email, password_hash, full_name, role)
               VALUES (%s, %s, %s, %s, %s)''',
            (admin_data['username'], admin_data['email'], password_hash, 
             admin_data['full_name'], admin_data.get('role', 'admin'))
        )
        
        if cursor:
            print(f"✓ Admin created successfully!\n")
            return cursor.lastrowid
        else:
            print(f"✗ Failed to create admin\n")
            return None
    
    def get_admin_by_username(self, username):
        """Get admin by username"""
        result = self.fetch_one('SELECT * FROM admins WHERE username = %s', (username,))
        return result
    
    def get_admin_by_id(self, admin_id):
        """Get admin by ID"""
        result = self.fetch_one('SELECT * FROM admins WHERE id = %s', (admin_id,))
        return result
    
    def verify_admin_password(self, username, password):
        """Verify admin password"""
        print(f"\n🔐 Attempting login for: {username}")
        print(f"   Password entered: {password}")
        
        admin = self.get_admin_by_username(username)
        
        if not admin:
            print(f"✗ Admin '{username}' not found in database\n")
            return None
        
        print(f"   Found admin in database")
        print(f"   Stored hash: {admin['password_hash'][:50]}...")
        
        is_correct = check_password_hash(admin['password_hash'], password)
        print(f"   Password match: {is_correct}\n")
        
        if is_correct:
            print(f"✓ Login successful!\n")
            return admin
        else:
            print(f"✗ Password incorrect\n")
            return None
    
    def update_admin_last_login(self, admin_id):
        """Update last login time"""
        self.execute_query(
            'UPDATE admins SET last_login = NOW() WHERE id = %s',
            (admin_id,)
        )
    
    def get_all_admins(self):
        """Get all admin users"""
        results = self.fetch_query('SELECT id, username, email, full_name, role, created_at, last_login FROM admins ORDER BY created_at DESC')
        return results if results else []
    
    def delete_admin(self, admin_id):
        """Delete an admin user"""
        self.execute_query('DELETE FROM admins WHERE id = %s', (admin_id,))
    
    def log_activity(self, admin_id, action, description, ip_address=None):
        """Log admin activity"""
        self.execute_query(
            '''INSERT INTO activity_logs (admin_id, action, description, ip_address)
               VALUES (%s, %s, %s, %s)''',
            (admin_id, action, description, ip_address)
        )
    
    def get_activity_logs(self, admin_id=None, limit=100):
        """Get activity logs"""
        if admin_id:
            results = self.fetch_query(
                '''SELECT * FROM activity_logs WHERE admin_id = %s 
                   ORDER BY created_at DESC LIMIT %s''',
                (admin_id, limit)
            )
        else:
            results = self.fetch_query(
                '''SELECT * FROM activity_logs 
                   ORDER BY created_at DESC LIMIT %s''',
                (limit,)
            )
        return results if results else []
    
    def get_admin_count(self):
        """Get total number of admins"""
        try:
            result = self.fetch_one('SELECT COUNT(*) as count FROM admins')
            if result and 'count' in result:
                return result['count']
            return 0
        except Exception as e:
            print(f"✗ Error getting admin count: {e}")
            return 0