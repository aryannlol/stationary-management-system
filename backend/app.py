from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum;
import jwt
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import os
import pandas as pd  # ✅ Added for Excel processing



# Initialize Flask app
app = Flask(__name__, static_folder="../frontend", template_folder="../frontend")
CORS(app, supports_credentials=True, origins=["http://127.0.0.1:5500"]) 
  # Add this line to enable CORS

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:minecraft%40OP1@localhost/stationary_management'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
SECRET_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MTUsInJvbGUiOiJlbXBsb3llZSIsImV4cCI6MTczOTQ3MjkzMH0.7lvZULEW69kSVRuqkpcCf38Cz2-CA_-bDOWJrddAeiQ"
app.config["SECRET_KEY"] = SECRET_KEY

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Authentication middleware - MOVED TO TOP BEFORE ROUTES
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token or " " not in token:  # ✅ Safer check
            return jsonify({'message': 'Access denied'}), 401

        try:
            token = token.split(" ")[1]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(data['id'])
            if not current_user:
                return jsonify({'message': 'User not found'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expired. Please log in again.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401

        return f(current_user, *args, **kwargs)
    return decorated



# User Model
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin', 'employee', 'supplier'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_token(self):
        token = jwt.encode(
            {'id': self.id, 'role': self.role, 'exp': datetime.utcnow() + timedelta(hours=1)},
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        return token

# Inventory Model
class Inventory(db.Model):
    __tablename__ = 'inventory'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    stock = db.Column(db.Integer, nullable=False)
    low_stock_threshold = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EmployeeRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory.id'), nullable=False)  # ✅ Fixed
    quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum('pending', 'approved', 'rejected'), default='pending')
    admin_response = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

    employee = db.relationship('User', backref=db.backref('requests', lazy=True))
    item = db.relationship('Inventory', backref=db.backref('requests', lazy=True))  # ✅ Fixed

class SupplierOrder(db.Model):
    __tablename__ = 'supplier_orders'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.Enum('pending', 'shipped', 'delivered'), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TransactionLog(db.Model):
    __tablename__ = 'transaction_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Routes
@app.route('/')
def serve_frontend():
    return send_from_directory(app.template_folder, 'index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(os.path.join(app.static_folder, 'static'), filename)

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    
    if not user or not user.check_password(password):
        return jsonify({'message': 'Invalid username or password'}), 400

    token = user.generate_token()
    return jsonify({'token': token, 'role': user.role})

# Remove the duplicate token_required decorator and keep this version
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token or " " not in token:
            return jsonify({'message': 'Access denied: No token provided'}), 401

        try:
            token = token.split(" ")[1]  # Remove 'Bearer ' prefix
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(data['id'])
            
            if not current_user:
                return jsonify({'message': 'User not found'}), 401
                
            # Add role to request context
            setattr(decorated, 'current_user', current_user)
            return f(current_user, *args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expired. Please log in again.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
    return decorated

def decode_token(token):
    try:
        data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        return data["id"]  # Return user ID from the token
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired. Please log in again."}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401


@app.route("/requests", methods=["GET"])
@token_required
def handle_requests(current_user):
    try:
        if current_user.role == "admin":
            # Admins can see all requests
            requests = EmployeeRequest.query.all()
        else:
            # Employees can only see their own requests
            requests = EmployeeRequest.query.filter_by(employee_id=current_user.id).all()

        request_list = []
        for req in requests:
            item = Inventory.query.get(req.item_id)
            request_list.append({
                "id": req.id,  # Make sure to include the request ID
                "item_name": item.name if item else "Unknown Item",
                "quantity": req.quantity,
                "status": req.status,
                "admin_response": req.admin_response
            })

        return jsonify(request_list), 200

    except Exception as e:
        print("ERROR in handle_requests:", str(e))
        return jsonify({"error": "Internal Server Error"}), 500
# In app.py, modify the submit_request route to not reduce stock on request creation
@app.route("/requests", methods=["POST"])
@token_required
def submit_request(current_user):
    data = request.json
    item_id = data.get("item_id")
    quantity = data.get("quantity")
    reason = data.get("reason", "")

    item = Inventory.query.get(item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    # Only check if stock exists, but don't reduce it yet
    if item.stock < quantity:
        return jsonify({"error": "Not enough stock"}), 400

    # Create request without reducing stock
    new_request = EmployeeRequest(
        employee_id=current_user.id,
        item_id=item_id,
        quantity=quantity,
        reason=reason
    )
    db.session.add(new_request)
    db.session.commit()

    return jsonify({"message": "Request placed successfully!"}), 201

# Update the request update route to handle stock changes
@app.route('/requests/<int:request_id>', methods=['PATCH'])
@token_required
def update_request(current_user, request_id):
    # First check if user is admin
    if current_user.role != 'admin':
        return jsonify({'message': 'Access denied: Admin privileges required'}), 403

    try:
        data = request.json
        new_status = data.get('status')

        if new_status not in ['approved', 'rejected']:
            return jsonify({'message': 'Invalid status'}), 400

        request_item = EmployeeRequest.query.get(request_id)
        if not request_item:
            return jsonify({'message': 'Request not found'}), 404

        # Handle stock reduction for approved requests
        if new_status == 'approved':
            item = Inventory.query.get(request_item.item_id)
            if not item:
                return jsonify({'message': 'Inventory item not found'}), 404

            if item.stock < request_item.quantity:
                return jsonify({'message': 'Insufficient stock'}), 400

            item.stock -= request_item.quantity
            
        request_item.status = new_status
        db.session.commit()

        return jsonify({
            'message': f'Request {new_status} successfully',
            'new_status': new_status
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error in update_request: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500

# Add a route to get admin requests specifically
@app.route('/admin/requests', methods=['GET'])
@token_required
def get_admin_requests(current_user):
    if current_user.role != 'admin':
        return jsonify({'message': 'Access denied: Admin privileges required'}), 403

    try:
        requests = EmployeeRequest.query.all()
        request_list = []
        
        for req in requests:
            item = Inventory.query.get(req.item_id)
            employee = User.query.get(req.employee_id)
            request_list.append({
                'id': req.id,
                'item_name': item.name if item else 'Unknown Item',
                'quantity': req.quantity,
                'status': req.status,
                'employee_name': employee.username if employee else 'Unknown Employee',
                'created_at': req.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
            
        return jsonify(request_list), 200
        
    except Exception as e:
        print(f"Error in get_admin_requests: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500

        
@app.route('/inventory', methods=['GET'])
@token_required
def search_inventory(current_user):
    items = Inventory.query.all()
    return jsonify([
        {'id': item.id, 'name': item.name, 'stock': item.stock}
        for item in items
    ])



@app.route("/requests/clear", methods=["DELETE"])
@token_required
def clear_all_requests(current_user):
    if current_user.role != "admin":
        return jsonify({"error": "Forbidden: Only admins can clear requests."}), 403

    try:
        db.session.query(EmployeeRequest).delete()
        db.session.commit()
        return jsonify({"message": "All requests cleared successfully!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/items', methods=['GET'])
@token_required
def get_items(current_user):
    try:
        items = Inventory.query.all()
        return jsonify([{'id': item.id, 'name': item.name} for item in items])
    except Exception as e:
        return jsonify({'message': f'Error fetching items: {str(e)}'}), 500




@app.route('/supplier-orders', methods=['POST'])
@token_required
def place_supplier_order(current_user):
    if current_user.role != 'admin':
        return jsonify({'message': 'Access denied'}), 403

    data = request.get_json()
    new_order = SupplierOrder(
        item_id=data['item_id'],  # ✅ FIXED: Add item_id
        quantity=data['quantity'],
        supplier_id=data['supplier_id']
    )
    db.session.add(new_order)
    db.session.commit()
    return jsonify({'message': 'Order placed successfully'})

REQUIRED_COLUMNS = {'name', 'description', 'stock', 'low_stock_threshold'}
@app.route('/upload-inventory', methods=['POST'])
@token_required

def upload_inventory(current_user):
    if current_user.role != 'admin':
        return jsonify({'message': 'Access denied'}), 403

    if 'file' not in request.files:
        return jsonify({'message': 'No file uploaded'}), 400

    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    try:
        df = pd.read_excel(file)

        # Convert all column names to lowercase and replace spaces with underscores
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

        # Check if required columns exist
        missing_columns = REQUIRED_COLUMNS - set(df.columns)
        if missing_columns:
            return jsonify({'message': f'Missing required columns: {missing_columns}'}), 400

        # Process and insert into the database
        inventory_data = df.to_dict(orient='records')
        for item in inventory_data:
            # Add to database (assuming SQLAlchemy)
            new_item = Inventory(**item)  
            db.session.add(new_item)
        
        db.session.commit()
        return jsonify({'message': 'Inventory uploaded successfully'}), 200

    except Exception as e:
        return jsonify({'message': f'Error processing file: {str(e)}'}), 500



# Main execution
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        users = [
            {"username": "admin", "password": "admin123", "role": "admin"},
            {"username": "emp", "password": "emp123", "role": "employee"},
            {"username": "supp", "password": "supp123", "role": "supplier"},
        ]
        for user_data in users:
            existing_user = User.query.filter_by(username=user_data["username"]).first()
            if not existing_user:
                new_user = User(username=user_data["username"], role=user_data["role"])
                new_user.set_password(user_data["password"])
                db.session.add(new_user)
        
        db.session.commit()
        print("Admin, Employee & Supplier users added successfully!")

    app.run(debug=True)