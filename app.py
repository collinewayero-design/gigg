"""
GigSpace - Gamified Digital Economy Platform
Flask Backend Application
Author: Collin Ewayero
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import secrets
from functools import wraps

# ============================================
# APP CONFIGURATION
# ============================================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///gigspace.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth_page'

# ============================================
# CONSTANTS
# ============================================
EXCHANGE_RATE = 250  # 250 GC = $1.00 USD
WELCOME_BONUS = 50   # 50 GC = $0.20 USD
REFERRAL_BONUS = 250 # 250 GC = $1.00 USD
DAILY_BONUS = 1      # 1 GC per day
WEEKLY_BONUS = 10    # 10 GC on day 7

# ============================================
# DATABASE MODELS
# ============================================

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='MEMBER')  # MEMBER, PRO, ADMIN, OWNER
    balance = db.Column(db.Integer, default=0)
    daily_streak = db.Column(db.Integer, default=0)
    last_daily_claim = db.Column(db.DateTime, nullable=True)
    has_claimed_welcome = db.Column(db.Boolean, default=False)
    avatar_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade='all, delete-orphan')
    completed_tasks = db.relationship('UserTask', backref='user', lazy=True, cascade='all, delete-orphan')
    purchases = db.relationship('Purchase', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'balance': self.balance,
            'daily_streak': self.daily_streak,
            'has_claimed_welcome': self.has_claimed_welcome,
            'avatar_url': self.avatar_url or f'https://i.pravatar.cc/300?u={self.id}',
            'last_daily_claim': self.last_daily_claim.timestamp() * 1000 if self.last_daily_claim else 0
        }


class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # earn, spend, bonus, referral, admin
    description = db.Column(db.String(255), nullable=False)
    balance_after = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': 'EARN' if self.amount > 0 else 'SPEND',
            'amount': abs(self.amount),
            'description': self.description,
            'timestamp': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'status': 'COMPLETED'
        }


class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # VIDEO, CPA, SURVEY
    reward_amount = db.Column(db.Integer, nullable=False)
    requires_verification = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    completions = db.relationship('UserTask', backref='task', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'type': self.type,
            'reward': self.reward_amount,
            'requiresVerification': self.requires_verification
        }


class UserTask(db.Model):
    __tablename__ = 'user_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'task_id', name='unique_user_task'),)


class ShopItem(db.Model):
    __tablename__ = 'shop_items'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    stock_quantity = db.Column(db.Integer, default=-1)  # -1 = unlimited
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    purchases = db.relationship('Purchase', backref='item', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'price': self.price,
            'category': self.category,
            'imageUrl': self.image_url,
            'sellerId': 'official'
        }


class Purchase(db.Model):
    __tablename__ = 'purchases'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('shop_items.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    total_price = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='completed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================
# LOGIN MANAGER
# ============================================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ============================================
# DECORATORS
# ============================================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['ADMIN', 'OWNER']:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# ROUTES - PAGES
# ============================================
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')


@app.route('/auth')
def auth_page():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('auth.html')


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user.to_dict())


@app.route('/earn')
@login_required
def earn_page():
    return render_template('earn.html', user=current_user.to_dict())


@app.route('/shop')
@login_required
def shop_page():
    return render_template('shop.html', user=current_user.to_dict())


@app.route('/learn')
@login_required
def learn_page():
    return render_template('learn.html', user=current_user.to_dict())


@app.route('/leaderboard')
@login_required
def leaderboard_page():
    return render_template('leaderboard.html', user=current_user.to_dict())


@app.route('/profile')
@login_required
def profile_page():
    return render_template('profile.html', user=current_user.to_dict())


@app.route('/wallet')
@login_required
def wallet_page():
    return render_template('wallet.html', user=current_user.to_dict())


@app.route('/admin')
@login_required
@admin_required
def admin_page():
    return render_template('admin.html', user=current_user.to_dict())


# ============================================
# API ROUTES - AUTHENTICATION
# ============================================
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.get_json()
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'success': False, 'message': 'Email already registered'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'success': False, 'message': 'Username already taken'}), 400
    
    user = User(
        username=data['username'],
        email=data['email'],
        avatar_url=f"https://i.pravatar.cc/300?u={data['email']}"
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    login_user(user, remember=True)
    
    return jsonify({
        'success': True,
        'message': 'Account created successfully',
        'user': user.to_dict()
    })


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
    
    login_user(user, remember=True)
    
    return jsonify({
        'success': True,
        'message': 'Login successful',
        'user': user.to_dict()
    })


@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'success': True, 'message': 'Logged out successfully'})


# ============================================
# API ROUTES - USER ACTIONS
# ============================================
@app.route('/api/user/profile', methods=['GET'])
@login_required
def get_profile():
    return jsonify({'success': True, 'user': current_user.to_dict()})


@app.route('/api/user/claim-welcome', methods=['POST'])
@login_required
def claim_welcome_bonus():
    if current_user.has_claimed_welcome:
        return jsonify({'success': False, 'message': 'Welcome bonus already claimed'}), 400
    
    current_user.balance += WELCOME_BONUS
    current_user.has_claimed_welcome = True
    
    transaction = Transaction(
        user_id=current_user.id,
        amount=WELCOME_BONUS,
        type='bonus',
        description='Welcome Bonus',
        balance_after=current_user.balance
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Welcome bonus claimed! +{WELCOME_BONUS} GC',
        'new_balance': current_user.balance
    })


@app.route('/api/user/claim-daily', methods=['POST'])
@login_required
def claim_daily_bonus():
    now = datetime.utcnow()
    
    if current_user.last_daily_claim:
        time_since_last = now - current_user.last_daily_claim
        
        if time_since_last.total_seconds() < 24 * 3600:
            return jsonify({
                'success': False,
                'message': 'Daily bonus not ready yet'
            }), 400
        
        # Check if streak continues (within 48 hours)
        if time_since_last.total_seconds() < 48 * 3600:
            current_user.daily_streak += 1
        else:
            current_user.daily_streak = 1
    else:
        current_user.daily_streak = 1
    
    # Reward: 10 GC on day 7, 1 GC otherwise
    amount = WEEKLY_BONUS if current_user.daily_streak % 7 == 0 else DAILY_BONUS
    
    current_user.balance += amount
    current_user.last_daily_claim = now
    
    transaction = Transaction(
        user_id=current_user.id,
        amount=amount,
        type='bonus',
        description=f'Daily Login Bonus (Day {current_user.daily_streak})',
        balance_after=current_user.balance
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Claimed {amount} GC! Streak: {current_user.daily_streak} days',
        'amount': amount,
        'streak': current_user.daily_streak,
        'new_balance': current_user.balance
    })


# ============================================
# API ROUTES - TASKS
# ============================================
@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    tasks = Task.query.filter_by(is_active=True).all()
    return jsonify({
        'success': True,
        'tasks': [task.to_dict() for task in tasks]
    })


@app.route('/api/tasks/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    # Check if already completed
    if UserTask.query.filter_by(user_id=current_user.id, task_id=task_id).first():
        return jsonify({'success': False, 'message': 'Task already completed'}), 400
    
    # Credit coins
    current_user.balance += task.reward_amount
    
    # Record completion
    user_task = UserTask(user_id=current_user.id, task_id=task_id)
    
    # Record transaction
    transaction = Transaction(
        user_id=current_user.id,
        amount=task.reward_amount,
        type='earn',
        description=f'Task: {task.title}',
        balance_after=current_user.balance
    )
    
    db.session.add(user_task)
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Earned +{task.reward_amount} GC',
        'amount': task.reward_amount,
        'new_balance': current_user.balance
    })


# ============================================
# API ROUTES - SHOP
# ============================================
@app.route('/api/shop/items', methods=['GET'])
@login_required
def get_shop_items():
    items = ShopItem.query.filter_by(is_active=True).all()
    return jsonify({
        'success': True,
        'items': [item.to_dict() for item in items]
    })


@app.route('/api/shop/purchase/<int:item_id>', methods=['POST'])
@login_required
def purchase_item(item_id):
    data = request.get_json()
    quantity = data.get('quantity', 1)
    
    item = ShopItem.query.get_or_404(item_id)
    total_price = item.price * quantity
    
    if current_user.balance < total_price:
        return jsonify({
            'success': False,
            'message': f'Insufficient balance. Need {total_price - current_user.balance} more GC'
        }), 400
    
    # Deduct balance
    current_user.balance -= total_price
    
    # Record purchase
    purchase = Purchase(
        user_id=current_user.id,
        item_id=item_id,
        quantity=quantity,
        total_price=total_price
    )
    
    # Record transaction
    transaction = Transaction(
        user_id=current_user.id,
        amount=-total_price,
        type='spend',
        description=f'Purchased: {item.title}',
        balance_after=current_user.balance
    )
    
    db.session.add(purchase)
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Purchase successful!',
        'new_balance': current_user.balance
    })


# ============================================
# API ROUTES - TRANSACTIONS
# ============================================
@app.route('/api/transactions', methods=['GET'])
@login_required
def get_transactions():
    transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.created_at.desc())\
        .limit(50)\
        .all()
    
    return jsonify({
        'success': True,
        'transactions': [tx.to_dict() for tx in transactions]
    })


# ============================================
# API ROUTES - LEADERBOARD
# ============================================
@app.route('/api/leaderboard', methods=['GET'])
@login_required
def get_leaderboard():
    users = User.query.order_by(User.balance.desc()).limit(100).all()
    
    leaderboard = []
    for idx, user in enumerate(users, 1):
        leaderboard.append({
            'rank': idx,
            'username': user.username,
            'coins': user.balance,
            'avatarUrl': user.avatar_url or f'https://i.pravatar.cc/150?u={user.id}',
            'trend': 'same'
        })
    
    return jsonify({
        'success': True,
        'leaderboard': leaderboard
    })


# ============================================
# API ROUTES - ADMIN
# ============================================
@app.route('/api/admin/mint', methods=['POST'])
@login_required
@admin_required
def admin_mint_coins():
    data = request.get_json()
    amount = data.get('amount', 1000)
    
    current_user.balance += amount
    
    transaction = Transaction(
        user_id=current_user.id,
        amount=amount,
        type='admin',
        description='Admin Mint',
        balance_after=current_user.balance
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Minted {amount} GC',
        'new_balance': current_user.balance
    })


# ============================================
# INITIALIZE DATABASE
# ============================================
def init_db():
    with app.app_context():
        db.create_all()
        
        # Create seed tasks if none exist
        if Task.query.count() == 0:
            tasks = [
                Task(title='Watch 30s Video Ad', description='Watch a short advertisement', type='VIDEO', reward_amount=10),
                Task(title='Install Partner App', description='Download and open our partner app', type='CPA', reward_amount=500, requires_verification=True),
                Task(title='Complete Survey', description='Share your opinion in 5 minutes', type='SURVEY', reward_amount=50),
                Task(title='Sign up for Newsletter', description='Subscribe to partner newsletter', type='CPA', reward_amount=100, requires_verification=True),
                Task(title='Watch Premium Ad', description='Watch 60-second premium content', type='VIDEO', reward_amount=20),
                Task(title='Install Game App', description='Install and reach level 5', type='CPA', reward_amount=1000, requires_verification=True),
                Task(title='Quick Poll', description='3-question quick poll', type='SURVEY', reward_amount=25),
                Task(title='Trial Signup', description='Sign up for free trial (no CC)', type='CPA', reward_amount=750, requires_verification=True),
            ]
            db.session.add_all(tasks)
        
        # Create seed shop items if none exist
        if ShopItem.query.count() == 0:
            items = [
                ShopItem(title='$5 Amazon Gift Card', description='Instant digital delivery', price=1250, category='Gift Cards', image_url='https://images.unsplash.com/photo-1523474253046-8cd2748b5fd2?w=400'),
                ShopItem(title='$10 Amazon Gift Card', description='Instant digital delivery', price=2500, category='Gift Cards', image_url='https://images.unsplash.com/photo-1523474253046-8cd2748b5fd2?w=400'),
                ShopItem(title='$5 Starbucks eGift', description='Coffee on us!', price=1250, category='Gift Cards', image_url='https://images.unsplash.com/photo-1511920170033-f8396924c348?w=400'),
                ShopItem(title='$10 iTunes Card', description='Music, apps, and more', price=2500, category='Gift Cards', image_url='https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=400'),
                ShopItem(title='Netflix 1 Month', description='Stream unlimited movies', price=2500, category='Subscriptions', image_url='https://images.unsplash.com/photo-1574375927938-d5a98e8ffe85?w=400'),
                ShopItem(title='Spotify Premium 1 Month', description='30 days ad-free music', price=2000, category='Subscriptions', image_url='https://images.unsplash.com/photo-1614680376593-902f74cf0d41?w=400'),
                ShopItem(title='$25 Visa Gift Card', description='Use anywhere Visa is accepted', price=6250, category='Gift Cards', image_url='https://images.unsplash.com/photo-1563013544-824ae1b704d3?w=400'),
                ShopItem(title='Xbox Game Pass 1 Month', description='Access 100+ games', price=2500, category='Gaming', image_url='https://images.unsplash.com/photo-1622297845775-5ff3fef71d13?w=400'),
            ]
            db.session.add_all(items)
        
        db.session.commit()
        print("✅ Database initialized with seed data")


# ============================================
# RUN APPLICATION
# ============================================
if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
