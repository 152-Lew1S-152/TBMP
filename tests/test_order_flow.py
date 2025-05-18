#!/usr/bin/env python
"""
Тестовый скрипт для проверки полного цикла заказа.
Этот скрипт создает тестового пользователя, добавляет товары в его корзину,
оформляет заказ и проверяет различные операции с заказом.
"""

import os
import sys
import unittest
from app import create_app
from app.models import db, User, Product, Category, CartItem, Order, OrderItem

class OrderFlowTestCase(unittest.TestCase):
    """Класс для тестирования полного процесса оформления заказа."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_telecom_site.sqlite'
        self.app.config['WTF_CSRF_ENABLED'] = False  # Отключаем CSRF для тестов
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            
            # Создаем тестового пользователя
            user = User(
                username='testuser',
                email='test@example.com',
                first_name='Test',
                last_name='User',
                phone='1234567890',
                address='Test Address'
            )
            user.set_password('testpassword')
            db.session.add(user)
            
            # Создаем тестовую категорию
            category = Category(name='Test Category', description='Test Description')
            db.session.add(category)
            db.session.commit()
            
            # Создаем тестовые товары
            product1 = Product(
                name='Test Product 1',
                description='Test Description 1',
                price=100.0,
                stock=10,
                category_id=category.id
            )
            product2 = Product(
                name='Test Product 2',
                description='Test Description 2',
                price=200.0,
                stock=5,
                category_id=category.id
            )
            db.session.add_all([product1, product2])
            db.session.commit()
    
    def tearDown(self):
        """Очистка после тестов."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def login(self):
        """Вход пользователя в систему."""
        return self.client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpassword'
        }, follow_redirects=True)
    
    def test_full_order_flow(self):
        """Тестирование полного цикла заказа."""
        
        # Шаг 1: Вход пользователя
        response = self.login()
        self.assertIn(b'успешно вошли', response.data)
        
        # Шаг 2: Добавление товаров в корзину
        with self.app.app_context():
            product1 = Product.query.filter_by(name='Test Product 1').first()
            product2 = Product.query.filter_by(name='Test Product 2').first()
            
            response = self.client.post(f'/cart/add/{product1.id}', data={
                'quantity': 2
            }, follow_redirects=True)
            self.assertIn(b'добавлен в корзину', response.data)
            
            response = self.client.post(f'/cart/add/{product2.id}', data={
                'quantity': 1
            }, follow_redirects=True)
            self.assertIn(b'добавлен в корзину', response.data)
            
            # Проверяем содержимое корзины
            user = User.query.filter_by(username='testuser').first()
            cart_items = CartItem.query.filter_by(user_id=user.id).all()
            self.assertEqual(len(cart_items), 2)
            
            total_price = sum(item.product.price * item.quantity for item in cart_items)
            self.assertEqual(total_price, 400.0)  # 2 * 100 + 1 * 200
        
        # Шаг 3: Оформление заказа
        response = self.client.post('/cart/place_order', data={
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'phone': '1234567890',
            'shipping_method': 'courier',
            'address': 'Test Address',
            'payment_method': 'card',
            'notes': 'Test notes'
        }, follow_redirects=True)
        
        self.assertIn(b'Заказ успешно оформлен', response.data)
        
        # Шаг 4: Проверка созданного заказа
        with self.app.app_context():
            user = User.query.filter_by(username='testuser').first()
            order = Order.query.filter_by(user_id=user.id).first()
            
            self.assertIsNotNone(order)
            self.assertEqual(order.shipping_method, 'courier')
            self.assertEqual(order.shipping_address, 'Test Address')
            self.assertEqual(order.payment_method, 'card')
            self.assertEqual(order.notes, 'Test notes')
            
            # С учетом стоимости доставки (300 рублей)
            self.assertEqual(order.total_price, 700.0)  # 400 + 300
            
            # Проверяем товары в заказе
            order_items = OrderItem.query.filter_by(order_id=order.id).all()
            self.assertEqual(len(order_items), 2)
            
            # Проверяем, что склад обновился
            product1 = Product.query.filter_by(name='Test Product 1').first()
            product2 = Product.query.filter_by(name='Test Product 2').first()
            self.assertEqual(product1.stock, 8)  # 10 - 2
            self.assertEqual(product2.stock, 4)  # 5 - 1
        
        # Шаг 5: Изменение статуса заказа (требует прав администратора)
        # Здесь мы делаем пользователя администратором для теста
        with self.app.app_context():
            user = User.query.filter_by(username='testuser').first()
            user.is_admin = True
            db.session.commit()
        
        response = self.client.post('/admin/orders/update_status', data={
            'order_id': 1,
            'status': 'processing'
        }, follow_redirects=True)
        
        self.assertIn(b'Статус заказа успешно обновлен', response.data)
        
        # Шаг 6: Отмена заказа
        response = self.client.post('/auth/order/1/cancel', follow_redirects=True)
        
        with self.app.app_context():
            order = Order.query.get(1)
            self.assertEqual(order.status, 'cancelled')
            
            # Проверяем, что товары вернулись на склад
            product1 = Product.query.filter_by(name='Test Product 1').first()
            product2 = Product.query.filter_by(name='Test Product 2').first()
            self.assertEqual(product1.stock, 10)  # 8 + 2
            self.assertEqual(product2.stock, 5)  # 4 + 1

if __name__ == '__main__':
    unittest.main()
