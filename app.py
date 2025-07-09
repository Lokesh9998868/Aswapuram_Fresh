from flask import Flask, render_template, request, redirect, url_for, session, flash
import uuid # For generating unique IDs for products and orders
from flask_sqlalchemy import SQLAlchemy # Corrected: SQLAlchemy (no extra 'A')
from datetime import datetime # to get current date for orders
from functools import wraps # For creating decorators

# Initialize Flask app
app = Flask(__name__)

# --- Database Configuration for PostgreSQL ---
# IMPORTANT: Replace 'lokesh9' with your actual password if it's different
# Make sure your PostgreSQL server is running and the database 'aswapuram_fresh_db' exists
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://flaskuser:lokesh9@localhost:5432/aswapuram_fresh_db' # Corrected: Removed misleading MySQL comment
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'lokesh123'

# Initialize the database
db = SQLAlchemy(app)

# --- Database Models ---
class User(db.Model):
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
    session.pop('logged_in', None)
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
        session['redirect_after_login'] = url_for('checkout')
        flash('Please login to checkout.', 'warning')
        return redirect(url_for('login'))

    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty. Please add items before checking out.', 'info')
        return redirect(url_for('view_cart'))

    cart_items = list(cart.values())
    total_price = sum(item['price'] * item['quantity'] for item in cart_items)
    # CORRECTED: Fetch user address from database using User model (not 'users')
    user = User.query.filter_by(email=session.get('email')).first()
    user_address = user.address if user else 'No address found. Please update your profile.'

    return render_template('payment.html', cart_items=cart_items, total_price=total_price, user_address=user_address)

@app.route('/place_order', methods=['POST'])
def place_order():
    if not session.get('logged_in'):
        flash('You must be logged in to place an order.', 'danger')
        return redirect(url_for('login'))

    cart = session.get('cart', {})
    if not cart:
        flash('Cannot place an empty order. Please add items to your cart.', 'info')
        return redirect(url_for('view_cart'))

    delivery_address = request.form.get('address', '')
    payment_method = request.form.get('payment_method', 'cod')

    cart_items_list = list(cart.values())
    total_amount = sum(item['price'] * item['quantity'] for item in cart_items_list)

    current_user_email = session.get('email')
    user = User.query.filter_by(email=current_user_email).first()

    if not user:
        flash('User not found. Please re-login.', 'danger')
        session.pop('logged_in', None)
        return redirect(url_for('login'))

    new_order = Order(
        user_email=user.email,
        total_amount=total_amount,
        delivery_address=delivery_address,
        payment_method=payment_method,
        status="Pending"
    )
    db.session.add(new_order)
    db.session.flush()

    for item in cart_items_list:
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=item['id'],
            product_name=item['name'],
            product_price_at_order=item['price'],
            quantity=item['quantity'],
            product_unit=item['unit']
        )
        db.session.add(order_item)

    db.session.commit()

    session.pop('cart', None)
    session.pop('cart_item_count', None)
    flash(f'Order {new_order.id} placed successfully!', 'success')
    return render_template('order_confirmation.html', order_id=new_order.id, username=session.get('username'))

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

# --- To run the Flask app ---
if __name__ == '__main__':
    app.run(debug=True)