import pyodbc
from datetime import datetime

def get_connection():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=DESKTOP-TA1QHNO;'  # E.g., localhost or IP address
        'DATABASE=Final;'  # Your database name
        'Trusted_Connection=yes;'
        )
    return conn

def check_username_exists(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Users WHERE username = ?", username)
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def register_user(username, password, role, owner_name=None, email=None, address=None, phone_number=None, registered_by=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Users (username, password, role) 
            VALUES (?, ?, ?)
        """, username, password, role)
        
        cursor.execute("SELECT @@IDENTITY")
        user_id = cursor.fetchone()[0]
        
        if role == 'user':
            if not registered_by:
                registered_by = user_id

            cursor.execute("""
                INSERT INTO Vehicles 
                (vehicle_number, user_id, owner_name, address, email, phone_number, registered_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, username, user_id, owner_name, address, email, phone_number, registered_by)
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error registering user: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
        
def delete_violation(violation_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Violations WHERE id = ?", violation_id)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting violation: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
        
        
def update_violation_status(violation_id, new_status, deposit_slip_path=None, payment_method=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = "UPDATE Violations SET status = ?, payment_method = ?"
        params = [new_status, payment_method, violation_id]

        if deposit_slip_path:
            query += ", deposit_slip_path = ?"
            params.insert(2, deposit_slip_path)

        query += " WHERE id = ?"

        cursor.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating violation status: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_dashboard_stats(user_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if user_id:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_fines,
                    SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending_fines_count,
                    SUM(CASE WHEN status = 'Paid' THEN 1 ELSE 0 END) as paid_fines_count,
                    SUM(CASE WHEN status = 'Pending' THEN v.fine_amount ELSE 0 END) as total_pending_amount,
                    SUM(CASE WHEN status = 'Paid' THEN v.fine_amount ELSE 0 END) as total_paid_amount,
                    SUM(v.fine_amount) as total_fine_amount
                FROM Violations v
                JOIN ViolationTypes vt ON v.violation_type = vt.id
                WHERE v.user_id = ?
            """, user_id)
        else:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_fines,
                    SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending_fines_count,
                    SUM(CASE WHEN status = 'Paid' THEN 1 ELSE 0 END) as paid_fines_count,
                    SUM(CASE WHEN status = 'Pending' THEN v.fine_amount ELSE 0 END) as total_pending_amount,
                    SUM(CASE WHEN status = 'Paid' THEN v.fine_amount ELSE 0 END) as total_paid_amount,
                    SUM(v.fine_amount) as total_fine_amount
                FROM Violations v
                JOIN ViolationTypes vt ON v.violation_type = vt.id
            """)
        
        return cursor.fetchone()
    except Exception as e:
        print(f"Error fetching dashboard stats: {e}")
        return [0, 0, 0, 0, 0, 0]
    finally:
        conn.close()

def get_user_by_credentials(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE username = ? AND password = ?", username, password)
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "username": row[1], "role": row[3]}
    return None

def fetch_vehicle_details(vehicle_number):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Vehicles WHERE vehicle_number = ?", vehicle_number)
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "owner_name": row[3],
            "address": row[4],
            "email": row[5],
            "phone_number": row[6],
            "user_id": row[2] 
        }
    return None

def get_vehicle_user_id(vehicle_number):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM Vehicles WHERE vehicle_number = ?", vehicle_number)
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def fetch_violation_types():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ViolationTypes")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "name": row[1], "fine_amount": row[2]} for row in rows]

def add_violation(vehicle_number, violation_type_id, user_id, officer_id, image_path=None, confidence=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT fine_amount FROM ViolationTypes WHERE id = ?", violation_type_id)
        violation_row = cursor.fetchone()
        if not violation_row:
            return False
        
        # Get the fine amount
        fine_amount = violation_row[0]

        cursor.execute("""
            INSERT INTO Violations 
            (vehicle_number, violation_type, user_id, timestamp, status, issued_by, image_path, confidence, fine_amount) 
            VALUES (?, ?, ?, GETDATE(), 'Pending', ?, ?, ?, ?)
        """, vehicle_number, violation_type_id, user_id, officer_id, image_path, confidence, fine_amount)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding violation: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
        
def fetch_all_vehicle_numbers():
    """
    Fetch all vehicle numbers from the Vehicles table.
    
    Returns:
        list: List of vehicle numbers
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT vehicle_number FROM Vehicles")
        vehicle_numbers = [row[0] for row in cursor.fetchall()]
        return vehicle_numbers
    except Exception as e:
        print(f"Error fetching vehicle numbers: {e}")
        return []
    finally:
        conn.close()

def get_violations(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            v.id,
            v.vehicle_number, 
            vt.name AS violation_type, 
            v.fine_amount, 
            v.timestamp,
            v.status,
            u.username AS officer_id,
            v.image_path
        FROM Violations v
        JOIN ViolationTypes vt ON v.violation_type = vt.id
        JOIN Users u ON v.issued_by = u.id
        WHERE v.user_id = ?
        ORDER BY v.timestamp DESC
    """, user_id)
    rows = cursor.fetchall()
    conn.close()
    return [{
        "id": row[0], 
        "vehicle_number": row[1], 
        "violation_type": row[2], 
        "fine_amount": row[3],
        "timestamp": row[4].strftime('%Y-%m-%d %H:%M:%S') if isinstance(row[4], datetime) else row[4],
        "status": row[5],
        "officer_id": row[6],
        "image_path": row[7]
    } for row in rows]
    

def get_fines_history(officer_id=None, vehicle_number=""):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = """
            SELECT 
                v.id,
                v.vehicle_number,
                u.username as officer_id,
                vt.name as violation_type,
                v.fine_amount,
                v.timestamp,
                v.status
            FROM Violations v
            JOIN Users u ON v.issued_by = u.id
            JOIN ViolationTypes vt ON v.violation_type = vt.id
            WHERE 1=1
        """
        params = []
        
        if officer_id:
            query += " AND u.username = ?"
            params.append(officer_id)
            
        if vehicle_number:
            query += " AND v.vehicle_number LIKE ?"
            params.append(f"%{vehicle_number}%")
            
        query += " ORDER BY v.timestamp DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [{
            "id": row[0],
            "vehicle_number": row[1],
            "officer_id": row[2],
            "violation_type": row[3],
            "fine_amount": float(row[4]),
            "timestamp": row[5].strftime("%Y-%m-%d %H:%M:%S"),
            "status": row[6]
        } for row in rows]
        
    except Exception as e:
        print(f"Error fetching fines history: {e}")
        return []
    finally:
        conn.close()

def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                id,
                username,
                role,
                created_at
            FROM Users
            WHERE role = 'user'
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        
        return [{
            "id": row[0],
            "username": row[1],
            "role": row[2],
            "created_at": row[3].strftime("%Y-%m-%d %H:%M:%S") if row[3] else None
        } for row in rows]
        
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []
    finally:
        conn.close()

def get_fine_details(category, vehicle_number=""):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = """
            SELECT 
                v.id,
                v.vehicle_number,
                u.username as officer_id,
                vt.name as violation_type,
                vt.fine_amount,
                v.timestamp,
                v.status
            FROM Violations v
            JOIN Users u ON v.issued_by = u.id
            JOIN ViolationTypes vt ON v.violation_type = vt.id
            WHERE 1=1
        """
        params = []
        
        if category == "pending":
            query += " AND v.status = 'Pending'"
            
        if vehicle_number:
            query += " AND v.vehicle_number LIKE ?"
            params.append(f"%{vehicle_number}%")
            
        query += " ORDER BY v.timestamp DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [{
            "id": row[0],
            "vehicle_number": row[1],
            "officer_id": row[2],
            "violation_type": row[3],
            "fine_amount": float(row[4]),
            "timestamp": row[5].strftime("%Y-%m-%d %H:%M:%S"),
            "status": row[6]
        } for row in rows]
        
    except Exception as e:
        print(f"Error fetching fine details: {e}")
        return []
    finally:
        conn.close()
        

def get_vehicles_by_admin(admin_id):
       conn = get_connection()
       cursor = conn.cursor()
       try:
           cursor.execute("""
               SELECT 
                   v.vehicle_number,
                   v.owner_name,
                   v.address,
                   v.email,
                   v.phone_number,
                   u.password
               FROM Vehicles v
               JOIN Users u ON v.user_id = u.id
               WHERE v.registered_by = ?
           """, admin_id)
           
           vehicles = [{
               "vehicle_number": row[0],
               "owner_name": row[1],
               "address": row[2],
               "email": row[3],
               "phone_number": row[4],
               "password": row[5]
           } for row in cursor.fetchall()]
           
           return vehicles
       except Exception as e:
           print(f"Error fetching vehicles by admin: {e}")
           return []
       finally:
           conn.close()

def delete_vehicle(vehicle_number):
    """
    Delete a vehicle and its associated user account.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM Vehicles WHERE vehicle_number = ?", vehicle_number)
        result = cursor.fetchone()
        if not result:
            return False
            
        user_id = result[0]
        
        cursor.execute("DELETE FROM Vehicles WHERE vehicle_number = ?", vehicle_number)
        
        cursor.execute("DELETE FROM Users WHERE id = ?", user_id)
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting vehicle: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_all_violation_types():
    """
    Fetch all violation types with their details.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, name, fine_amount FROM ViolationTypes ORDER BY name")
        
        violation_types = [{
            "id": row[0],
            "name": row[1],
            "fine_amount": float(row[2])
        } for row in cursor.fetchall()]
        
        return violation_types
    except Exception as e:
        print(f"Error fetching violation types: {e}")
        return []
    finally:
        conn.close()

def update_fine_amount(violation_id, new_amount):
    """
    Update the fine amount for a specific violation type.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE ViolationTypes SET fine_amount = ? WHERE id = ?",
            (new_amount, violation_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating fine amount: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
        
def get_violation_details(violation_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                v.vehicle_number,
                vt.name AS violation_type,
                vt.fine_amount,
                v.timestamp,
                v.status,
                u.username AS officer_id,
                v.payment_method
            FROM Violations v
            JOIN ViolationTypes vt ON v.violation_type = vt.id
            JOIN Users u ON v.issued_by = u.id
            WHERE v.id = ?
        """, violation_id)
        
        row = cursor.fetchone()

        if row:
            return {
                "vehicle_number": row[0],
                "violation_type": row[1],
                "fine_amount": row[2],
                "timestamp": row[3].strftime('%Y-%m-%d %H:%M:%S'),
                "status": row[4],
                "officer_id": row[5],
                "payment_method": row[6]
            }
        return None
    except Exception as e:
        print(f"Error fetching violation details: {e}")
        return None
    finally:
        conn.close()
        
def get_user_by_vehicle_and_phone(vehicle_number, phone_number):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, u.username
        FROM Users u
        JOIN Vehicles v ON u.id = v.user_id
        WHERE v.vehicle_number = ? AND v.phone_number = ?
    """, vehicle_number, phone_number)
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"id": user[0], "username": user[1]}
    return None

def update_user_password(user_id, new_password):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE Users
            SET password = ?
            WHERE id = ?
        """, new_password, user_id)
        conn.commit()
    except Exception as e:
        print(f"Error updating password: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
    return True

def update_user_profile(vehicle_number, owner_name, email, address, phone_number):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE Vehicles
            SET owner_name = ?, email = ?, address = ?, phone_number = ?
            WHERE vehicle_number = ?
        """, owner_name, email, address, phone_number, vehicle_number)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating user profile: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
        
def fetch_all_vehicle_numbers_details():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT vehicle_number, owner_name, address, email, phone_number FROM Vehicles")
        rows = cursor.fetchall()
        return [{
            "vehicle_number": row[0],
            "owner_name": row[1],
            "address": row[2],
            "email": row[3],
            "phone_number": row[4]
        } for row in rows]
    except Exception as e:
        print(f"Error fetching vehicle details: {e}")
        return []
    finally:
        conn.close()