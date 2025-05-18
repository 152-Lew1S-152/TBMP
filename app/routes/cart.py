from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from ..models import db, Product, CartItem, Order, OrderItem

bp = Blueprint('cart', __name__, url_prefix='/cart')

@bp.route('/')
def view_cart():
    """Просмотр корзины"""
    if current_user.is_authenticated:
        # Для авторизованных пользователей берем корзину из БД
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        items = []
        total = 0
        
        for item in cart_items:
            product = Product.query.get(item.product_id)
            if product:
                subtotal = product.price * item.quantity
                items.append({
                    'id': item.id,
                    'product': product,
                    'quantity': item.quantity,
                    'subtotal': subtotal
                })
                total += subtotal
    else:
        # Для неавторизованных пользователей используем сессию
        cart = session.get('cart', {})
        items = []
        total = 0
        
        for product_id, quantity in cart.items():
            product = Product.query.get(int(product_id))
            if product:
                subtotal = product.price * quantity
                items.append({
                    'product': product,
                    'quantity': quantity,
                    'subtotal': subtotal
                })
                total += subtotal
    
    return render_template('cart/cart.html', items=items, total=total)

@bp.route('/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    """Добавление товара в корзину"""
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))
    
    if product.stock < quantity:
        flash('Извините, нет достаточного количества товара на складе', 'danger')
        return redirect(url_for('catalog.product_detail', product_id=product_id))
    
    if current_user.is_authenticated:
        # Для авторизованных пользователей сохраняем в БД
        cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
        
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
            db.session.add(cart_item)
            
        db.session.commit()
    else:
        # Для неавторизованных пользователей сохраняем в сессии
        cart = session.get('cart', {})
        product_id_str = str(product_id)
        
        if product_id_str in cart:
            cart[product_id_str] += quantity
        else:
            cart[product_id_str] = quantity
            
        session['cart'] = cart
    
    flash(f'Товар "{product.name}" добавлен в корзину', 'success')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'success'})
    
    return redirect(url_for('cart.view_cart'))

@bp.route('/update/<int:item_id>', methods=['POST'])
def update_cart(item_id):
    """Обновление количества товара в корзине"""
    quantity = int(request.form.get('quantity', 1))
    
    if current_user.is_authenticated:
        cart_item = CartItem.query.get_or_404(item_id)
        
        if cart_item.user_id != current_user.id:
            flash('Доступ запрещен', 'danger')
            return redirect(url_for('cart.view_cart'))
            
        product = Product.query.get(cart_item.product_id)
        
        if product.stock < quantity:
            flash('Извините, нет достаточного количества товара на складе', 'danger')
            return redirect(url_for('cart.view_cart'))
            
        cart_item.quantity = quantity
        db.session.commit()
    else:
        # В этом случае item_id это product_id
        cart = session.get('cart', {})
        product_id_str = str(item_id)
        
        if product_id_str in cart:
            product = Product.query.get(item_id)
            
            if product.stock < quantity:
                flash('Извините, нет достаточного количества товара на складе', 'danger')
                return redirect(url_for('cart.view_cart'))
                
            cart[product_id_str] = quantity
            session['cart'] = cart
    
    return redirect(url_for('cart.view_cart'))

@bp.route('/remove/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    """Удаление товара из корзины"""
    if current_user.is_authenticated:
        cart_item = CartItem.query.get_or_404(item_id)
        
        if cart_item.user_id != current_user.id:
            flash('Доступ запрещен', 'danger')
            return redirect(url_for('cart.view_cart'))
            
        db.session.delete(cart_item)
        db.session.commit()
    else:
        # В этом случае item_id это product_id
        cart = session.get('cart', {})
        product_id_str = str(item_id)
        
        if product_id_str in cart:
            del cart[product_id_str]
            session['cart'] = cart
            
    return redirect(url_for('cart.view_cart'))

@bp.route('/update_session/<int:product_id>', methods=['POST'])
def update_cart_session(product_id):
    """Обновление количества товара в корзине для неаутентифицированных пользователей"""
    quantity = int(request.form.get('quantity', 1))
    
    # Проверяем наличие товара
    product = Product.query.get_or_404(product_id)
    
    if product.stock < quantity:
        flash('Извините, нет достаточного количества товара на складе', 'danger')
        return redirect(url_for('cart.view_cart'))
    
    # Обновляем корзину в сессии
    cart = session.get('cart', {})
    product_id_str = str(product_id)
    
    if product_id_str in cart:
        cart[product_id_str] = quantity
        session['cart'] = cart
    
    return redirect(url_for('cart.view_cart'))

@bp.route('/remove_session/<int:product_id>', methods=['POST'])
def remove_from_cart_session(product_id):
    """Удаление товара из корзины для неаутентифицированных пользователей"""
    # Удаляем товар из корзины в сессии
    cart = session.get('cart', {})
    product_id_str = str(product_id)
    
    if product_id_str in cart:
        del cart[product_id_str]
        session['cart'] = cart
            
    return redirect(url_for('cart.view_cart'))

@bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """Оформление заказа"""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    if not cart_items:
        flash('Ваша корзина пуста', 'info')
        return redirect(url_for('cart.view_cart'))
    
    total = 0
    items = []
    
    for item in cart_items:
        product = Product.query.get(item.product_id)
        if product:
            subtotal = product.price * item.quantity
            items.append({
                'id': item.id,
                'product': product,
                'quantity': item.quantity,
                'subtotal': subtotal
            })
            total += subtotal
    
    if request.method == 'POST':
        shipping_address = request.form.get('shipping_address')
        
        # Создаем новый заказ
        order = Order(
            user_id=current_user.id,
            shipping_address=shipping_address,
            total_price=total,
            status='pending'
        )
        db.session.add(order)
        db.session.flush()  # Чтобы получить order.id
        
        # Добавляем элементы заказа
        for item in cart_items:
            product = Product.query.get(item.product_id)
            if product:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    price=product.price
                )
                db.session.add(order_item)
                
                # Уменьшаем количество товара на складе
                product.stock -= item.quantity
                
        # Очищаем корзину
        for item in cart_items:
            db.session.delete(item)
            
        db.session.commit()
        
        flash('Заказ успешно оформлен', 'success')
        return redirect(url_for('auth.order_detail', order_id=order.id))
    
    return render_template('cart/checkout.html', items=items, total=total)

@bp.route('/apply_promo', methods=['POST'])
def apply_promo():
    """Применение промокода к корзине"""
    promo_code = request.form.get('promo_code', '')
    
    # Здесь будет логика проверки промокода
    # Проверяем, существует ли такой промокод и действителен ли он
    # Пока просто заглушка
    
    if promo_code.strip():
        # Временная заглушка для демо
        flash('Промокод применен! Скидка 10%', 'success')
    else:
        flash('Пожалуйста, введите промокод', 'warning')
    
    return redirect(url_for('cart.view_cart'))

@bp.route('/place_order', methods=['POST'])
@login_required
def place_order():
    """Оформление и сохранение заказа"""
    if not current_user.is_authenticated:
        flash('Пожалуйста, войдите в систему', 'warning')
        return redirect(url_for('auth.login'))
    
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    if not cart_items:
        flash('Ваша корзина пуста', 'warning')
        return redirect(url_for('cart.view_cart'))
    
    # Рассчитываем общую стоимость
    total = 0
    for item in cart_items:
        product = Product.query.get(item.product_id)
        if product:
            total += product.price * item.quantity
    
    # Получаем данные из формы
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    shipping_method = request.form.get('shipping_method')
    payment_method = request.form.get('payment_method')
    notes = request.form.get('notes')
    
    # Определяем адрес доставки в зависимости от способа доставки
    if shipping_method == 'courier':
        shipping_address = request.form.get('address')
        # Добавляем стоимость доставки
        total += 300  # Стоимость курьерской доставки 300 рублей
    else:
        pickup_point_id = request.form.get('pickup_point')
        pickup_points = {            '1': 'Офис TBMP - ул. Ленина, 12',
            '2': 'Офис TBMP - пр. Гагарина, 24',
            '3': 'Офис TBMP - ул. Белинского, 63',
            '4': 'Офис TBMP - ул. Коминтерна, 105',
            '5': 'Офис TBMP - ул. Бекетова, 13'
        }
        shipping_address = pickup_points.get(pickup_point_id, 'Самовывоз')
    
    # Обновляем данные пользователя, если они изменились
    if first_name and first_name != current_user.first_name:
        current_user.first_name = first_name
    
    if last_name and last_name != current_user.last_name:
        current_user.last_name = last_name
    
    if phone and phone != current_user.phone:
        current_user.phone = phone
    
    if shipping_method == 'courier' and shipping_address and shipping_address != current_user.address:
        current_user.address = shipping_address
    
    # Создаем новый заказ
    order = Order(
        user_id=current_user.id,
        shipping_address=shipping_address,
        shipping_method=shipping_method,
        payment_method=payment_method,
        contact_phone=phone,
        contact_email=email,
        notes=notes,
        total_price=total,
        status='new'
    )
    
    db.session.add(order)
    db.session.flush()  # Чтобы получить order.id
    
    # Добавляем товары в заказ
    for item in cart_items:
        product = Product.query.get(item.product_id)
        if product:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=product.price
            )
            db.session.add(order_item)
            
            # Уменьшаем количество товара на складе
            if product.stock >= item.quantity:
                product.stock -= item.quantity
      # Очищаем корзину пользователя
    for item in cart_items:
        db.session.delete(item)
    
    try:
        db.session.commit()
        flash('Заказ успешно оформлен! Номер вашего заказа: ' + str(order.id), 'success')
        return redirect(url_for('cart.order_success', order_id=order.id))
    except Exception as e:
        db.session.rollback()
        # Логируем ошибку для отладки
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при оформлении заказа: {str(e)}")
        
        flash('Произошла ошибка при оформлении заказа. Пожалуйста, попробуйте снова.', 'danger')
        return redirect(url_for('cart.checkout'))

@bp.route('/order/success/<int:order_id>')
@login_required
def order_success(order_id):
    """Страница успешного оформления заказа"""
    order = Order.query.get_or_404(order_id)
    
    # Проверяем, что заказ принадлежит текущему пользователю
    if order.user_id != current_user.id:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('auth.profile'))
    
    items = OrderItem.query.filter_by(order_id=order_id).all()
    order_products = []
    
    for item in items:
        product = Product.query.get(item.product_id)
        if product:
            order_products.append({
                'product': product,
                'quantity': item.quantity,
                'price': item.price,
                'subtotal': item.price * item.quantity
            })
    
    return render_template('cart/order_success.html', order=order, items=order_products)
