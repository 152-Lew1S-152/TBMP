#!/usr/bin/env python
"""
Тестовый скрипт для проверки функциональности администраторской панели управления заказами.
"""

import os
import sys
import unittest
from app import create_app
from app.models import db, User, Product, Category, Order, OrderItem

class AdminOrdersTestCase(unittest.TestCase):
    """Класс для тестирования администраторского интерфейса управления заказами."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_admin_orders.sqlite'
        self.app.config['WTF_CSRF_ENABLED'] = False  # Отключаем CSRF для тестов
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            
            # Создаем администратора
            admin = User(
                username='admin',
                email='admin@example.com',
                first_name='Admin',
                last_name='User',
                is_admin=True
            )
            admin.set_password('adminpassword')
            db.session.add(admin)
            
            # Создаем обычного пользователя
            user = User(
                username='user',
                email='user@example.com',
                first_name='Normal',
                last_name='User'
            )
            user.set_password('userpassword')
            db.session.add(user)
            
            # Создаем категорию и товары
            category = Category(name='Test Category')
            db.session.add(category)
            db.session.flush()
            
            product = Product(
                name='Test Product',
                price=100.0,
                stock=10,
                category_id=category.id
            )
            db.session.add(product)
            db.session.flush()
            
            # Создаем заказ
            order = Order(
                user_id=user.id,
                shipping_address='Test Address',
                shipping_method='courier',
                payment_method='card',
                contact_phone='1234567890',
                contact_email='user@example.com',
                total_price=100.0,
                status='new'
            )
            db.session.add(order)
            db.session.flush()
            
            # Добавляем товар в заказ
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=1,
                price=100.0
            )
            db.session.add(order_item)
            db.session.commit()
    
    def tearDown(self):
        """Очистка после тестов."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def login_as_admin(self):
        """Вход администратора в систему."""
        return self.client.post('/auth/login', data={
            'username': 'admin',
            'password': 'adminpassword'
        }, follow_redirects=True)
    
    def login_as_user(self):
        """Вход обычного пользователя в систему."""
        return self.client.post('/auth/login', data={
            'username': 'user',
            'password': 'userpassword'
        }, follow_redirects=True)
    
    def test_admin_orders_list_access(self):
        """Тест доступа к списку заказов."""
        # Незалогиненный пользователь должен быть перенаправлен
        response = self.client.get('/admin/orders')
        self.assertEqual(response.status_code, 302)  # Редирект на страницу входа
        
        # Обычный пользователь не должен иметь доступа
        self.login_as_user()
        response = self.client.get('/admin/orders')
        self.assertEqual(response.status_code, 403)  # Запрещено
        
        # Администратор должен иметь доступ
        self.login_as_admin()
        response = self.client.get('/admin/orders')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Управление заказами', response.data)
    
    def test_admin_order_detail(self):
        """Тест просмотра деталей заказа."""
        self.login_as_admin()
        
        response = self.client.get('/admin/orders/1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Address', response.data)  # Адрес доставки
        self.assertIn(b'Test Product', response.data)  # Название товара
    
    def test_update_order_status(self):
        """Тест обновления статуса заказа."""
        self.login_as_admin()
        
        # Проверяем, что статус изначально 'new'
        with self.app.app_context():
            order = Order.query.get(1)
            self.assertEqual(order.status, 'new')
        
        # Меняем статус на 'processing'
        response = self.client.post('/admin/orders/update_status', data={
            'order_id': 1,
            'status': 'processing'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Статус заказа успешно обновлен', response.data)
        
        # Проверяем, что статус изменился
        with self.app.app_context():
            order = Order.query.get(1)
            self.assertEqual(order.status, 'processing')
    
    def test_cancel_order(self):
        """Тест отмены заказа."""
        self.login_as_admin()
        
        # Проверяем начальное количество товара
        with self.app.app_context():
            product = Product.query.get(1)
            initial_stock = product.stock
            self.assertEqual(initial_stock, 10)
        
        # Отменяем заказ
        response = self.client.post('/admin/orders/update_status', data={
            'order_id': 1,
            'status': 'cancelled'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Статус заказа успешно обновлен', response.data)
        
        # Проверяем, что товар вернулся на склад
        with self.app.app_context():
            product = Product.query.get(1)
            self.assertEqual(product.stock, initial_stock + 1)  # 10 + 1 = 11
            
            order = Order.query.get(1)
            self.assertEqual(order.status, 'cancelled')

if __name__ == '__main__':
    unittest.main()
