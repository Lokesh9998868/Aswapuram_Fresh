from flask import Flask, render_template, request, redirect, url_for, session, flash
import uuid # For generating unique IDs for products and orders
from datetime import datetime # to get current date for orders

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'lokesh123'

# --- In-memory Data Storage (for demonstration purposes) ---
# In a real application, this data would be stored in a persistent database

# Mock product data
products = [
    {"id": str(uuid.uuid4()), "name": "Fresh Tomatoes", "price": 45.00, "unit": "kg", "image": "tomato.png"},
    {"id": str(uuid.uuid4()), "name": "Organic Spinach", "price": 30.00, "unit": "bunch", "image": "spinach.png"},
    {"id": str(uuid.uuid4()), "name": "Farm Fresh Potatoes", "price": 25.00, "unit": "kg", "image": "potato.png"},
    {"id": str(uuid.uuid4()), "name": "Green Chillies", "price": 10.00, "unit": "100g", "image": "chillies.png"},
    {"id": str(uuid.uuid4()), "name": "Carrots", "price": 35.00, "unit": "kg", "image": "carrot.png"},
]

# Mock user data
users = {
    "customer@fresh.com": {"password": "password123", "name": "Local Customer", "address": "H.No 1-2-3, Main Road, Aswapuram, Telangana 507123"},
    "admin@fresh.com": {"password": "admin123", "name": "Admin User", "is_admin": True}
}

# Order data (to store placed orders)
orders = []

# --- Helper Functions (for admin access control) ---
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or not session.get('is_admin'):
            flash('Admin access required.', 'danger') # Use flash for messages
            session['redirect_after_login'] = request.url # Store the URL trying to access
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes and Views ---

@app.route('/')
def homepage():
    username = session.get('username')
    return render_template('home.html', products=products, username=username)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    email_attempt = ''

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        email_attempt = email

        user_data = users.get(email)

        if user_data and user_data['password'] == password:
            session['logged_in'] = True
            session['email'] = email
            session['username'] = user_data['name']
            session['is_admin'] = user_data.get('is_admin', False)

            next_page = session.pop('redirect_after_login', None)
            if next_page:
                return redirect(next_page)
            elif session['is_admin']:
                return redirect(url_for('admin_dashboard')) # Redirect admin to dashboard
            else:
                return redirect(url_for('homepage'))
        else:
            error = 'Invalid Credentials. Please try again.'

    return render_template('login.html', error=error, email=email_attempt)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('email', None)
    session.pop('username', None)
    session.pop('cart', None)
    session.pop('is_admin', None)
    flash('You have been logged out.', 'info') # Add flash message
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

    product = next((p for p in products if p["id"] == product_id), None)

    if product:
        cart = session.get('cart', {})

        item_to_add = {
            "id": product["id"],
            "name": product["name"],
            "price": product["price"],
            "unit": product.get("unit", "N/A"),
            "image": product.get("image", ""),
            "quantity": quantity
        }

        if product_id in cart:
            cart[product_id]['quantity'] += quantity
        else:
            cart[product_id] = item_to_add

        session['cart'] = cart
        flash(f'{quantity} x {product["name"]} added to cart!', 'success')
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
    user_address = users.get(session.get('email'), {}).get('address', '')

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

    order_id = str(uuid.uuid4())
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_order = {
        "id": order_id,
        "user_email": session.get('email'),
        "user_name": session.get('username'),
        "items": cart_items_list,
        "total_amount": total_amount,
        "delivery_address": delivery_address,
        "payment_method": payment_method,
        "date": current_date,
        "status": "Pending"
    }
    orders.append(new_order)

    session.pop('cart', None)
    flash(f'Order {order_id} placed successfully!', 'success')
    return render_template('order_confirmation.html', order_id=order_id, username=session.get('username'))

# --- NEW ADMIN ROUTES ---

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard to show an overview and links to other admin functions."""
    total_products = len(products)
    total_orders = len(orders)
    pending_orders = len([o for o in orders if o['status'] == 'Pending'])
    # In a real app, you'd fetch from DB and do more complex aggregations
    return render_template('admin_dashboard.html',
                           total_products=total_products,
                           total_orders=total_orders,
                           pending_orders=pending_orders)

@app.route('/admin/products')
@admin_required
def admin_products():
    """Admin panel to view, add, edit, and remove products."""
    return render_template('admin_products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    """Handles adding a new product."""
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        unit = request.form['unit']
        # For simplicity, image is hardcoded or could be a basic text input for filename
        image = request.form.get('image', 'default_product.png') # Optional image field

        new_product = {
            "id": str(uuid.uuid4()),
            "name": name,
            "price": price,
            "unit": unit,
            "image": image
        }
        products.append(new_product)
        flash(f'Product "{name}" added successfully!', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin_add_product.html')

@app.route('/admin/products/edit/<product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    """Handles editing an existing product."""
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        flash('Product not found!', 'danger')
        return redirect(url_for('admin_products'))

    if request.method == 'POST':
        product['name'] = request.form['name']
        product['price'] = float(request.form['price'])
        product['unit'] = request.form['unit']
        product['image'] = request.form.get('image', product.get('image', 'default_product.png')) # Update or keep existing
        flash(f'Product "{product["name"]}" updated successfully!', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin_edit_product.html', product=product)

@app.route('/admin/products/delete/<product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    """Handles deleting a product."""
    global products # Need to declare global to modify the list directly
    original_len = len(products)
    products = [p for p in products if p["id"] != product_id]
    if len(products) < original_len:
        flash('Product deleted successfully!', 'success')
    else:
        flash('Product not found or could not be deleted.', 'danger')
    return redirect(url_for('admin_products'))

@app.route('/admin/orders')
@admin_required # Use the decorator here as well
def admin_orders():
    """Admin panel to view all placed orders."""
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/orders/<order_id>/update_status', methods=['POST'])
@admin_required # Use the decorator here as well
def update_order_status(order_id):
    """Updates the status of a specific order (e.g., to 'Delivered')."""
    order = next((o for o in orders if o["id"] == order_id), None)
    if order:
        order["status"] = "Delivered"
        flash(f'Order {order_id} marked as Delivered!', 'success')
    else:
        flash('Order not found!', 'danger')
    return redirect(url_for('admin_orders'))

# To run this Flask app:
# export FLASK_APP=app.py
# flask run

if __name__ == '__main__':
    app.run(debug=True) # Run in debug mode for development