from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = 'happy_secret_key'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'happybites.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    orders = db.relationship('Order', backref='user', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_address = db.Column(db.Text, nullable=True) # Added address field
    total = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    items = db.relationship('OrderItem', backref='order', lazy=True)

class StoreSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.Text, nullable=False, default='123 Bakery Street, Food Town, FL 32000')
    phone = db.Column(db.String(20), nullable=False, default='+1 (555) 123-4567')
    email = db.Column(db.String(120), nullable=False, default='hello@happybites.com')
    instagram = db.Column(db.String(255), nullable=True)
    facebook = db.Column(db.String(255), nullable=True)
    twitter = db.Column(db.String(255), nullable=True)
    whatsapp = db.Column(db.String(20), nullable=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=1)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    message = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False) # bakery, snacks, fresh
    image_url = db.Column(db.String(255), nullable=True)
    initial_stock = db.Column(db.Integer, default=50)
    remaining_stock = db.Column(db.Integer, default=50)

admin_credentials = {
    'username': 'admin',
    'password': 'admin123'
}

def seed_products():
    if StoreSettings.query.count() == 0:
        settings = StoreSettings()
        db.session.add(settings)
        db.session.commit()

    if Product.query.count() == 0:
        default_products = [
            {'name': 'Crispy Samosa', 'price': 15.00, 'category': 'snacks', 'image_url': 'static/assets/images/SAMOSA.jpg', 'stock': 20},
            {'name': 'Butter Cookies', 'price': 45.00, 'category': 'bakery', 'image_url': 'static/assets/images/cookies.jpg', 'stock': 15},
            {'name': 'Fresh Fruit Salad', 'price': 60.00, 'category': 'fresh', 'image_url': 'static/assets/images/fruit.avif', 'stock': 10},
            {'name': 'Hot Bhajji', 'price': 20.00, 'category': 'snacks', 'image_url': 'static/assets/images/BHAJJI.jpg', 'stock': 5},
            {'name': 'Unnakaya', 'price': 35.00, 'category': 'bakery', 'image_url': 'static/assets/images/UNNAKAYA.jpg', 'stock': 8},
            {'name': 'Garden Salad', 'price': 70.00, 'category': 'bakery', 'image_url': 'static/assets/images/salad.webp', 'stock': 4}
        ]
        for p in default_products:
            new_p = Product(name=p['name'], price=p['price'], category=p['category'], 
                            image_url=p['image_url'], initial_stock=p['stock'], remaining_stock=p['stock'])
            db.session.add(new_p)
        db.session.commit()
    else:
        # Migration: If prices look like they are in dollars (e.g. < 10), scale them to Rs.
        products = Product.query.all()
        for p in products:
            if p.price < 10:
                p.price = p.price * 10
        db.session.commit()

with app.app_context():
    db.create_all()
    seed_products()

@app.context_processor
def inject_settings():
    settings = StoreSettings.query.first()
    if not settings:
        settings = StoreSettings()
        db.session.add(settings)
        db.session.commit()
    return dict(store_settings=settings)

@app.route('/')
def home():
    featured_products = Product.query.limit(4).all()
    # Fetch top 5 recent feedbacks for landing page
    recent_feedbacks = Feedback.query.order_by(Feedback.timestamp.desc()).limit(5).all()
    return render_template('index.html', products=featured_products, testimonials=recent_feedbacks)

@app.route('/feedbacks')
def all_feedbacks():
    feedbacks = Feedback.query.order_by(Feedback.timestamp.desc()).all()
    return render_template('feedbacks.html', feedbacks=feedbacks)

@app.route('/menu')
def menu_page():
    all_products = Product.query.all()
    return render_template('menu.html', products=all_products)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == admin_credentials['username'] and password == admin_credentials['password']:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error="Invalid credentials")
    return render_template('admin_login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        if User.query.filter_by(username=username).first():
            return render_template('signup.html', error="Username already exists")
        if User.query.filter_by(email=email).first():
            return render_template('signup.html', error="Email already exists")
            
        new_user = User(
            username=username,
            password=password,
            email=email,
            full_name=full_name,
            phone=phone,
            address=address
        )
        db.session.add(new_user)
        db.session.commit()
        
        session['user_logged_in'] = True
        session['username'] = username
        session['full_name'] = full_name
        session['phone'] = phone
        return redirect(url_for('home'))
        
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session['user_logged_in'] = True
            session['username'] = username
            session['full_name'] = user.full_name
            session['phone'] = user.phone
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error="Invalid username or password")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_logged_in', None)
    session.pop('username', None)
    session.pop('full_name', None)
    return redirect(url_for('home'))

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Get orders from database
    db_orders = Order.query.order_by(Order.timestamp.desc()).all()
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='Pending').count()
    processing_orders = Order.query.filter_by(status='Processing').count()
    completed_orders = Order.query.filter_by(status='Completed').count()
    cancelled_orders = Order.query.filter_by(status='Cancelled').count()
    
    # Daily Analytics (Today's Stats)
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    today_orders = Order.query.filter(db.func.date(Order.timestamp) == today_str).all()
    
    today_revenue = 0.0
    daily_items_sold = {}
    
    for o in today_orders:
        # Calculate revenue (exclude cancelled)
        if o.status != 'Cancelled':
            total_str = str(o.total).replace('Rs.', '').replace('$', '')
            try:
                today_revenue += float(total_str)
            except ValueError:
                pass
            
            # Aggregate items sold today
            for item in o.items:
                qty = getattr(item, 'quantity', 1) or 1
                daily_items_sold[item.name] = daily_items_sold.get(item.name, 0) + qty

    # Sort daily items by quantity
    top_selling_today = sorted(daily_items_sold.items(), key=lambda x: x[1], reverse=True)
    
    # Format for template
    formatted_orders = []
    for o in db_orders:
        formatted_orders.append({
            'id': o.id,
            'timestamp': o.timestamp.strftime("%Y-%m-%d %H:%M:%S") if o.timestamp else "N/A",
            'items': [{'name': i.name, 'price': i.price, 'qty': getattr(i, 'quantity', 1)} for i in o.items],
            'total': o.total,
            'status': o.status
        })

    # Get feedback from database
    db_feedbacks = Feedback.query.order_by(Feedback.timestamp.desc()).all()

    return render_template('admin_dashboard.html', 
                         orders=formatted_orders, 
                         username=session.get('admin_username', 'admin'),
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         processing_orders=processing_orders,
                         completed_orders=completed_orders,
                         cancelled_orders=cancelled_orders,
                         revenue=f"Rs.{today_revenue:.2f}",
                         top_selling_today=top_selling_today,
                         feedbacks=db_feedbacks)

@app.route('/admin/order/update-status', methods=['POST'])
def update_order_status():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
    order_id = request.form.get('order_id')
    new_status = request.form.get('status')
    
    order = Order.query.get(order_id)
    if order:
        order.status = new_status
        db.session.commit()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
    error = None
    success = None
    settings = StoreSettings.query.first()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_credentials':
            current_user = request.form.get('current_username')
            current_pass = request.form.get('current_password')
            new_user = request.form.get('new_username')
            new_pass = request.form.get('new_password')
            
            if (current_user == admin_credentials['username'] and 
                current_pass == admin_credentials['password']):
                
                if new_user and new_pass:
                    admin_credentials['username'] = new_user
                    admin_credentials['password'] = new_pass
                    session['admin_username'] = new_user
                    success = "Credentials updated successfully!"
                else:
                    error = "New username and password cannot be empty."
            else:
                error = "Current credentials invalid."
        
        elif action == 'update_store_info':
            new_address = request.form.get('address')
            new_phone = request.form.get('phone')
            new_email = request.form.get('email')
            new_insta = request.form.get('instagram')
            new_fb = request.form.get('facebook')
            new_twitter = request.form.get('twitter')
            new_whatsapp = request.form.get('whatsapp')
            
            if settings:
                settings.address = new_address
                settings.phone = new_phone
                settings.email = new_email
                settings.instagram = new_insta
                settings.facebook = new_fb
                settings.twitter = new_twitter
                settings.whatsapp = new_whatsapp
                db.session.commit()
                success = "Store information updated successfully!"
            else:
                error = "Store settings not found."
            
    return render_template('admin_settings.html', 
                         username=session.get('admin_username', 'admin'),
                         error=error,
                         success=success,
                         store_settings=settings)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('admin_login'))

@app.route('/api/contact', methods=['POST'])
def contact():
    data = request.get_json()
    # Simulate saving data or sending email
    print(f"Contact received from {data.get('email')}: {data.get('message')}")
    return jsonify({"status": "success", "message": "Message sent successfully!"})

@app.route('/api/order', methods=['POST'])
def order():
    if not session.get('user_logged_in'):
        return jsonify({"status": "error", "message": "Please login to place an order"}), 401
        
    data = request.get_json()
    items = data.get('items')
    total = data.get('total')
    customer_data = data.get('customer', {})
    
    # Get user details from session/db
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    new_order = Order(
        customer_name=user.full_name,
        customer_phone=user.phone,
        customer_address=customer_data.get('address', user.address), # Use provided address or profile default
        total=total or "Rs.0.00",
        user_id=user.id
    )
    db.session.add(new_order)
    db.session.flush() # Get the order ID

    if items:
        for item in items:
            qty = int(item.get('qty', 1))
            # Update Stock
            prod = Product.query.filter_by(name=item['name']).first()
            if prod:
                if prod.remaining_stock >= qty:
                    prod.remaining_stock -= qty
                else:
                    qty_available = prod.remaining_stock
                    prod.remaining_stock = 0
                    print(f"WARNING: {prod.name} only had {qty_available} left!")
            
            # Extract price safely
            item_price = 0.0
            try:
                price_str = str(item.get('price', '0')).replace('Rs.', '').replace('$', '').replace(',', '').strip()
                item_price = float(price_str)
            except (ValueError, TypeError):
                pass

            order_item = OrderItem(
                order_id=new_order.id,
                name=item['name'],
                price=item_price,
                quantity=qty
            )
            db.session.add(order_item)
    
    db.session.commit()
    return jsonify({"status": "success", "message": "Order placed successfully!"})

@app.route('/admin/reports')
def admin_reports():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin_reports.html', username=session.get('admin_username', 'admin'))

@app.route('/admin/users')
def admin_users():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Get all registered users from DB
    registered_users = User.query.all()
    user_list = []
    
    for u in registered_users:
        # Count orders for this user
        count = Order.query.filter_by(user_id=u.id).count()
        last_order = Order.query.filter_by(user_id=u.id).order_by(Order.timestamp.desc()).first()
        last_active = last_order.timestamp.strftime("%Y-%m-%d %H:%M:%S") if last_order else "N/A"
        
        user_list.append({
            'id': u.id,
            'name': u.full_name,
            'phone': u.phone,
            'email': u.email,
            'address': u.address,
            'orders_count': count,
            'last_order': last_active
        })
            
    return render_template('admin_users.html', users=user_list, username=session.get('admin_username', 'admin'))

@app.route('/admin/user/<int:user_id>/history')
def admin_user_history(user_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        user = User.query.get_or_404(user_id)
        # Get user's orders with items
        user_orders = Order.query.filter_by(user_id=user.id).order_by(Order.timestamp.desc()).all()
        
        formatted_orders = []
        for o in user_orders:
            # Map items and handle potential missing quantity
            items_list = []
            for i in o.items:
                items_list.append({
                    'name': i.name or "Unknown Item",
                    'price': i.price or 0.0,
                    'qty': int(getattr(i, 'quantity', 1) or 1)
                })
            
            formatted_orders.append({
                'id': o.id,
                'timestamp': o.timestamp.strftime("%Y-%m-%d %H:%M:%S") if o.timestamp else "N/A",
                'items': items_list,
                'total': o.total or "Rs.0.00",
                'status': o.status or "Pending"
            })
            
        print(f"DEBUG: Found {len(formatted_orders)} orders for user {user.full_name}")
        return render_template('admin_user_history.html', 
                             user=user, 
                             orders=formatted_orders,
                             username=session.get('admin_username', 'admin'))
    except Exception as e:
        print(f"ERROR in admin_user_history: {e}")
        return f"Error loading user history: {e}", 500

@app.route('/admin/products', methods=['GET', 'POST'])
def admin_products():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            new_p = Product(
                name=request.form.get('name'),
                price=float(request.form.get('price')),
                category=request.form.get('category'),
                image_url=request.form.get('image_url'),
                initial_stock=int(request.form.get('stock')),
                remaining_stock=int(request.form.get('stock'))
            )
            db.session.add(new_p)
        
        elif action == 'edit':
            p_id = request.form.get('product_id')
            prod = Product.query.get(p_id)
            if prod:
                prod.name = request.form.get('name')
                prod.price = float(request.form.get('price'))
                prod.category = request.form.get('category')
                prod.remaining_stock = int(request.form.get('stock'))
        
        elif action == 'delete':
            p_id = request.form.get('product_id')
            prod = Product.query.get(p_id)
            if prod:
                db.session.delete(prod)
        
        db.session.commit()
        return redirect(url_for('admin_products'))

    all_products = Product.query.all()
    print(f"DEBUG: Found {len(all_products)} products to render")
    return render_template('admin_products.html', products=all_products, username=session.get('admin_username', 'admin'))

@app.route('/admin/api/stats')
def admin_stats():
    if not session.get('admin_logged_in'):
        return jsonify({})
    
    # Calculate product sales from DB
    product_sales = {}
    all_order_items = OrderItem.query.all()
    for item in all_order_items:
        product_sales[item.name] = product_sales.get(item.name, 0) + 1
            
    # Also get stock info for inventory report
    all_products = Product.query.all()
    stock_labels = [p.name for p in all_products]
    stock_data = [p.remaining_stock for p in all_products]

    return jsonify({
        'labels': list(product_sales.keys()),
        'data': list(product_sales.values()),
        'stock_labels': stock_labels,
        'stock_data': stock_data
    })
    
@app.route('/admin/export/orders')
def export_orders():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Generate CSV from DB
    output = "Order ID,Date,Customer Name,Phone,Items,Total,Status\n"
    db_orders = Order.query.all()
    for o in db_orders:
        items_str = "|".join([i.name for i in o.items])
        output += f"{o.id},{o.timestamp.strftime('%Y-%m-%d %H:%M:%S')},{o.customer_name},{o.customer_phone},{items_str},{o.total},{o.status}\n"
        
    from flask import Response
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=orders_report.csv"}
    )

@app.route('/api/feedback', methods=['POST'])
def feedback():
    data = request.get_json()
    rating = data.get('rating')
    message = data.get('message')
    
    new_feedback = Feedback(rating=rating, message=message)
    db.session.add(new_feedback)
    db.session.commit()
    
    print(f"Feedback Received - Rating: {rating} stars, Message: {message}")
    return jsonify({"status": "success", "message": "Feedback received!"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
