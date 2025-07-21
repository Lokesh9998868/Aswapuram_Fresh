import os # For file path handling
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash
import uuid # For generating unique IDs for products and orders
from flask_sqlalchemy import SQLAlchemy # Corrected: SQLAlchemy (no extra 'A')
from datetime import datetime # to get current date for orders
from functools import wraps # For creating decorators
from flask_wtf import FlaskForm # For form handling (if needed in the future)
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError
import re # For UPI ID validation
from urllib.parse import quote_plus
from uuid import uuid4
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user



logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Initialize Flask app
app = Flask(__name__)

# --- Database Configuration for PostgreSQL ---
# IMPORTANT: Replace 'lokesh9' with your actual password if it's different
# Make sure your PostgreSQL server is running and the database 'aswapuram_fresh_db' exists
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')# Corrected: Removed misleading MySQL comment
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get(SECRET_KEY, 'default_secret_key_for_dev')
import os

# Initialize Flask app
app = Flask(__name__)

# --- Database Configuration for PostgreSQL ---
# IMPORTANT: Replace 'lokesh9' with your actual password if it's different
# Make sure your PostgreSQL server is running and the database 'aswapuram_fresh_db' exists
#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://flaskuser:lokesh9@localhost:5432/aswapuram_fresh_db' # Corrected: Removed misleading MySQL comment
#app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#app.secret_key = 'lokesh123'


app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("postgresql://aswapuram_fresh_db_user:gsUgYkR3EhW6DeQKswS8ptGjjbtslwt1@dpg-d1t4osh5pdvs73d70vpg-a.oregon-postgres.render.com/aswapuram_fresh_db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# Initialize the database
db = SQLAlchemy(app)

from models import User, Product, Order, OrderItem, Transaction

@app.before_first_request
def create_tables():
    logging.info("Attempting to create database tables...")
    try:
        db.create_all() # This creates all tables defined in your models if they don't exist
        logging.info("Database tables created successfully (if they didn't exist).")
    except Exception as e:
        logging.error(f"Error creating database tables: {e}", exc_info=True)


# --- Flask-Login Setup --- # ADD THIS SECTION
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # This tells Flask-Login what route to redirect to if a user needs to log in
login_manager.login_message = 'Please log in to access this page.' # Optional: custom message
login_manager.login_message_category = 'warning'

# --- Database Models ---
class User(db.Model, UserMixin):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    orders = db.relationship('Order', backref='customer', lazy=True)

    def __repr__(self):
        return f"User('{self.email}', '{self.name}', Admin: {self.is_admin})"

# CORRECTED INDENTATION: Product class is now at the top level, not nested in User
class Product(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(50), nullable=True)
    image = db.Column(db.String(200), nullable=True, default='default_product.png')

    def __repr__(self):
        return f"Product('{self.name}', {self.price}, {self.unit})"
    @property
    def is_authenticated(self):
        # A user is authenticated if they have provided valid credentials.
        return True # Since you only call login_user after successful password check

    @property
    def is_active(self):
        # All users in your system are active unless you implement a "banned" status
        return True

    @property
    def is_anonymous(self):
        # Anonymous users are not logged in. Your users are not anonymous if they reach this point.
        return False

    def get_id(self):
        # Return the unique ID for the user
        return str(self.id)

# CORRECTED INDENTATION: Order class is now at the top level
class Order(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_email = db.Column(db.String(120), db.ForeignKey('user.email'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    delivery_address = db.Column(db.String(255), nullable=True)
    payment_method = db.Column(db.String(50), nullable=False, default='cod')
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"Order('{self.id}', '{self.user_email}', '{self.status}', Total: {self.total_amount})"

# CORRECTED INDENTATION: OrderItem class is now at the top level
class OrderItem(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = db.Column(db.String(36), db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey('product.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    product_price_at_order = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product_unit = db.Column(db.String(50), nullable=True)
    product = db.relationship('Product', lazy=True)

    def __repr__(self):
        return f"OrderItem('{self.product_name}', Qty: {self.quantity}, Order: {self.order_id})"

class Transaction(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())) # Changed to String(36) and uuid4 for consistency
    order_id = db.Column(db.String(36), db.ForeignKey('order.id'), nullable=False) # Link to Order ID
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    transaction_id = db.Column(db.String(100), unique=True, nullable=False) # For UPI's unique tx ID
    status = db.Column(db.String(50), default='Pending', nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Transaction {self.transaction_id} for Order {self.order_id} - {self.status}>"
# REMOVED: Old in-memory Data Storage comments (no longer applicable)

# --- Helper Functions (for admin access control) ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or not session.get('is_admin'):
            flash('Admin access required.', 'danger')
            session['redirect_after_login'] = request.url
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# app.py (after your User model definition)

@login_manager.user_loader
def load_user(user_id):
    # Flask-Login expects this function to return a user object or None
    # given the user_id from the session.
    # Your User ID is a UUID string, so query by that.
    return User.query.get(user_id)

# --- Helper Functions (for admin access control) ---
# ... (your admin_required decorator) ...

# --- Routes and Views ---

@app.route('/')
def homepage():
    username = session.get('username')
    all_products = Product.query.all()
    cart_item_count = session.get('cart_item_count', 0)
    return render_template('home.html', products=all_products, username=username, cart_item_count=cart_item_count)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    email_attempt = ''

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        email_attempt = email

        user_data = User.query.filter_by(email=email).first() # CORRECTED: 'User' (singular)

        # CORRECTED: Access password via .password attribute (not dictionary key)
        if user_data and user_data.password == password:

            login_user(user_data) 
            session['logged_in'] = True
            session['email'] = user_data.email
            session['username'] = user_data.name
            session['is_admin'] = user_data.is_admin

            next_page = session.pop('redirect_after_login', None)
            if next_page:
                return redirect(next_page)
            elif session['is_admin']:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('homepage'))
        else:
            error = 'Invalid Credentials. Please try again.'

    return render_template('login.html', error=error, email=email_attempt)

# ADDED: New route for user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        address = request.form.get('address', '') # Address is optional

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            error = 'Email already registered. Please login or use a different email.'
        else:
            new_user = User(email=email, password=password, name=name, address=address, is_admin=False)
            db.session.add(new_user)
            db.session.commit()

            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html', error=error)

@app.route('/logout')
def logout():
    logout_user()  
    session.pop('email', None)
    session.pop('username', None)
    session.pop('cart', None)
    session.pop('is_admin', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('homepage'))

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if not session.get('logged_in'):
        session['redirect_after_login'] = request.referrer or url_for('homepage')
        flash('Please login to add items to cart.', 'warning')
        return redirect(url_for('login'))

    product_id = request.form['product_id']
    try:
        quantity = int(request.form.get('quantity', 1))
        if quantity < 1:
            quantity = 1
    except ValueError:
        quantity = 1

    product = Product.query.get(product_id)

    if product:
        cart = session.get('cart', {})

        item_to_add = {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "unit": product.unit,
            "image": product.image,
            "quantity": quantity
        }

        if product_id in cart:
            cart[product_id]['quantity'] += quantity
        else:
            cart[product_id] = item_to_add

        session['cart'] = cart
        cart_item_count = sum(item['quantity'] for item in cart.values())
        session['cart_item_count'] = cart_item_count
        flash(f'{quantity} x {product.name} added to cart!', 'success')
    else:
        flash('Product not found!', 'danger')
    return redirect(url_for('homepage'))

@app.route('/cart')
def view_cart():
    if not session.get('logged_in'):
        session['redirect_after_login'] = url_for('view_cart')
        flash('Please login to view your cart.', 'warning')
        return redirect(url_for('login'))

    cart = session.get('cart', {})
    cart_items = list(cart.values())
    total_price = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

# ADDED: Route to update product quantity in the cart
@app.route('/update_cart_quantity', methods=['POST'])
def update_cart_quantity():
    if not session.get('logged_in'):
        flash('Please login to update your cart.', 'warning')
        return redirect(url_for('login'))

    product_id = request.form.get('product_id')
    action = request.form.get('action') # 'increase' or 'decrease'

    cart = session.get('cart', {})

    if product_id in cart:
        if action == 'increase':
            cart[product_id]['quantity'] += 1
        elif action == 'decrease':
            cart[product_id]['quantity'] -= 1

        # Ensure quantity doesn't go below 1
        if cart[product_id]['quantity'] < 1:
            del cart[product_id] # Remove item if quantity drops to 0 or less
            flash('Product removed from cart.', 'info')
        else:
            flash(f"Quantity for {cart[product_id]['name']} updated.", 'success')
    else:
        flash('Product not found in cart.', 'danger')

    session['cart'] = cart
    
    # Recalculate and update cart_item_count for the homepage badge
    cart_item_count = sum(item['quantity'] for item in cart.values())
    session['cart_item_count'] = cart_item_count

    return redirect(url_for('view_cart')) # Redirect back to the cart page

@app.route('/checkout')
def checkout():
    if not session.get('logged_in'):
        flash('Please login to update your cart.', 'warning')
        return redirect(url_for('login'))

    product_id = request.form.get('product_id')
    action = request.form.get('action') # 'increase' or 'decrease'

    cart = session.get('cart', {})

    if product_id in cart:
        if action == 'increase':
            cart[product_id]['quantity'] += 1
        elif action == 'decrease':
            cart[product_id]['quantity'] -= 1

        # Ensure quantity doesn't go below 1
        if cart[product_id]['quantity'] < 1:
            del cart[product_id] # Remove item if quantity drops to 0 or less
            flash('Product removed from cart.', 'info')
        else:
            flash(f"Quantity for {cart[product_id]['name']} updated.", 'success')
    else:
        flash('Product not found in cart.', 'danger')
    cart_items = list(cart.values())
    total_price = sum(item['price'] * item['quantity'] for item in cart_items)
    # CORRECTED: Fetch user address from database using User model (not 'users')
    user = User.query.filter_by(email=session.get('email')).first()
    user_address = user.address if user else 'No address found. Please update your profile.'

    session['cart'] = cart
    
    # Recalculate and update cart_item_count for the homepage badge
    cart_item_count = sum(item['quantity'] for item in cart.values())
    session['cart_item_count'] = cart_item_count

    return redirect(url_for('view_cart')) # Redirect back to the cart page

# Ensure current_user is imported if you're using Flask-Login
# Make sure 'from flask_login import login_required, current_user' is at the top of your file
from flask_login import login_required, current_user # This line needs to be at the top level of your imports, not inside other code.

@app.route('/checkout', methods=['GET']) # Corrected syntax: methods=['GET']
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty. Please add items before checking out.', 'info')
        return redirect(url_for('view_cart'))

    cart_items_list = list(cart.values())
    total_amount = sum(item['price'] * item['quantity'] for item in cart_items_list)
    user_address = current_user.address if current_user.address else 'No address found. Please update your profile.'

    # --- START OF NEW/MODIFIED LOGIC ---
    # Find an existing pending order for the current user, or create a new one.
    order = Order.query.filter_by(
        user_email=current_user.email,
        status='Pending'
    ).order_by(Order.date.desc()).first()

    if not order:
        # Create a new order if no pending one exists
        order = Order(
            user_email=current_user.email,
            total_amount=total_amount,
            delivery_address=user_address,
            payment_method='cod', # Default to COD on initial checkout view
            status="Pending"
        )
        db.session.add(order)
        db.session.flush() # Get ID before committing items (needed for order_item.order_id)

        for item_data in cart_items_list: # Iterate through cart items from session
            order_item = OrderItem(
                order_id=order.id,
                product_id=item_data['id'],
                product_name=item_data['name'],
                product_price_at_order=item_data['price'],
                quantity=item_data['quantity'],
                product_unit=item_data['unit']
            )
            db.session.add(order_item)
        db.session.commit()
        flash(f'New order initiated (ID: {order.id}).', 'info') # Optional: for debugging
    else:
        # If pending order exists, update its details (total, address) if necessary
        order.total_amount = total_amount
        order.delivery_address = user_address
        # IMPORTANT: If cart contents can change after initiating an order and user comes back to checkout,
        # you might need to delete existing order items and re-create them here based on the current cart.
        # For simplicity, we are not doing that now, assuming order items are fixed once an order is created.
        db.session.commit()
        flash(f'Resuming pending order (ID: {order.id}).', 'info') # Optional: for debugging

    # Ensure 'order.items' are populated correctly for the template
    # (either from the newly created order or the fetched one).
    # If the order was just created, order.items will already be there.
    # If fetched, order.items is lazy-loaded, so accessing it here is fine.
    # Use order.items for the order summary display in payment.html
    order_items_for_display = order.items if order else cart_items_list 
    # --- END OF NEW/MODIFIED LOGIC ---

    upi_form = UPIPaymentForm()

    return render_template('payment.html',
                           order=order, # <--- CRUCIAL: Pass the actual order object
                           cart_items=order_items_for_display, # Use items from the order object for display
                           total_price=order.total_amount, # Use total from the order object
                           user_address=order.delivery_address, # Use address from the order object
                           form=upi_form)
# app.py

# ... (keep all your existing imports and code above this)

@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    # Get the order_id from the hidden input in payment.html
    order_id = request.form.get('order_id')
    if not order_id:
        flash('Order ID missing from form. Please try checkout again.', 'danger')
        return redirect(url_for('checkout')) # Redirect to checkout to re-initiate if order_id is missing

    order = Order.query.get(order_id)

    # Validate the order: exists, belongs to user, is pending
    if not order or order.user_email != current_user.email or order.status != 'Pending':
        flash('Invalid or unauthorized order. Please start a new checkout.', 'danger')
        # Clear cart if this order is problematic, so they start fresh
        session.pop('cart', None)
        session.pop('cart_item_count', None)
        return redirect(url_for('checkout'))

    # Retrieve form data
    delivery_address = request.form.get('address', order.delivery_address) # Use form address or existing order address
    payment_method = request.form.get('payment_method') # Get selected payment method (cod or upi)
    # The 'upi_id' input is part of the form, but will be processed by initiate_upi_payment if UPI is chosen

    # Update order details (delivery address and selected payment method)
    order.delivery_address = delivery_address
    order.payment_method = payment_method # Save the chosen payment method

    # total_amount and order.items were already set when the order was created/updated in the /checkout GET request.
    # We do NOT create new Order or OrderItem objects here.

    db.session.commit() # Commit the updates to the existing order

    # IMPORTANT: Clear the cart ONLY after the order is processed/finalized
    # for payment, to prevent users from placing the same order multiple times
    # by going back.
    session.pop('cart', None)
    session.pop('cart_item_count', None)

    if payment_method == 'upi':
        flash(f'Order {order.id} proceeding to UPI payment.', 'info')
        # Redirect to a route that handles UPI initiation, passing the order ID
        # The form on payment.html for UPI will now submit to initiate_upi_payment
        # which needs the order_id to process the transaction.
        return redirect(url_for('checkout_payment', order_id=order.id)) # Re-render payment page for UPI form submission
    else: # This covers 'cod' and any other non-UPI methods
        order.status = "Confirmed (COD)" # Update status for COD orders
        db.session.commit() # Commit this status update
        flash(f'Order {order.id} placed successfully via Cash on Delivery!', 'success')
        return render_template('order_confirmation.html', order_id=order.id, username=current_user.name)
# ... (keep admin routes, init-db, my_orders, UPIPaymentForm as they are) ...

# --- ADMIN ROUTES ---

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard to show an overview and links to other admin functions."""
    total_products = Product.query.count()
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='Pending').count()
    return render_template('admin_dashboard.html',
                           total_products=total_products,
                           total_orders=total_orders,
                           pending_orders=pending_orders)

@app.route('/admin/products')
@admin_required
def admin_products():
    """Admin panel to view, add, edit, and remove products."""
    all_products = Product.query.all() # Fetch all products from db
    return render_template('admin_products.html', products=all_products) # CORRECTED: Pass all_products

@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    """Handles adding a new product."""
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        unit = request.form['unit']
        image = request.form.get('image', 'default_product.png')

        new_product = Product(name=name, price=price, unit=unit, image=image)
        db.session.add(new_product)
        db.session.commit()

        flash(f'Product "{name}" added successfully!', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin_add_product.html')

@app.route('/admin/products/edit/<product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    """Handles editing an existing product."""
    product = Product.query.get(product_id)
    if not product:
        flash('Product not found!', 'danger')
        return redirect(url_for('admin_products'))

    if request.method == 'POST':
        product.name = request.form['name'] # CORRECTED: Access via .name (not dictionary key)
        product.price = float(request.form['price']) # CORRECTED: Access via .price
        product.unit = request.form['unit'] # CORRECTED: Access via .unit
        product.image = request.form.get('image', product.image) # CORRECTED: Access via .image
        db.session.commit()

        flash(f'Product "{product.name}" updated successfully!', 'success') # CORRECTED: Access via .name
        return redirect(url_for('admin_products'))
    return render_template('admin_edit_product.html', product=product)

@app.route('/admin/products/delete/<product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    """Handles deleting a product."""
    product = Product.query.get(product_id)
    if product:
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully!', 'success')
    else:
        flash('Product not found or could not be deleted.', 'danger')
    return redirect(url_for('admin_products'))

@app.route('/admin/orders')
@admin_required
def admin_orders():
    """Admin panel to view all placed orders."""
    all_orders = Order.query.order_by(Order.date.desc()).all()
    return render_template('admin_orders.html', orders=all_orders)

@app.route('/admin/orders/<order_id>/update_status', methods=['POST'])
@admin_required
def update_order_status(order_id):
    """Updates the status of a specific order (e.g., to 'Delivered')."""
    order = Order.query.get(order_id) # CORRECTED: Fetch order by ID from DB (not 'next' on 'orders' list)
    if order:
        order.status = "Delivered" # CORRECTED: Update status attribute (not dictionary key)
        db.session.commit()
        flash(f'Order {order_id} marked as Delivered!', 'success')
    else:
        flash('Order not found!', 'danger')
    return redirect(url_for('admin_orders'))

# --- Flask CLI Commands (for database initialization) ---
@app.cli.command("init-db")
def init_db_command():
    """Clear existing data and create new tables."""
    with app.app_context():
        db.drop_all()
        db.create_all()

        if Product.query.count() == 0:
            print("Adding initial products...")
            initial_products = [
                Product(name="Fresh Tomatoes", price=45.00, unit="kg", image="tomato.png"),
                Product(name="Organic Spinach", price=30.00, unit="bunch", image="spinach.png"),
                Product(name="Farm Fresh Potatoes", price=25.00, unit="kg", image="potato.png"),
                Product(name="Green Chillies", price=10.00, unit="100g", image="chillies.png"),
                Product(name="Carrots", price=35.00, unit="kg", image="carrot.png"),
            ]
            db.session.add_all(initial_products)
            db.session.commit()
            print("Initial products added.")

        if User.query.count() == 0:
            print("Adding initial users...")
            initial_users = [
                User(email="customer@fresh.com", password="password123", name="Local Customer", address="H.No 1-2-3, Main Road, Aswapuram, Telangana 507123"),
                User(email="admin@fresh.com", password="admin123", name="Admin User", is_admin=True)
            ]
            db.session.add_all(initial_users)
            db.session.commit()
            print("Initial users added.")
    print("Initialized the database.")
    
# app.py

# ... (keep all your existing imports and code above this)

@app.route('/my_orders')
def my_orders():
    """
    Displays a list of all orders placed by the current logged-in customer.
    """
    if not session.get('logged_in'):
        flash('Please login to view your orders.', 'warning')
        session['redirect_after_login'] = url_for('my_orders')
        return redirect(url_for('login'))

    user_email = session.get('email')

    # Fetch all orders for the current user, ordered by most recent first
    # We use .options(db.joinedload(Order.items)) to eagerly load the order items
    # in the same query, which is more efficient.
    orders = Order.query.filter_by(user_email=user_email) \
                        .order_by(Order.date.desc()) \
                        .all()

    return render_template('customer_orders.html', orders=orders)

class UPIPaymentForm(FlaskForm):
    upi_id = StringField('UPI ID', validators=[DataRequired(), Length(min=5, max=256)])
    submit = SubmitField('Pay with UPI')

    def validate_upi_id(self, upi_id):
        upi_regex = r"^[a-zA-Z0-9.\-]{2,256}@[a-zA-Z]{2,64}$"
        if not re.match(upi_regex, upi_id.data):
            raise ValidationError('Invalid UPI ID format.')
        
   # Ensure current_user is imported if you're using Flask-Login
from flask_login import login_required, current_user # Add current_user import

@app.route('/checkout/payment/<order_id>', methods=['GET']) # Changed to GET, as place_order handles POST
@login_required
def checkout_payment(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_email != current_user.email:
        flash('You do not have permission to view this order.', 'danger')
        return redirect(url_for('my_orders'))
    upi_form = UPIPaymentForm()

    return render_template('payment.html', order=order, cart_items=order.items, total_price=order.total_amount, user_address=order.delivery_address, form=upi_form)   

@app.route('/initiate_upi_payment', methods=['POST'])
@login_required
def initiate_upi_payment():
    upi_form = UPIPaymentForm()

    # --- START OF NEW/MODIFIED LOGIC ---
    # Retrieve the order_id from the form (it must be passed as a hidden input)
    order_id = request.form.get('order_id')
    if not order_id:
        flash('Order ID missing for UPI payment initiation.', 'danger')
        return redirect(url_for('checkout')) # Redirect to checkout if order_id is missing

    order_to_pay = Order.query.get(order_id)

    # Basic validation for the order
    if not order_to_pay or order_to_pay.user_email != current_user.email or order_to_pay.status not in ['Pending', 'Initiated']:
        flash('Invalid or unauthorized order for UPI payment.', 'danger')
        return redirect(url_for('my_orders')) # Redirect if order is invalid or not pending/initiated
    # --- END OF NEW/MODIFIED LOGIC ---

    if not upi_form.validate_on_submit():
        # If validation fails, re-render the payment page with errors
        flash('Invalid UPI ID format. Please correct it.', 'danger')
        return render_template('payment.html',
                               order=order_to_pay, # Pass the order object back to the template
                               cart_items=order_to_pay.items, # Use items from order
                               total_price=order_to_pay.total_amount,
                               user_address=order_to_pay.delivery_address,
                               form=upi_form) # Pass the form with errors

    upi_id = upi_form.upi_id.data
    amount = order_to_pay.total_amount # Use amount from the order
    merchant_name = "Aswapuram Fresh"
    merchant_vpa = "9966270260@ybl"  # **VERY IMPORTANT: REPLACE WITH YOUR ACTUAL UPI ID**

    transaction_id = str(uuid4())

    try:
        # Create a transaction record
        new_transaction = Transaction(
            order_id=order_to_pay.id,
            amount=amount,
            payment_method='UPI',
            transaction_id=transaction_id,
            status='Initiated'
        )
        db.session.add(new_transaction)

        # Update the order status and payment method
        order_to_pay.status = 'Initiated'
        order_to_pay.payment_method = 'upi'
        
        db.session.commit()

        # Construct UPI Intent URL
        upi_intent_url = (
            f"upi://pay?"
            f"pa={quote_plus(merchant_vpa)}&"
            f"pn={quote_plus(merchant_name)}&"
            f"mc=5411&"
            f"tid={quote_plus(transaction_id)}&"
            f"tr={quote_plus(transaction_id)}&"
            f"am={quote_plus(str(amount))}&"
            f"cu=INR&"
            f"tn={quote_plus(f'Payment for Order #{order_to_pay.id} from Aswapuram Fresh')}"
        )
        print("Generated UPI Intent URL:", upi_intent_url)
        logging.info(f"Initiated UPI payment for Order ID: {order_to_pay.id}, Transaction ID: {transaction_id}, Amount: {amount}")
        logging.debug(f"UPI Intent URL: {upi_intent_url}")
        flash('Redirecting to UPI app for payment. Please complete the transaction.', 'info')
        return redirect(upi_intent_url)

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error initiating UPI payment for Order ID {order_to_pay.id}: {e}", exc_info=True) # Added more robust error logging
        flash(f'Error processing UPI payment: {e}', 'danger')
        return redirect(url_for('checkout_payment', order_id=order_to_pay.id)) # Redirect back to payment with error

# ... (keep all your existing routes and code below this)

# ... (keep all your existing routes and code below this)

# --- To run the Flask app ---
if __name__ == '__main__':
    app.run(debug=True)
    