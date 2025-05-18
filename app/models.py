from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    
    orders = db.relationship('Order', backref='user', lazy=True)
    cart_items = db.relationship('CartItem', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(200))
    
    products = db.relationship('Product', backref='category', lazy=True)
    
    def __repr__(self):
        return f'<Category {self.name}>'


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200))
    stock = db.Column(db.Integer, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    brand = db.Column(db.String(50))
    memory = db.Column(db.Integer)  # Для электронных устройств (в ГБ)
    is_active = db.Column(db.Boolean, default=True)  # Флаг активности товара
    
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    cart_items = db.relationship('CartItem', backref='product', lazy=True)
    
    def __repr__(self):
        return f'<Product {self.name}>'


class Tariff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    period = db.Column(db.String(20), nullable=False)  # месяц, год и т.д.
    features = db.Column(db.Text)  # JSON строка с особенностями тарифа
    image = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    
    # Связь с пользователями через таблицу подключенных тарифов
    subscriptions = db.relationship('TariffSubscription', backref='tariff', lazy=True)
    
    def __repr__(self):
        return f'<Tariff {self.name}>'


class TariffSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tariff_id = db.Column(db.Integer, db.ForeignKey('tariff.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, active, cancelled, expired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    activated_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)
    admin_comment = db.Column(db.Text)
    
    # Определяем отношение к пользователю
    user = db.relationship('User', backref='tariff_subscriptions')
    
    def __repr__(self):
        return f'<TariffSubscription {self.id}, User: {self.user_id}, Tariff: {self.tariff_id}, Status: {self.status}>'


class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    duration = db.Column(db.String(20))  # разовая услуга, подписка и т.д.
    image = db.Column(db.String(200))
    category = db.Column(db.String(50))  # internet, calls, security, other
    
    def __repr__(self):
        return f'<Service {self.name}>'


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='new')  # new, processing, shipped, delivered, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_price = db.Column(db.Float, default=0.0)
    shipping_address = db.Column(db.String(200))
    shipping_method = db.Column(db.String(50))  # courier, pickup
    payment_method = db.Column(db.String(50))   # card, cash
    contact_phone = db.Column(db.String(20))
    contact_email = db.Column(db.String(120))
    notes = db.Column(db.Text)
    
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Order {self.id}>'


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, nullable=False)
    
    def __repr__(self):
        return f'<OrderItem {self.id}>'


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CartItem {self.id}>'


def init_db():
    """Инициализация базы данных тестовыми данными"""
    # Проверяем, есть ли уже данные в БД
    if Category.query.first() is not None:
        return
    
    # Создаем категории
    categories = [
        {'name': 'Смартфоны', 'description': 'Мобильные телефоны разных брендов', 'image': 'smartphones.jpg'},
        {'name': 'Планшеты', 'description': 'Планшетные компьютеры', 'image': 'tablets.jpg'},
        {'name': 'Аксессуары', 'description': 'Аксессуары для мобильных устройств', 'image': 'accessories.jpg'},
    ]
    
    for cat_data in categories:
        category = Category(**cat_data)
        db.session.add(category)
    
    db.session.commit()
    
    # Добавляем продукты
    products = [
        {
            'name': 'iPhone 15', 
            'description': 'Смартфон Apple iPhone 15 с OLED-дисплеем и A16 Bionic', 
            'price': 89990.0, 
            'image': 'iphone15.jpg',
            'stock': 15,
            'category_id': 1
        },
        {
            'name': 'Samsung Galaxy S24', 
            'description': 'Флагманский смартфон Samsung с процессором Exynos', 
            'price': 79990.0, 
            'image': 'samsung_s24.jpg',
            'stock': 25,
            'category_id': 1
        },
        {
            'name': 'iPad Air', 
            'description': 'Планшет Apple iPad Air с чипом M1', 
            'price': 59990.0, 
            'image': 'ipad_air.jpg',
            'stock': 10,
            'category_id': 2
        },
        {
            'name': 'Samsung Galaxy Tab S9', 
            'description': 'Планшет Samsung Galaxy Tab S9 с AMOLED-экраном', 
            'price': 49990.0, 
            'image': 'samsung_tab_s9.jpg',
            'stock': 12,
            'category_id': 2
        },
        {
            'name': 'Беспроводные наушники AirPods Pro 2', 
            'description': 'Наушники с активным шумоподавлением', 
            'price': 24990.0, 
            'image': 'airpods_pro.jpg',
            'stock': 30,
            'category_id': 3
        },
    ]
    
    for prod_data in products:
        product = Product(**prod_data)
        db.session.add(product)
    
    # Добавляем тарифы
    tariffs = [
        {
            'name': 'Безлимит Premium', 
            'description': 'Безлимитный интернет и 1000 минут', 
            'price': 650.0, 
            'period': 'месяц',
            'features': '{"internet": "безлимит", "minutes": 1000, "sms": 100}',
            'image': 'tariff_unlimited.jpg'
        },
        {
            'name': 'Оптима', 
            'description': '30 ГБ интернета и 500 минут', 
            'price': 450.0, 
            'period': 'месяц',
            'features': '{"internet": "30GB", "minutes": 500, "sms": 50}',
            'image': 'tariff_optima.jpg'
        },
        {
            'name': 'Лайт', 
            'description': '15 ГБ интернета и 200 минут', 
            'price': 300.0, 
            'period': 'месяц',
            'features': '{"internet": "15GB", "minutes": 200, "sms": 30}',
            'image': 'tariff_light.jpg'
        },
    ]
    
    for tariff_data in tariffs:
        tariff = Tariff(**tariff_data)
        db.session.add(tariff)
    
    # Добавляем услуги
    services = [
        {
            'name': 'Защита от спама', 
            'description': 'Блокировка нежелательных вызовов и SMS', 
            'price': 60.0, 
            'duration': 'месяц',
            'image': 'service_spam_protection.jpg'
        },
        {
            'name': 'Родительский контроль', 
            'description': 'Контроль использования интернета детьми', 
            'price': 100.0, 
            'duration': 'месяц',
            'image': 'service_parental_control.jpg'
        },
        {
            'name': 'Безлимит на соцсети', 
            'description': 'Безлимитный трафик для популярных соцсетей', 
            'price': 150.0, 
            'duration': 'месяц',
            'image': 'service_social_unlimited.jpg'
        },
    ]
    
    for service_data in services:
        service = Service(**service_data)
        db.session.add(service)
    
    # Добавляем тестового пользователя
    test_user = User(
        username='test_user',
        email='test@example.com',
        first_name='Иван',
        last_name='Иванов',
        phone='+7 (999) 123-45-67',
        address='г. Москва, ул. Пушкина, д. 10'
    )
    test_user.set_password('password123')
    db.session.add(test_user)
    
    db.session.commit()
