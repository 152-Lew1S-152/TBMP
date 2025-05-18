from functools import wraps
import time
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy.exc import OperationalError
from ..models import db, Product, Category, Tariff, Service, User
from ..db_utils import safe_db_operation

# Настройка логгера для модуля
logger = logging.getLogger(__name__)

# Изменяем имя блюпринта на 'admin_panel', чтобы избежать конфликта с flask-admin
bp = Blueprint('admin_panel', __name__, url_prefix='/admin')

# Декоратор для проверки прав администратора
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)  # Запрещено
        return f(*args, **kwargs)
    return decorated_function

# Главная страница админ-панели
@bp.route('/')
@login_required
@admin_required
def index():
    # Добавляем информацию о новых заявках на тарифы
    from ..models import TariffSubscription
    
    pending_subscriptions = TariffSubscription.query.filter_by(status='pending').count()
    
    return render_template('admin/index.html', pending_subscriptions=pending_subscriptions)

# Управление товарами
@bp.route('/products')
@login_required
@admin_required
def products():
    products = Product.query.all()
    categories = Category.query.all()
    return render_template('admin/products.html', products=products, categories=categories)

# Управление категориями
@bp.route('/categories')
@login_required
@admin_required
def categories():
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)

# Управление заявками на подключение тарифов
@bp.route('/tariff_subscriptions')
@login_required
@admin_required
def tariff_subscriptions():
    from ..models import TariffSubscription
    
    status_filter = request.args.get('status', 'all')
    
    # Базовый запрос
    query = TariffSubscription.query
    
    # Применяем фильтр по статусу
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    # Получаем список подписок с сортировкой по дате создания (новые в начале)
    subscriptions = query.order_by(TariffSubscription.created_at.desc()).all()
    
    return render_template(
        'admin/tariff_subscriptions.html',
        subscriptions=subscriptions,
        status_filter=status_filter
    )

# Обработка подписки на тариф
@bp.route('/tariff_subscriptions/<int:subscription_id>/<action>', methods=['POST'])
@login_required
@admin_required
def process_tariff_subscription(subscription_id, action):
    from ..models import TariffSubscription
    from ..email import send_tariff_subscription_notification_user
    from datetime import datetime, timedelta
    
    subscription = TariffSubscription.query.get_or_404(subscription_id)
    
    if action == 'activate':
        if subscription.status == 'active':
            flash('Подписка уже активирована.', 'warning')
        else:
            # Активируем подписку
            subscription.status = 'active'
            subscription.activated_at = datetime.utcnow()
            
            # Определяем дату окончания в зависимости от периода тарифа
            if subscription.tariff.period == 'месяц':
                subscription.expires_at = subscription.activated_at + timedelta(days=30)
            elif subscription.tariff.period == 'год':
                subscription.expires_at = subscription.activated_at + timedelta(days=365)
            else:
                # Для других периодов по умолчанию устанавливаем месяц
                subscription.expires_at = subscription.activated_at + timedelta(days=30)
            
            subscription.admin_comment = request.form.get('admin_comment', '')
            
            db.session.commit()
            
            # Отправляем уведомление пользователю
            send_tariff_subscription_notification_user(subscription)
            
            flash(f'Подписка на тариф "{subscription.tariff.name}" для пользователя {subscription.user.username} успешно активирована.', 'success')
    
    elif action == 'cancel':
        if subscription.status == 'cancelled':
            flash('Подписка уже отменена.', 'warning')
        else:
            # Отменяем подписку
            subscription.status = 'cancelled'
            subscription.admin_comment = request.form.get('admin_comment', '')
            
            db.session.commit()
            
            # Отправляем уведомление пользователю
            send_tariff_subscription_notification_user(subscription)
            
            flash(f'Подписка на тариф "{subscription.tariff.name}" для пользователя {subscription.user.username} отменена.', 'info')
    
    else:
        flash('Неизвестное действие', 'danger')
    
    return redirect(url_for('admin_panel.tariff_subscriptions'))

# Добавление новой категории
@bp.route('/categories/add', methods=['POST'])
@login_required
@admin_required
def add_category():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        # Валидация данных
        if not name:
            flash('Пожалуйста, укажите название категории', 'danger')
            return redirect(url_for('admin_panel.categories'))
        
        # Создаем новую категорию
        new_category = Category(
            name=name,
            description=description
        )
        # Загрузка изображения, если оно было отправлено
        if 'image' in request.files and request.files['image'].filename:
            # Здесь должна быть логика обработки изображения
            # Например, сохранение файла и установка пути в свойство image объекта Category
            pass
            
        # Сохраняем категорию в базу данных
        db.session.add(new_category)
        db.session.commit()
        
        flash('Категория успешно добавлена', 'success')
        return redirect(url_for('admin_panel.categories'))

# Редактирование категории
@bp.route('/categories/edit', methods=['POST'])
@login_required
@admin_required
def edit_category():
    if request.method == 'POST':
        category_id = request.form.get('id')
        category = Category.query.get_or_404(category_id)
        
        # Обновляем данные категории
        category.name = request.form.get('name')
        category.description = request.form.get('description')
          # Обработка изображения, если оно было изменено
        if 'image' in request.files and request.files['image'].filename:
            # Здесь должна быть логика обработки изображения
            pass
            
        # Сохраняем изменения
        db.session.commit()
        
        flash('Категория успешно обновлена', 'success')
        return redirect(url_for('admin_panel.categories'))

# Удаление категории
@bp.route('/categories/delete', methods=['POST'])
@login_required
@admin_required
def delete_category():
    if request.method == 'POST':
        category_id = request.form.get('id')
        category = Category.query.get_or_404(category_id)
        
        # Проверяем, есть ли товары в этой категории
        if category.products:
            flash('Нельзя удалить категорию, содержащую товары', 'danger')
            return redirect(url_for('admin_panel.categories'))
            
        # Удаляем категорию из базы данных
        db.session.delete(category)
        db.session.commit()
        
        flash('Категория успешно удалена', 'success')
        return redirect(url_for('admin_panel.categories'))

# Управление тарифами
@bp.route('/tariffs')
@login_required
@admin_required
def tariffs():
    tariffs = Tariff.query.all()
    return render_template('admin/tariffs.html', tariffs=tariffs)

# Управление заказами
@bp.route('/orders')
@login_required
@admin_required
def orders():
    from ..models import Order, User
    from sqlalchemy import or_
    
    # Параметры поиска и фильтрации
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Пагинация
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Количество заказов на странице
    
    # Начинаем формировать запрос
    query = Order.query
    
    # Применяем поиск по номеру заказа или данным пользователя
    if search_query:
        # Подзапрос для поиска пользователей
        user_subquery = User.query.filter(
            or_(
                User.first_name.ilike(f'%{search_query}%'),
                User.last_name.ilike(f'%{search_query}%'),
                User.email.ilike(f'%{search_query}%'),
                User.phone.ilike(f'%{search_query}%')
            )
        ).with_entities(User.id)
        
        # Объединяем условия поиска
        query = query.filter(
            or_(
                Order.id == search_query if search_query.isdigit() else False,
                Order.user_id.in_(user_subquery),
                Order.shipping_address.ilike(f'%{search_query}%'),
                Order.contact_phone.ilike(f'%{search_query}%'),
                Order.contact_email.ilike(f'%{search_query}%')
            )
        )
    
    # Применяем фильтр по статусу
    if status_filter:
        query = query.filter(Order.status == status_filter)
    
    # Применяем фильтры по дате
    from datetime import datetime
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Order.created_at >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            # Добавляем 23:59:59 чтобы включить весь день
            date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
            query = query.filter(Order.created_at <= date_to_obj)
        except ValueError:
            pass
    
    # Сортировка и пагинация
    orders_pagination = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=per_page)
    
    # Список всех возможных статусов для фильтра
    statuses = [
        {'code': 'new', 'name': 'Новый'},
        {'code': 'processing', 'name': 'В обработке'},
        {'code': 'shipped', 'name': 'Отправлен'},
        {'code': 'delivered', 'name': 'Доставлен'},
        {'code': 'cancelled', 'name': 'Отменён'}
    ]
    
    return render_template('admin/orders.html', 
                          orders=orders_pagination.items, 
                          pagination=orders_pagination,
                          search_query=search_query,
                          status_filter=status_filter,
                          date_from=date_from,
                          date_to=date_to,
                          statuses=statuses)

# Детальный просмотр заказа
@bp.route('/orders/<int:order_id>')
@login_required
@admin_required
def order_detail(order_id):
    """Детальная информация о заказе для администратора"""
    from ..models import Order, OrderItem
    order = Order.query.get_or_404(order_id)
    items = OrderItem.query.filter_by(order_id=order_id).all()
    
    return render_template('admin/order_detail.html', order=order, items=items)

# Обновление статуса заказа
@bp.route('/orders/update_status', methods=['POST'])
@login_required
@admin_required
def update_order_status():
    """Обновление статуса заказа администратором"""
    from ..models import Order
    from ..email import send_order_status_notification
    
    order_id = request.form.get('order_id')
    new_status = request.form.get('status')
    
    if not order_id or not new_status:
        flash('Не указан ID заказа или новый статус', 'danger')
        return redirect(url_for('admin_panel.orders'))
    
    order = Order.query.get_or_404(order_id)
    
    # Запоминаем старый статус для проверки изменений
    old_status = order.status
    
    # Если заказ отменяется, возвращаем товары на склад
    if order.status != 'cancelled' and new_status == 'cancelled':
        from ..models import OrderItem, Product
        order_items = OrderItem.query.filter_by(order_id=order_id).all()
        for item in order_items:
            product = Product.query.get(item.product_id)
            if product:
                product.stock += item.quantity
    
    # Обновляем статус
    order.status = new_status
    
    try:
        db.session.commit()
        
        # Если статус изменился, отправляем уведомление по email
        if old_status != new_status:
            try:
                send_order_status_notification(order)
                logger.info(f"Отправлено уведомление об изменении статуса заказа {order_id}")
            except Exception as email_error:
                logger.error(f"Ошибка при отправке уведомления о заказе {order_id}: {str(email_error)}")
        
        flash('Статус заказа успешно обновлен', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Ошибка при обновлении статуса заказа {order_id}: {str(e)}")
        flash('Произошла ошибка при обновлении статуса заказа.', 'danger')
    
    return redirect(url_for('admin_panel.order_detail', order_id=order_id))

# Управление пользователями
@bp.route('/users')
@login_required
@admin_required
def users():    # Получаем всех пользователей
    users = db.session.query(User).all()
    return render_template('admin/users.html', users=users)

# Редактирование пользователя
@bp.route('/users/edit', methods=['POST'])
@login_required
@admin_required
def edit_user():
    if request.method == 'POST':
        user_id = request.form.get('id')
        is_admin = True if request.form.get('is_admin') == '1' else False
        
        user = User.query.get_or_404(user_id)
        
        # Изменяем статус пользователя
        user.is_admin = is_admin
        
        try:
            # Используем функцию safe_db_operation для безопасного коммита
            def commit_operation():
                db.session.commit()
                return True
            
            result = safe_db_operation(commit_operation, False)
            
            if result:
                flash('Статус пользователя успешно обновлен', 'success')
            else:
                flash('Произошла ошибка при обновлении статуса пользователя. Попробуйте снова.', 'danger')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении статуса пользователя: {str(e)}', 'danger')
            logger.error(f"Ошибка при обновлении статуса пользователя: {str(e)}")
        
        return redirect(url_for('admin_panel.users'))

# Удаление пользователя
@bp.route('/users/delete', methods=['POST'])
@login_required
@admin_required
def delete_user():
    if request.method == 'POST':
        user_id = request.form.get('id')
        user = User.query.get_or_404(user_id)
        
        # Не позволяем удалять себя
        if int(user_id) == current_user.id:
            flash('Вы не можете удалить собственную учётную запись', 'danger')
            return redirect(url_for('admin_panel.users'))
        
        try:
            # Удаляем пользователя
            db.session.delete(user)
            
            # Используем функцию safe_db_operation для безопасного коммита
            def commit_operation():
                db.session.commit()
                return True
            
            result = safe_db_operation(commit_operation, False)
            
            if result:
                flash('Пользователь успешно удален', 'success')
            else:
                flash('Произошла ошибка при удалении пользователя. Попробуйте снова.', 'danger')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при удалении пользователя: {str(e)}', 'danger')
            logger.error(f"Ошибка при удалении пользователя: {str(e)}")
        
        return redirect(url_for('admin_panel.users'))

# Добавление нового товара
@bp.route('/products/add', methods=['POST'])
@login_required
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        category_id = request.form.get('category_id')
        price = request.form.get('price')
        stock = request.form.get('stock')
        description = request.form.get('description')
          # Валидация данных
        if not name or not category_id or not price:
            flash('Пожалуйста, заполните все обязательные поля', 'danger')
            return redirect(url_for('admin_panel.products'))
            
        # Создаем новый товар
        new_product = Product(
            name=name,
            category_id=category_id,
            price=float(price),
            stock=int(stock) if stock else 0,
            description=description
        )
          # Загрузка изображения, если оно было отправлено
        if 'image' in request.files and request.files['image'].filename:
            from werkzeug.utils import secure_filename
            import os
            
            # Получаем файл изображения
            file = request.files['image']
            
            # Определяем имя файла на основе названия товара
            # Используем secure_filename, чтобы избежать проблем с путями и спецсимволами
            filename = secure_filename(name + os.path.splitext(file.filename)[1])
            
            # Сохраняем файл в папку статических изображений
            file_path = os.path.join(bp.root_path, '..', 'static', 'img', 'products', filename)
            file.save(file_path)
            
            # Устанавливаем имя файла в атрибут image товара
            new_product.image = filename
            
        # Сохраняем товар в базу данных с обработкой ошибок
        try:
            db.session.add(new_product)
            
            # Используем функцию safe_db_operation для безопасного коммита
            def commit_operation():
                db.session.commit()
                return True
                
            result = safe_db_operation(commit_operation, False)
            
            if result:
                flash('Товар успешно добавлен', 'success')
            else:
                flash('Произошла ошибка при добавлении товара. Попробуйте снова.', 'danger')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении товара: {str(e)}', 'danger')
            logger.error(f"Ошибка при добавлении товара: {str(e)}")
            
        return redirect(url_for('admin_panel.products'))

# Редактирование товара
@bp.route('/products/edit', methods=['POST'])
@login_required
@admin_required
def edit_product():
    if request.method == 'POST':
        product_id = request.form.get('id')
        product = Product.query.get_or_404(product_id)
        
        # Обновляем данные товара        product.name = request.form.get('name')
        product.category_id = request.form.get('category_id')
        product.price = float(request.form.get('price'))
        product.stock = int(request.form.get('stock')) if request.form.get('stock') else 0
        product.description = request.form.get('description')
        # Обработка изображения, если оно было изменено
        if 'image' in request.files and request.files['image'].filename:
            from werkzeug.utils import secure_filename
            import os
            
            # Получаем файл изображения
            file = request.files['image']
            
            # Определяем имя файла на основе названия товара
            # Используем secure_filename, чтобы избежать проблем с путями и спецсимволами
            filename = secure_filename(product.name + os.path.splitext(file.filename)[1])
            
            # Если у товара уже было изображение, и оно не совпадает с новым именем,
            # удаляем старый файл, чтобы избежать накопления лишних файлов
            if product.image and product.image != filename:
                old_file_path = os.path.join(bp.root_path, '..', 'static', 'img', 'products', product.image)
                try:
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                except Exception as e:
                    logger.warning(f"Не удалось удалить старое изображение: {str(e)}")
            
            # Сохраняем файл в папку статических изображений
            file_path = os.path.join(bp.root_path, '..', 'static', 'img', 'products', filename)
            file.save(file_path)
            
            # Устанавливаем имя файла в атрибут image товара
            product.image = filename
            
        # Сохраняем изменения с обработкой ошибок
        try:
            # Используем функцию safe_db_operation для безопасного коммита
            def commit_operation():
                db.session.commit()
                return True
                
            result = safe_db_operation(commit_operation, False)
            
            if result:
                flash('Товар успешно обновлен', 'success')
            else:
                flash('Произошла ошибка при обновлении товара. Попробуйте снова.', 'danger')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении товара: {str(e)}', 'danger')
            logger.error(f"Ошибка при обновлении товара: {str(e)}")
        
        return redirect(url_for('admin_panel.products'))

# Удаление товара
@bp.route('/products/delete', methods=['POST'])
@login_required
@admin_required
def delete_product():
    if request.method == 'POST':
        product_id = request.form.get('id')
        product = Product.query.get_or_404(product_id)
        
        # Удаляем товар из базы данных с обработкой ошибок
        try:
            db.session.delete(product)
            
            # Используем функцию safe_db_operation для безопасного коммита
            def commit_operation():
                db.session.commit()
                return True
                
            result = safe_db_operation(commit_operation, False)
            
            if not result:
                flash('Произошла ошибка при удалении товара. Попробуйте снова.', 'danger')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при удалении товара: {str(e)}', 'danger')
            logger.error(f"Ошибка при удалении товара: {str(e)}")
        
        flash('Товар успешно удален', 'success')
        return redirect(url_for('admin_panel.products'))

# Добавление нового тарифа
@bp.route('/tariffs/add', methods=['POST'])
@login_required
@admin_required
def add_tariff():
    if request.method == 'POST':
        name = request.form.get('name')
        tariff_type = request.form.get('type')
        price = request.form.get('price')
        is_active = True if request.form.get('is_active') else False
        description = request.form.get('description')
        features = request.form.get('features')
        
        # Валидация данных
        if not name or not price:
            flash('Пожалуйста, заполните все обязательные поля', 'danger')
            return redirect(url_for('admin_panel.tariffs'))
          # Создаем новый тариф
        new_tariff = Tariff(
            name=name,
            period=tariff_type,  # Используем type как период
            price=float(price),
            description=description,
            features=features,
            is_active=is_active
        )
          # Сохраняем тариф в базу данных с обработкой ошибок
        try:
            db.session.add(new_tariff)
            
            # Используем функцию safe_db_operation для безопасного коммита
            def commit_operation():
                db.session.commit()
                return True
                
            result = safe_db_operation(commit_operation, False)
            
            if result:
                flash('Тариф успешно добавлен', 'success')
            else:
                flash('Произошла ошибка при добавлении тарифа. Попробуйте снова.', 'danger')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении тарифа: {str(e)}', 'danger')
            logger.error(f"Ошибка при добавлении тарифа: {str(e)}")
            
        return redirect(url_for('admin_panel.tariffs'))

# Редактирование тарифа
@bp.route('/tariffs/edit', methods=['POST'])
@login_required
@admin_required
def edit_tariff():
    if request.method == 'POST':
        tariff_id = request.form.get('id')
        tariff = Tariff.query.get_or_404(tariff_id)
        
    # Обновляем данные тарифа
        tariff.name = request.form.get('name')
        tariff.period = request.form.get('type')  # Используем type как период
        tariff.price = float(request.form.get('price'))
        tariff.description = request.form.get('description')
        tariff.features = request.form.get('features')
        tariff.is_active = True if request.form.get('is_active') else False
          # Сохраняем изменения с обработкой ошибок
        try:
            # Используем функцию safe_db_operation для безопасного коммита
            def commit_operation():
                db.session.commit()
                return True
                
            result = safe_db_operation(commit_operation, False)
            
            if result:
                flash('Тариф успешно обновлен', 'success')
            else:
                flash('Произошла ошибка при обновлении тарифа. Попробуйте снова.', 'danger')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении тарифа: {str(e)}', 'danger')
            logger.error(f"Ошибка при обновлении тарифа: {str(e)}")
            
        return redirect(url_for('admin_panel.tariffs'))

# Удаление тарифа
@bp.route('/tariffs/delete', methods=['POST'])
@login_required
@admin_required
def delete_tariff():
    if request.method == 'POST':
        tariff_id = request.form.get('id')
        tariff = Tariff.query.get_or_404(tariff_id)
          # Удаляем тариф из базы данных с обработкой ошибок
        try:
            db.session.delete(tariff)
            
            # Используем функцию safe_db_operation для безопасного коммита
            def commit_operation():
                db.session.commit()
                return True
                
            result = safe_db_operation(commit_operation, False)
            
            if result:
                flash('Тариф успешно удален', 'success')
            else:
                flash('Произошла ошибка при удалении тарифа. Попробуйте снова.', 'danger')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при удалении тарифа: {str(e)}', 'danger')
            logger.error(f"Ошибка при удалении тарифа: {str(e)}")
            
        return redirect(url_for('admin_panel.tariffs'))

# Добавление новой услуги
@bp.route('/services/add', methods=['POST'])
@login_required
@admin_required
def add_service():
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        duration = request.form.get('duration')
        category = request.form.get('category')
        description = request.form.get('description')
        
        # Валидация данных
        if not name or not price:
            flash('Пожалуйста, заполните все обязательные поля', 'danger')
            return redirect(url_for('admin_panel.services'))
        
        # Создаем новую услугу
        new_service = Service(
            name=name,
            price=float(price),
            duration=duration,
            description=description,
            category=category
        )
        
        # Сохраняем услугу в базу данных с обработкой ошибок
        try:
            db.session.add(new_service)
            
            # Используем функцию safe_db_operation для безопасного коммита
            def commit_operation():
                db.session.commit()
                return True
                
            result = safe_db_operation(commit_operation, False)
            
            if result:
                flash('Услуга успешно добавлена', 'success')
            else:
                flash('Произошла ошибка при добавлении услуги. Попробуйте снова.', 'danger')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении услуги: {str(e)}', 'danger')
            logger.error(f"Ошибка при добавлении услуги: {str(e)}")
            
        return redirect(url_for('admin_panel.services'))

# Редактирование услуги
@bp.route('/services/edit', methods=['POST'])
@login_required
@admin_required
def edit_service():
    if request.method == 'POST':
        service_id = request.form.get('id')
        service = Service.query.get_or_404(service_id)
        
        # Обновляем данные услуги
        service.name = request.form.get('name')
        service.price = float(request.form.get('price'))
        service.duration = request.form.get('duration')
        service.description = request.form.get('description')
        service.category = request.form.get('category')
        
        # Сохраняем изменения с обработкой ошибок
        try:
            # Используем функцию safe_db_operation для безопасного коммита
            def commit_operation():
                db.session.commit()
                return True
                
            result = safe_db_operation(commit_operation, False)
            
            if result:
                flash('Услуга успешно обновлена', 'success')
            else:
                flash('Произошла ошибка при обновлении услуги. Попробуйте снова.', 'danger')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении услуги: {str(e)}', 'danger')
            logger.error(f"Ошибка при обновлении услуги: {str(e)}")
            
        return redirect(url_for('admin_panel.services'))

# Удаление услуги
@bp.route('/services/delete', methods=['POST'])
@login_required
@admin_required
def delete_service():
    if request.method == 'POST':
        service_id = request.form.get('id')
        service = Service.query.get_or_404(service_id)
        
        try:
            db.session.delete(service)
            
            # Используем функцию safe_db_operation для безопасного коммита
            def commit_operation():
                db.session.commit()
                return True
                
            result = safe_db_operation(commit_operation, False)
            
            if result:
                flash('Услуга успешно удалена', 'success')
            else:
                flash('Произошла ошибка при удалении услуги. Попробуйте снова.', 'danger')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при удалении услуги: {str(e)}', 'danger')
            logger.error(f"Ошибка при удалении услуги: {str(e)}")
            
        return redirect(url_for('admin_panel.services'))

# Страница управления услугами
@bp.route('/services')
@login_required
@admin_required
def services():
    services = Service.query.all()
    return render_template('admin/services.html', services=services)
