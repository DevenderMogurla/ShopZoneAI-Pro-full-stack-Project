
import os, uuid
from datetime import datetime
from decimal import Decimal
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parent
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-only-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f"sqlite:///{ROOT / 'shopzone.db'}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = str(ROOT / 'static' / 'uploads')
ALLOWED = {'png','jpg','jpeg','webp','gif'}
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(90), nullable=False)
    email = db.Column(db.String(140), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(25))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(15), default='user', nullable=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    category = db.Column(db.String(70), nullable=False, default='General')
    description = db.Column(db.Text, nullable=False, default='')
    price = db.Column(db.Numeric(12,2), nullable=False, default=0)
    compare_price = db.Column(db.Numeric(12,2), default=0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    image = db.Column(db.String(255), default='')
    active = db.Column(db.Boolean, default=True)
    featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    product = db.relationship('Product')
    __table_args__ = (db.UniqueConstraint('user_id','product_id', name='uq_cart_user_product'),)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(25), default='Placed')
    payment_method = db.Column(db.String(30), default='Razorpay (Test)')
    payment_status = db.Column(db.String(25), default='Pending')
    payment_id = db.Column(db.String(100), default='')
    subtotal = db.Column(db.Numeric(12,2), default=0)
    shipping = db.Column(db.Numeric(12,2), default=0)
    total = db.Column(db.Numeric(12,2), default=0)
    address = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    customer = db.relationship('User')
    items = db.relationship('OrderItem', cascade='all, delete-orphan', backref='order')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product_name = db.Column(db.String(140), nullable=False)
    price = db.Column(db.Numeric(12,2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(255), default='')

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor = db.Column(db.String(140), default='System')
    action = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def current_user():
    uid = session.get('user_id')
    return db.session.get(User, uid) if uid else None

@app.context_processor
def inject_globals():
    u = current_user()
    count = CartItem.query.filter_by(user_id=u.id).count() if u and u.role == 'user' else 0
    return {'current_user':u, 'cart_count':count, 'currency':os.getenv('CURRENCY','INR')}

def login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            u=current_user()
            if not u or not u.active:
                session.clear(); flash('Please sign in to continue.','warning')
                return redirect(url_for('login', next=request.path))
            if role and u.role != role: abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return deco
user_required = login_required('user')
admin_required = login_required('admin')

def money(v): return Decimal(str(v or 0))
def cart_data(uid):
    rows=CartItem.query.filter_by(user_id=uid).all()
    subtotal=sum((money(x.product.price)*x.quantity for x in rows), Decimal('0.00'))
    shipping=Decimal('0.00') if subtotal >= 999 or subtotal == 0 else Decimal('49.00')
    return rows, subtotal, shipping, subtotal+shipping

def log(action):
    db.session.add(Activity(actor=current_user().name if current_user() else 'System', action=action))

def seed():
    db.create_all()
    email=os.getenv('ADMIN_EMAIL','admin@shopzone.local').lower()
    admin=User.query.filter_by(email=email).first()
    if not admin:
        db.session.add(User(name=os.getenv('ADMIN_NAME','ShopZone Admin'),email=email,
            password_hash=generate_password_hash(os.getenv('ADMIN_PASSWORD','Admin@123')),role='admin'))
    if Product.query.count()==0:
        demo=[
          ('Nova X Pro Smartphone','Electronics','6.7-inch AMOLED display, 5G connectivity, 256GB storage and all-day battery.',42999,49999,18,'phone.svg',True),
          ('Sonic Wireless Headphones','Electronics','Comfort-fit wireless headphones with active noise cancellation.',3499,4999,32,'headphones.svg',True),
          ('Urban Everyday Backpack','Fashion','Water-resistant 24L backpack with padded laptop compartment.',1499,1999,45,'bag.svg',True),
          ('Minimal Desk Lamp','Home & Living','Dimmable LED desk lamp with adjustable neck and warm light.',1199,1599,24,'lamp.svg',False),
          ('Pulse Smart Watch','Electronics','Fitness tracking, heart-rate insights and bright touch display.',2799,3999,27,'watch.svg',True),
          ('Ceramic Coffee Set','Home & Living','Elegant two-cup ceramic set for your daily coffee ritual.',799,1099,50,'coffee.svg',False),
        ]
        for n,c,d,p,cp,s,img,f in demo:
            db.session.add(Product(name=n,category=c,description=d,price=p,compare_price=cp,stock=s,image=img,featured=f))
    db.session.commit()

@app.route('/')
def home():
    featured=Product.query.filter_by(active=True,featured=True).order_by(Product.created_at.desc()).limit(4).all()
    latest=Product.query.filter_by(active=True).order_by(Product.created_at.desc()).limit(8).all()
    categories=db.session.query(Product.category).filter_by(active=True).distinct().all()
    return render_template('home.html',featured=featured,products=latest,categories=[x[0] for x in categories])

@app.route('/products')
def products():
    q=request.args.get('q','').strip(); category=request.args.get('category','').strip()
    query=Product.query.filter_by(active=True)
    if q: query=query.filter(db.or_(Product.name.ilike(f'%{q}%'),Product.description.ilike(f'%{q}%')))
    if category: query=query.filter_by(category=category)
    items=query.order_by(Product.featured.desc(),Product.created_at.desc()).all()
    categories=[x[0] for x in db.session.query(Product.category).filter_by(active=True).distinct().all()]
    return render_template('products.html',products=items,categories=categories,q=q,category=category)

@app.route('/product/<int:pid>')
def product_detail(pid):
    p=Product.query.filter_by(id=pid,active=True).first_or_404()
    related=Product.query.filter(Product.category==p.category,Product.id!=p.id,Product.active==True).limit(4).all()
    return render_template('product.html',p=p,related=related)

@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        name=request.form.get('name','').strip(); email=request.form.get('email','').strip().lower()
        password=request.form.get('password','')
        if len(name)<2 or len(password)<8:
            flash('Enter your name and a password with at least 8 characters.','danger')
        elif User.query.filter_by(email=email).first():
            flash('An account with this email already exists.','danger')
        else:
            u=User(name=name,email=email,phone=request.form.get('phone',''),password_hash=generate_password_hash(password))
            db.session.add(u); db.session.commit(); flash('Account created. Please sign in.','success')
            return redirect(url_for('login'))
    return render_template('auth.html',mode='register')

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form.get('email','').strip().lower(); password=request.form.get('password','')
        u=User.query.filter_by(email=email).first()
        if not u or not check_password_hash(u.password_hash,password) or not u.active:
            flash('Email or password is incorrect, or the account is disabled.','danger')
        else:
            session.clear(); session['user_id']=u.id
            flash(f"Welcome back, {u.name.split()[0]}!",'success')
            return redirect(url_for('admin_dashboard') if u.role=='admin' else request.args.get('next') or url_for('products'))
    return render_template('auth.html',mode='login')

@app.route('/logout')
def logout():
    session.clear(); flash('You have been signed out.','info'); return redirect(url_for('home'))

@app.route('/cart')
@user_required
def cart():
    rows,subtotal,shipping,total=cart_data(current_user().id)
    return render_template('cart.html',rows=rows,subtotal=subtotal,shipping=shipping,total=total)

@app.route('/cart/add/<int:pid>',methods=['POST'])
@user_required
def cart_add(pid):
    p=Product.query.filter_by(id=pid,active=True).first_or_404()
    qty=max(1,int(request.form.get('quantity',1)))
    if p.stock<qty: flash('Requested quantity is not available.','danger')
    else:
        item=CartItem.query.filter_by(user_id=current_user().id,product_id=pid).first()
        if item:
            if item.quantity+qty>p.stock: flash('Cart quantity exceeds available stock.','warning')
            else: item.quantity+=qty; db.session.commit(); flash('Cart updated.','success')
        else:
            db.session.add(CartItem(user_id=current_user().id,product_id=pid,quantity=qty)); db.session.commit(); flash('Product added to cart.','success')
    return redirect(request.referrer or url_for('products'))

@app.route('/cart/update/<int:item_id>',methods=['POST'])
@user_required
def cart_update(item_id):
    item=CartItem.query.filter_by(id=item_id,user_id=current_user().id).first_or_404()
    qty=int(request.form.get('quantity',1))
    if qty<1 or qty>item.product.stock: flash('Choose a valid quantity within available stock.','danger')
    else: item.quantity=qty; db.session.commit(); flash('Cart updated.','success')
    return redirect(url_for('cart'))

@app.route('/cart/remove/<int:item_id>',methods=['POST'])
@user_required
def cart_remove(item_id):
    item=CartItem.query.filter_by(id=item_id,user_id=current_user().id).first_or_404()
    db.session.delete(item); db.session.commit(); flash('Item removed.','info'); return redirect(url_for('cart'))

@app.route('/checkout',methods=['GET','POST'])
@user_required
def checkout():
    rows,subtotal,shipping,total=cart_data(current_user().id)
    if not rows: flash('Your cart is empty.','info'); return redirect(url_for('products'))
    if request.method=='POST':
        address=request.form.get('address','').strip()
        if len(address)<12: flash('Please enter a complete delivery address.','danger')
        elif any(x.product.stock<x.quantity for x in rows): flash('Stock changed. Update your cart and try again.','danger')
        else:
            order=Order(user_id=current_user().id,address=address,subtotal=subtotal,shipping=shipping,total=total,
                        status='Placed',payment_status='Pending')
            db.session.add(order); db.session.flush()
            for row in rows:
                p=row.product; p.stock-=row.quantity
                order.items.append(OrderItem(product_id=p.id,product_name=p.name,price=p.price,quantity=row.quantity,image=p.image))
                db.session.delete(row)
            db.session.commit(); session['pending_order_id']=order.id
            return redirect(url_for('dummy_payment',oid=order.id))
    return render_template('checkout.html',rows=rows,subtotal=subtotal,shipping=shipping,total=total)

@app.route('/payment/test/<int:oid>',methods=['GET','POST'])
@user_required
def dummy_payment(oid):
    order=Order.query.filter_by(id=oid,user_id=current_user().id).first_or_404()
    if order.payment_status=='Paid': return redirect(url_for('order_detail',oid=oid))
    if request.method=='POST':
        action=request.form.get('action')
        if action=='success':
            order.payment_status='Paid'; order.status='Processing'
            order.payment_id='pay_test_'+uuid.uuid4().hex[:14]
            log(f'Test payment successful for order #{order.id}')
            db.session.commit(); flash('Test payment successful! This was a dummy transaction; no money was charged.','success')
            return redirect(url_for('order_detail',oid=oid))
        order.payment_status='Failed'; order.status='Payment failed'
        for line in order.items:
            p=db.session.get(Product,line.product_id)
            if p: p.stock+=line.quantity
        db.session.commit(); flash('Test payment marked as failed. Stock has been restored.','warning')
        return redirect(url_for('my_orders'))
    return render_template('payment.html',order=order)

@app.route('/orders')
@user_required
def my_orders():
    orders=Order.query.filter_by(user_id=current_user().id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html',orders=orders)

@app.route('/orders/<int:oid>')
@user_required
def order_detail(oid):
    order=Order.query.filter_by(id=oid,user_id=current_user().id).first_or_404()
    return render_template('order_detail.html',order=order)

@app.route('/assistant',methods=['GET','POST'])
def assistant():
    answer=None; question=''
    if request.method=='POST':
        question=request.form.get('question','').strip()
        q=question.lower()
        if any(k in q for k in ['cart','add to cart','basket']): answer='Open a product, choose the quantity and select Add to cart. Sign in first. Your cart is available from the top navigation.'
        elif any(k in q for k in ['payment','razorpay','pay','checkout']): answer='At checkout, enter your delivery address and continue to the Razorpay Test Checkout. Choose Simulate success or Simulate failure. This demo never charges real money.'
        elif any(k in q for k in ['order','track','delivery','shipping']): answer='Sign in and open My Orders to view each order status, payment status, order ID and items. Admins update fulfilment status in the admin Orders screen.'
        elif any(k in q for k in ['return','refund','cancel']): answer='This demo supports order-status tracking. Contact the store administrator for a return or refund request; payment simulation does not move real money.'
        elif any(k in q for k in ['admin','product upload','add product']): answer='Administrators sign in using the admin account, then open Admin Dashboard → Products → Add Product. Add a name, category, price, stock, description and optional image.'
        else: answer='I can help with products, cart, checkout, test payments, order tracking and admin product management. Try asking: “How do I track my order?”'
    return render_template('assistant.html',answer=answer,question=question)

# ---------------- Admin area ----------------
@app.route('/admin')
@admin_required
def admin_dashboard():
    stats={'products':Product.query.count(),'users':User.query.filter_by(role='user').count(),
           'orders':Order.query.count(),'revenue':db.session.query(db.func.coalesce(db.func.sum(Order.total),0)).filter_by(payment_status='Paid').scalar(),
           'pending':Order.query.filter(Order.status.in_(['Placed','Processing'])).count()}
    recent=Order.query.order_by(Order.created_at.desc()).limit(7).all()
    low=Product.query.filter(Product.stock<=5,Product.active==True).order_by(Product.stock.asc()).limit(6).all()
    return render_template('admin/dashboard.html',stats=stats,recent=recent,low=low)

@app.route('/admin/products')
@admin_required
def admin_products():
    q=request.args.get('q','').strip()
    query=Product.query
    if q: query=query.filter(Product.name.ilike(f'%{q}%'))
    return render_template('admin/products.html',products=query.order_by(Product.created_at.desc()).all(),q=q)

@app.route('/admin/products/new',methods=['GET','POST'])
@admin_required
def product_new():
    if request.method=='POST':
        p=save_product(Product())
        if p: db.session.add(p); log(f'Added product: {p.name}'); db.session.commit(); flash('Product added successfully.','success'); return redirect(url_for('admin_products'))
    return render_template('admin/product_form.html',p=None)

def save_product(p):
    try:
        p.name=request.form.get('name','').strip()
        p.category=request.form.get('category','General').strip()
        p.description=request.form.get('description','').strip()
        p.price=Decimal(request.form.get('price','0'))
        p.compare_price=Decimal(request.form.get('compare_price') or '0')
        p.stock=max(0,int(request.form.get('stock','0')))
        p.featured=bool(request.form.get('featured'))
        p.active=bool(request.form.get('active'))
        f=request.files.get('image')
        if f and f.filename:
            ext=f.filename.rsplit('.',1)[-1].lower()
            if ext not in ALLOWED: raise ValueError('Upload a JPG, PNG, WEBP or GIF image.')
            filename=uuid.uuid4().hex+'.'+ext
            f.save(os.path.join(app.config['UPLOAD_FOLDER'],filename)); p.image='uploads/'+filename
        if not p.name or p.price<0: raise ValueError('Product name and a valid price are required.')
        return p
    except Exception as e:
        flash(str(e),'danger'); return None

@app.route('/admin/products/<int:pid>/edit',methods=['GET','POST'])
@admin_required
def product_edit(pid):
    p=Product.query.get_or_404(pid)
    if request.method=='POST':
        if save_product(p): log(f'Updated product: {p.name}'); db.session.commit(); flash('Product updated.','success'); return redirect(url_for('admin_products'))
    return render_template('admin/product_form.html',p=p)

@app.route('/admin/products/<int:pid>/toggle',methods=['POST'])
@admin_required
def product_toggle(pid):
    p=Product.query.get_or_404(pid); p.active=not p.active; db.session.commit(); flash('Product visibility updated.','success'); return redirect(url_for('admin_products'))

@app.route('/admin/orders')
@admin_required
def admin_orders():
    status=request.args.get('status','')
    query=Order.query
    if status: query=query.filter_by(status=status)
    return render_template('admin/orders.html',orders=query.order_by(Order.created_at.desc()).all(),status=status)

@app.route('/admin/orders/<int:oid>',methods=['GET','POST'])
@admin_required
def admin_order_detail(oid):
    order=Order.query.get_or_404(oid)
    if request.method=='POST':
        new=request.form.get('status')
        if new in ['Placed','Processing','Shipped','Out for delivery','Delivered','Cancelled']:
            order.status=new; log(f'Order #{oid} status changed to {new}'); db.session.commit(); flash('Order status updated.','success')
        return redirect(url_for('admin_order_detail',oid=oid))
    return render_template('admin/order_detail.html',order=order)

@app.route('/admin/users')
@admin_required
def admin_users():
    users=User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html',users=users)

@app.route('/admin/users/<int:uid>/toggle',methods=['POST'])
@admin_required
def user_toggle(uid):
    u=User.query.get_or_404(uid)
    if u.role=='admin': flash('Admin accounts cannot be disabled here.','warning')
    else: u.active=not u.active; db.session.commit(); flash('User access updated.','success')
    return redirect(url_for('admin_users'))

@app.errorhandler(403)
def forbidden(e): return render_template('error.html',code=403,message='You do not have permission to view this page.'),403
@app.errorhandler(404)
def not_found(e): return render_template('error.html',code=404,message='The page you requested was not found.'),404

with app.app_context(): seed()
if __name__=='__main__':
    app.run(debug=True)
