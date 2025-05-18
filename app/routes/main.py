from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from ..models import db, Product, Category

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Главная страница"""
    # Получаем популярные продукты для отображения на главной странице
    featured_products = Product.query.order_by(Product.created_at.desc()).limit(6).all()
    categories = Category.query.all()
    
    return render_template('main/index.html', 
                           featured_products=featured_products,
                           categories=categories)

@bp.route('/about')
def about():
    """О компании"""
    return render_template('main/about.html')

@bp.route('/contacts')
def contacts():
    """Контактная информация"""
    return render_template('main/contacts.html')

@bp.route('/search')
def search():
    """Поиск по сайту"""
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('main.index'))
    
    products = Product.query.filter(Product.name.ilike(f'%{query}%')).all()
    
    return render_template('main/search_results.html', 
                           products=products,
                           query=query)
