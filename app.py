from flask import Flask, render_template, request, redirect, url_for, session
import uuid # For generating unique IDs for products and orders
from datetime import datetime # to get current date for orders

# Initialize Flask app
app = Flask(__name__)
# A secret key is required for sessions in Flask (used for managing user login status).
# In a real app, this should be a strong, randomly generated key stored securely (e.g., environment variable).
app.secret_key = 'lokesh123'

# --- In-memory Data Storage (for demonstration purposes) ---
# In a real application, this data would be stored in a persistent database
# like PostgreSQL, MySQL, SQLite, etc.

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

#Order data (to store placed orders)
orders = []

# --- Routes and Views ---

@app.route('/')
def homepage():
    """
    Render the homepage displaying available products.
    Check if the user is logged in to display their name and relevant links
    """
    username = session.get('username')
    return render_template('home.html', products=products, username=username)

# ... (rest of your app.py imports and initializations) ...

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user login.
    GET request: Displays the login form.
    POST request: Authenticates user based on email and password.
    If successful, sets session variables and redirects.
    If failed, displays an error message on the same page.
    """
    error = None
    email_attempt = '' # Initialize email_attempt here so it's always defined

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        email_attempt = email # This line now re-assigns it for POST requests

        user_data = users.get(email)

        if user_data and user_data['password'] == password:
            session['logged_in'] = True
            session['email'] = email
            session['username'] = user_data['name']
            session['is_admin'] = user_data.get('is_admin', False)

            # Check if there's a page to redirect to after successful login
            next_page = session.pop('redirect_after_login', None)
            if next_page:
                return redirect(next_page)
            elif session['is_admin']:
                return redirect(url_for('admin_orders'))
            else:
                return redirect(url_for('homepage'))
        else:
            error = 'Invalid Credentials. Please try again.'

    # Render the login page, passing the error message (if any) and the attempted email
    return render_template('login.html', error=error, email=email_attempt)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handles user registration, saving new users to the database.
    """
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        address = request.form.get('address', '')
        is_admin = request.form.get('is_admin') == 'on' # Checkbox value from form

        if User.query.filter_by(email=email).first():
            return "Email already registered", 409 # Conflict

        # IMPORTANT: Hash the password before saving in a real application!
        new_user = User(email=email, password=password, name=name, address=address, is_admin=is_admin)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

# ... (rest of your app.py routes and code) ...
@app.route('/logout')
def logout():
    """
    Handle user logout.
    Clears the session and redirects to the homepage.
    """
    session.pop('logged_in', None)
    session.pop('email', None)
    session.pop('username', None)
    session.pop('cart', None)
    session.pop('is_admin', None)
    return redirect(url_for('homepage'))

# ... (rest of your app.py imports and initializations) ...

# ... (rest of your app.py imports and initializations) ...

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    """
    Adds a product to the user's shopping cart with a specified quantity.
    Uses Flask's session to store cart items.
    """
    if not session.get('logged_in'):
        session['redirect_after_login'] = request.referrer or url_for('homepage')
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
        
        # Ensure the item structure is consistent for storage in cart
        item_to_add = {
            "id": product["id"],
            "name": product["name"],
            "price": product["price"],
            "unit": product.get("unit", "N/A"), # Safely get unit, default to "N/A"
            "image": product.get("image", ""), # Safely get image, default to empty string
            "quantity": quantity
        }

        if product_id in cart:
            cart[product_id]['quantity'] += quantity
        else:
            cart[product_id] = item_to_add # Use the consistently structured item
            
        session['cart'] = cart
    return redirect(url_for('homepage'))

# ... (rest of your app.py routes and code) .....

@app.route('/cart')
def view_cart():
    """
    Displays the contents of the user's shopping cart.
    Calculates the total price of items in the cart.
    """
    if not session.get('logged_in'):
        session['redirect_after_login'] = url_for('view_cart')
        return redirect(url_for('login'))

    cart = session.get('cart', {})
    cart_items = list(cart.values()) # Convert dictionary values to a list for iteration in template
    total_price = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

@app.route('/checkout')
def checkout():
    """
    Displays the checkout page, showing order summary and payment options.
    For this MVP, only Cash on Delivery (COD) is available.
    """
    if not session.get('logged_in'):
        session['redirect_after_login'] = url_for('checkout')
        return redirect(url_for('login'))

    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('view_cart')) # Redirect to cart if empty

    cart_items = list(cart.values())
    total_price = sum(item['price'] * item['quantity'] for item in cart_items)
    # Get user's default address or provide a placeholder
    user_address = users.get(session.get('email'), {}).get('address', '')

    return render_template('payment.html', cart_items=cart_items, total_price=total_price, user_address=user_address)

@app.route('/place_order', methods=['POST'])
def place_order():
    """
    Processes the order after checkout.
    Creates a new order record and clears the user's cart.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('view_cart')) # Cannot place an empty order

    delivery_address = request.form.get('address', '')
    payment_method = request.form.get('payment_method', 'cod') # Default to COD

    cart_items_list = list(cart.values())
    total_amount = sum(item['price'] * item['quantity'] for item in cart_items_list)

    order_id = str(uuid.uuid4())
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Format current date/time

    new_order = {
        "id": order_id,
        "user_email": session.get('email'),
        "user_name": session.get('username'),
        "items": cart_items_list,
        "total_amount": total_amount,
        "delivery_address": delivery_address,
        "payment_method": payment_method,
        "date": current_date,
        "status": "Pending" # Initial status
    }
    orders.append(new_order) # Add to our in-memory orders list

    session.pop('cart', None) # Clear the cart after placing the order

    return render_template('order_confirmation.html', order_id=order_id, username=session.get('username'))

@app.route('/admin/orders')
def admin_orders():
    """
    Admin panel to view all placed orders.
    Requires admin login.
    """
    if not session.get('logged_in') or not session.get('is_admin'):
        # If not logged in as admin, redirect to login page
        session['redirect_after_login'] = url_for('admin_orders')
        return redirect(url_for('login'))
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/orders/<order_id>/update_status', methods=['POST'])
def update_order_status(order_id):
    """
    Updates the status of a specific order (e.g., to 'Delivered').
    Admin function.
    """
    if not session.get('logged_in') or not session.get('is_admin'):
        return "Unauthorized Access. Please login as admin.", 403 # HTTP 403 Forbidden

    order = next((o for o in orders if o["id"] == order_id), None)
    if order:
        order["status"] = "Delivered" # Simple status update
    return redirect(url_for('admin_orders'))


# To run this Flask app, make sure your virtual environment is activated in your terminal.
# Then, set the FLASK_APP environment variable and run Flask:
# export FLASK_APP=app.py # For macOS/Linux
# flask run
