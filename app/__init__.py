from flask import Flask
from flask_login import LoginManager
import os
import logging
from flask_admin import Admin as FlaskAdmin
from flask_admin.contrib.sqla import ModelView
from sqlalchemy.exc import OperationalError
from flask_wtf.csrf import CSRFProtect

# Настройка логирования
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

login_manager = LoginManager()
flask_admin = FlaskAdmin()  # Переименовываем переменную admin в flask_admin
csrf = CSRFProtect()  # Инициализация CSRF защиты

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'telecom_site.sqlite'),
        UPLOAD_FOLDER=os.path.join(app.static_folder, 'img/products'),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.instance_path, 'telecom_site.sqlite')}?timeout=60",
        SQLALCHEMY_ENGINE_OPTIONS={
            'pool_recycle': 280,
            'pool_timeout': 60,
            'pool_pre_ping': True,
        },
        SQLALCHEMY_TRACK_MODIFICATIONS=False,        # Настройки для Flask-Mail
        MAIL_SERVER=os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
        MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
        MAIL_USE_TLS=True,
        MAIL_USERNAME=os.environ.get('MAIL_USERNAME', 'telecomsite@example.com'),
        MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD', 'app_password_here'),
        MAIL_DEFAULT_SENDER=('TBMP', os.environ.get('MAIL_SENDER', 'no-reply@tbmp.com')),
        SITE_URL=os.environ.get('SITE_URL', 'http://localhost:5000/')
    )
    
    # Создаем instance папку, если она не существует
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        logger.info(f"Instance директория проверена: {app.instance_path}")
    except Exception as e:
        logger.error(f"Не удалось создать instance директорию: {str(e)}")    # Инициализация базы данных
    from .models import db, User, Product, Category, Order, OrderItem, Tariff, Service, CartItem
    from .db_utils import configure_sqlite
    from .email import mail
    
    db.init_app(app)
    mail.init_app(app)
    
    # Настраиваем SQLite для оптимальной работы
    with app.app_context():
        try:
            configure_sqlite(db.engine, timeout=60, journal_mode='WAL')
            logger.info("SQLite настроен с увеличенным timeout и WAL-режимом")
        except Exception as e:
            logger.error(f"Ошибка при настройке SQLite: {str(e)}")

    # Инициализация login manager
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Инициализация flask-admin
    flask_admin.init_app(app)
    flask_admin.add_view(ModelView(User, db.session))
    flask_admin.add_view(ModelView(Product, db.session))
    flask_admin.add_view(ModelView(Category, db.session))
    flask_admin.add_view(ModelView(Tariff, db.session))
    flask_admin.add_view(ModelView(Service, db.session))

    # Регистрация маршрутов
    from .routes import main, catalog, tariffs, auth, cart
    from .routes import admin as admin_routes  # Импортируем маршруты admin с другим именем
    
    app.register_blueprint(main.bp)
    app.register_blueprint(catalog.bp)
    app.register_blueprint(tariffs.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(cart.bp)
    app.register_blueprint(admin_routes.bp)

    # Создание папок, если их нет
    try:
        os.makedirs(app.instance_path)
        os.makedirs(app.config['UPLOAD_FOLDER'])
    except OSError:
        pass

    # Инициализация БД при первом запуске
    with app.app_context():
        db.create_all()
        from .models import init_db
        init_db()

    # Регистрация обработчиков ошибок
    from .error_handlers import init_error_handlers
    init_error_handlers(app)

    return app
