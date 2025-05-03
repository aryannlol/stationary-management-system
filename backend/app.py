from flask import Flask, request, jsonify, send_from_directory,make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum;
import jwt
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import os
import pandas as pd  # ✅ Added for Excel processing
from flask import current_app

from io import StringIO, BytesIO
import csv


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
from functools import wraps

def role_required(*required_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(current_user, *args, **kwargs):
            if current_user.role not in required_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(current_user, *args, **kwargs)
        return decorated_function
    return decorator

# Authentication middleware - MOVED TO TOP BEFORE ROUTES
def generate_token(self, expires_in=8 * 60 * 60):  # 8 hours
        payload = {
            'id': self.id,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in)
        }
        return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
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
    __table_args__ = (
        db.Index('idx_name_search', 'name'),  # For faster searching
        db.Index('idx_stock_status', 'stock', 'low_stock_threshold'),  # For inventory alerts
    )
    __tablename__ = 'inventory'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    stock = db.Column(db.Integer, nullable=False)
    low_stock_threshold = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(db.Model):
    
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(50))
    record_id = db.Column(db.Integer)
    action = db.Column(db.String(10))  # INSERT/UPDATE/DELETE
    old_values = db.Column(db.JSON)
    new_values = db.Column(db.JSON)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

class EmployeeRequest(db.Model):
    __table_args__ = (
        db.Index('idx_request_status', 'status'),  # Faster status filtering
        db.Index('idx_employee_items', 'employee_id', 'item_id'),  # For user-item analysis
    )
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
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    item = db.relationship('Inventory', backref=db.backref('supplier_orders', lazy='dynamic'))
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
# In app.py, replace the existing /admin/requests route
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
                'stock': item.stock if item else 0,  # Add stock
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
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 8  # Items per page

    query = Inventory.query
    
    if search:
        query = query.filter(Inventory.name.ilike(f'%{search}%'))

    paginated_items = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'items': [{
            'id': item.id,
            'name': item.name,
            'stock': item.stock,
            'description': item.description
        } for item in paginated_items.items],
        'total_pages': paginated_items.pages,
        'current_page': page
    })
@app.route('/users', methods=['GET'])
@token_required
def get_users(current_user):
    if current_user.role != 'admin':
        print(f"Unauthorized access by user {current_user.id}")
        return jsonify({'message': 'Access denied'}), 403

    try:
        role = request.args.get('role')
        if role:
            users = User.query.filter_by(role=role).all()
        else:
            users = User.query.all()
        print(f"Fetched {len(users)} users with role={role or 'all'}")
        return jsonify([{
            'id': user.id,
            'username': user.username,
            'role': user.role
        } for user in users]), 200
    except Exception as e:
        print(f"Error fetching users: {str(e)}")
        return jsonify({'message': f'Failed to fetch users: {str(e)}'}), 500

@app.route('/supplier-orders', methods=['POST'])
@token_required
def place_supplier_order(current_user):
    if current_user.role != 'admin':
        print(f"Unauthorized access by user {current_user.id}")
        return jsonify({'message': 'Access denied'}), 403

    try:
        data = request.get_json()
        if not data:
            print("No JSON data provided")
            return jsonify({'message': 'Missing request body'}), 400

        item_id = data.get('item_id')
        quantity = data.get('quantity')
        supplier_id = data.get('supplier_id')

        if not all([item_id, quantity, supplier_id]):
            print(f"Missing fields: item_id={item_id}, quantity={quantity}, supplier_id={supplier_id}")
            return jsonify({'message': 'Missing required fields'}), 400

        if not isinstance(quantity, int) or quantity <= 0:
            print(f"Invalid quantity: {quantity}")
            return jsonify({'message': 'Quantity must be a positive integer'}), 400

        item = Inventory.query.get(item_id)
        if not item:
            print(f"Item not found: item_id={item_id}")
            return jsonify({'message': 'Item not found'}), 404

        supplier = User.query.get(supplier_id)
        if not supplier:
            print(f"Supplier not found: supplier_id={supplier_id}")
            return jsonify({'message': 'Supplier not found'}), 404
        if supplier.role != 'supplier':
            print(f"User is not a supplier: supplier_id={supplier_id}, role={supplier.role}")
            return jsonify({'message': 'User is not a supplier'}), 400

        new_order = SupplierOrder(
            item_id=item_id,
            quantity=quantity,
            supplier_id=supplier_id,
            status='pending',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(new_order)
        db.session.commit()
        print(f"Supplier order created: item_id={item_id}, quantity={quantity}, supplier_id={supplier_id}")
        return jsonify({'message': 'Order placed successfully'}), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error creating supplier order: {str(e)}")
        return jsonify({'message': f'Failed to place order: {str(e)}'}), 500

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
            existing_item = Inventory.query.filter_by(name=item['name'], description=item['description']).first()

            if existing_item:
                # ✅ If item exists, update stock instead of inserting a duplicate
                existing_item.stock += item['stock']
                existing_item.updated_at = datetime.utcnow()
            else:
                # ✅ If item does not exist, insert it as a new entry
                new_item = Inventory(**item)
                db.session.add(new_item)

        db.session.commit()
        return jsonify({'message': 'Inventory uploaded successfully'}), 200

    except Exception as e:
        db.session.rollback()  # Rollback if any error occurs
        return jsonify({'message': f'Error processing file: {str(e)}'}), 500
# Employee Order History
@app.route('/employee/orders', methods=['GET'])
@token_required  # This ensures only logged-in users can access
def get_employee_orders(current_user):
    try:
        requests = EmployeeRequest.query.filter_by(
            employee_id=current_user.id
        ).join(Inventory).all()
        
        return jsonify([{
            'item_name': req.item.name,
            'quantity': req.quantity,
            'status': req.status,
            'date': req.created_at.strftime('%Y-%m-%d')
        } for req in requests])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    
# Export to CSV
@app.route('/employee/orders/export', methods=['GET'])
@token_required
def export_employee_orders(current_user):
    try:
        requests = EmployeeRequest.query.filter_by(
            employee_id=current_user.id
        ).join(Inventory).all()

        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Item', 'Quantity', 'Status', 'Date'])
        
        # Data
        for req in requests:
            writer.writerow([
                req.item.name,
                req.quantity,
                req.status,
                req.created_at.strftime('%Y-%m-%d')
            ])

        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=my_orders.csv'
        response.headers['Content-type'] = 'text/csv'
        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Admin Export (All Orders)
@app.route('/admin/orders/export', methods=['GET'])
@token_required
@role_required('admin')
def export_all_orders(current_user):
    try:
        requests = EmployeeRequest.query.join(
            Inventory
        ).join(
            User
        ).add_columns(
            User.username,
            Inventory.name,
            EmployeeRequest.quantity,
            EmployeeRequest.status,
            EmployeeRequest.created_at
        ).all()

        df = pd.DataFrame([{
            'Employee': req.username,
            'Item': req.name,
            'Quantity': req.quantity,
            'Status': req.status,
            'Date': req.created_at.strftime('%Y-%m-%d')
        } for req in requests])

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='All Orders', index=False)
        
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=all_orders.xlsx'
        response.headers['Content-type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/supplier-orders', methods=['GET'])
@token_required
def get_supplier_orders(current_user):
    try:
        if current_user.role == 'admin':
            orders = SupplierOrder.query.all()
        else:
            orders = SupplierOrder.query.filter_by(supplier_id=current_user.id).all()
        print(f"Fetched {len(orders)} supplier orders for user {current_user.id}")
        return jsonify([{
            'id': order.id,
            'item_name': order.item.name if order.item else 'Unknown Item',
            'quantity': order.quantity,
            'status': order.status,
            'created_at': order.created_at.strftime('%Y-%m-%d')
        } for order in orders]), 200
    except Exception as e:
        print(f"Error fetching supplier orders: {str(e)}")
        return jsonify({'message': f'Failed to fetch orders: {str(e)}'}), 500
    
    
@app.route('/supplier-orders/<int:order_id>', methods=['PATCH'])
@token_required
def update_supplier_order(current_user, order_id):
    if current_user.role != 'supplier':
        return jsonify({'message': 'Access denied'}), 403

    data = request.json
    status = data.get('status')
    if status not in ['shipped', 'delivered']:
        return jsonify({'message': 'Invalid status'}), 400

    order = SupplierOrder.query.get(order_id)
    if not order or order.supplier_id != current_user.id:
        return jsonify({'message': 'Order not found'}), 404

    order.status = status
    if status == 'delivered':
        item = Inventory.query.get(order.item_id)
        if item:
            item.stock += order.quantity
            item.updated_at = datetime.utcnow()

    db.session.commit()
    return jsonify({'message': f'Order {status} successfully'}), 200



@app.route('/admin/orders', methods=['GET'])
@token_required
@role_required('admin')  # Now properly defined
def get_all_orders(current_user):
    try:
        requests = db.session.query(
            EmployeeRequest,
            User.username,
            Inventory.name
        ).join(
            User, EmployeeRequest.employee_id == User.id
        ).join(
            Inventory, EmployeeRequest.item_id == Inventory.id
        ).all()

        orders = [{
            'employee_name': username,
            'item_name': item_name,
            'quantity': req.quantity,
            'status': req.status,
            'created_at': req.created_at.isoformat()
        } for req, username, item_name in requests]

        return jsonify(orders)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

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