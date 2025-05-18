from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from flask_login import login_user, logout_user, login_required, current_user
from ..models import db, User, Order, OrderItem, Product
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET', 'POST'))
def register():
    """Регистрация нового пользователя"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        error = None
        
        if not username:
            error = 'Имя пользователя обязательно'
        elif not email:
            error = 'Email обязателен'
        elif not password:
            error = 'Пароль обязателен'
        elif password != password_confirm:
            error = 'Пароли не совпадают'
        elif User.query.filter_by(username=username).first() is not None:
            error = 'Пользователь {} уже зарегистрирован'.format(username)
        elif User.query.filter_by(email=email).first() is not None:
            error = 'Email {} уже используется'.format(email)
            
        if error is None:
            new_user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                address=address
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
            return redirect(url_for('auth.login'))
            
        flash(error, 'danger')
            
    return render_template('auth/register.html')

@bp.route('/login', methods=('GET', 'POST'))
def login():
    """Вход в личный кабинет"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        error = None
        user = User.query.filter_by(username=username).first()
        
        if user is None:
            error = 'Неверное имя пользователя'
        elif not user.check_password(password):
            error = 'Неверный пароль'
            
        if error is None:
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash('Вы успешно вошли в систему!', 'success')
            
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.index'))
            
        flash(error, 'danger')
            
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('main.index'))

@bp.route('/profile')
@login_required
def profile():
    """Профиль пользователя"""
    # Пагинация
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Количество заказов на странице
    
    # Получаем заказы с пагинацией
    orders_pagination = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('auth/profile.html', orders=orders_pagination.items, pagination=orders_pagination)

@bp.route('/profile/edit', methods=('GET', 'POST'))
@login_required
def edit_profile():
    """Редактирование профиля"""
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.phone = request.form.get('phone')
        current_user.address = request.form.get('address')
        
        email = request.form.get('email')
        if email != current_user.email:
            if User.query.filter_by(email=email).first() is not None:
                flash('Этот email уже используется', 'danger')
                return render_template('auth/edit_profile.html')
            current_user.email = email
            
        password = request.form.get('password')
        if password:
            current_user.set_password(password)
            
        db.session.commit()
        flash('Профиль успешно обновлен', 'success')
        return redirect(url_for('auth.profile'))
        
    return render_template('auth/edit_profile.html')

@bp.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    """Детальная информация о заказе"""
    order = Order.query.get_or_404(order_id)
    
    # Проверяем, что заказ принадлежит текущему пользователю
    if order.user_id != current_user.id:
        abort(403)
        
    items = OrderItem.query.filter_by(order_id=order_id).all()
    
    return render_template('auth/order_detail.html', order=order, items=items)

@bp.route('/order/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    """Отмена заказа"""
    from datetime import datetime
    
    order = Order.query.get_or_404(order_id)
    success = False
    
    # Проверяем, что заказ принадлежит текущему пользователю
    if order.user_id != current_user.id:
        abort(403)
    
    # Проверяем, что заказ можно отменить (только новые или в обработке)
    if order.status not in ['new', 'processing']:
        flash('Заказ не может быть отменен, так как он уже отправлен или доставлен.', 'danger')
        return redirect(url_for('auth.order_detail', order_id=order_id))
    
    # Возвращаем товары в наличие
    order_items = OrderItem.query.filter_by(order_id=order_id).all()
    for item in order_items:
        product = Product.query.get(item.product_id)
        if product:
            product.stock += item.quantity
    
    # Меняем статус заказа на "отменен"
    order.status = 'cancelled'
    
    # Добавляем поле updated_at если его нет
    if hasattr(order, 'updated_at'):
        order.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        success = True
        
        # Отправка уведомления по электронной почте, если email настроен
        try:
            from ..email import send_order_status_notification
            send_order_status_notification(order)
        except Exception as email_error:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка при отправке уведомления о заказе {order_id}: {str(email_error)}")
    except Exception as e:
        db.session.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при отмене заказа {order_id}: {str(e)}")
    
    # Рендерим страницу с результатом
    return render_template('auth/order_cancelled.html', 
                          order=order, 
                          success=success, 
                          now=datetime.utcnow())
