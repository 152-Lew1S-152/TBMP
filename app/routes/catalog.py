from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from ..models import db, Product, Category
from werkzeug.utils import secure_filename
import os

bp = Blueprint('catalog', __name__, url_prefix='/catalog')

@bp.route('/')
def index():
    """Страница каталога товаров"""
    categories = Category.query.all()
    # Получаем популярные товары из всех категорий
    featured_products = Product.query.order_by(Product.price.desc()).limit(8).all()
    return render_template('catalog/index.html', categories=categories, featured_products=featured_products)

@bp.route('/category/<int:category_id>')
def category(category_id):
    """Страница категории с товарами"""
    category = Category.query.get_or_404(category_id)
    page = request.args.get('page', 1, type=int)
    per_page = 12  # товаров на страницу
    
    # Базовый запрос
    query = Product.query.filter_by(category_id=category_id)
    
    # Применяем фильтры    # 1. Фильтр по бренду
    brand_filter = request.args.getlist('brand')
    if brand_filter:
        query = query.filter(Product.brand.in_(brand_filter))
    
    # 2. Фильтр по цене
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)    # 3. Фильтр по памяти (для смартфонов и планшетов)
    category = Category.query.get_or_404(category_id)
    memory_filter = request.args.get('memory', type=int)
    if memory_filter and (category.name == 'Смартфоны' or category.name == 'Планшеты'):
        query = query.filter(Product.memory == memory_filter)
    
    # 4. Фильтр по наличию
    availability = request.args.get('availability')
    if availability == 'in_stock':
        query = query.filter(Product.stock > 0)
        
    # Получаем доступные значения памяти для этой категории (если это смартфоны или планшеты)
    memory_options = []
    if category.name == 'Смартфоны' or category.name == 'Планшеты':
        memory_values = db.session.query(Product.memory).filter(
            Product.category_id == category_id,
            Product.memory.isnot(None)
        ).distinct().order_by(Product.memory).all()
        memory_options = [mem[0] for mem in memory_values if mem[0] is not None]
      # Получаем все бренды в текущей категории для фильтра
    all_products = Product.query.filter_by(category_id=category_id).all()
    brands = {}
    for product in all_products:
        # Используем поле brand если оно заполнено, иначе берем первое слово из названия
        brand = product.brand if product.brand else product.name.split()[0]
        if brand in brands:
            brands[brand] += 1
        else:
            brands[brand] = 1
    
    # Сортировка
    sort = request.args.get('sort', 'popularity')
    if sort == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Product.price.desc())
    elif sort == 'name_asc':
        query = query.order_by(Product.name.asc())
    elif sort == 'name_desc':
        query = query.order_by(Product.name.desc())
    
    # Пагинация
    products = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Определяем минимальную и максимальную цену товаров в категории
    price_range = db.session.query(
        db.func.min(Product.price).label('min_price'),
        db.func.max(Product.price).label('max_price')
    ).filter(Product.category_id == category_id).first()
    
    min_category_price = int(price_range.min_price) if price_range.min_price else 0
    max_category_price = int(price_range.max_price) if price_range.max_price else 100000
    
    # Если не установлены параметры цены в запросе, используем мин и макс из категории
    if min_price is None:
        min_price = min_category_price
    if max_price is None:
        max_price = max_category_price
      # Передаем информацию о доступных опциях памяти
    return render_template('catalog/category.html', 
                           category=category,
                           products=products,
                           brands=brands,
                           min_price=min_price,
                           max_price=max_price,
                           min_category_price=min_category_price,
                           max_category_price=max_category_price,
                           selected_brands=brand_filter,
                           memory_options=memory_options,
                           selected_memory=memory_filter)

@bp.route('/product/<int:product_id>')
def product_detail(product_id):
    """Детальная страница товара"""
    product = Product.query.get_or_404(product_id)
    related_products = Product.query.filter_by(category_id=product.category_id).filter(Product.id != product_id).limit(4).all()
    
    return render_template('catalog/product_detail.html', 
                           product=product,
                           related_products=related_products)

@bp.route('/sale')
def sale():
    """Страница с акционными товарами"""
    # Здесь можно реализовать логику выбора товаров со скидками
    sale_products = Product.query.order_by(Product.price).limit(8).all()
    
    return render_template('catalog/sale.html', products=sale_products)
