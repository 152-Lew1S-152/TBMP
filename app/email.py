from threading import Thread
from flask import current_app, render_template
from flask_mail import Mail, Message

mail = Mail()

def send_async_email(app, msg):
    """Отправка электронной почты в отдельном потоке."""
    with app.app_context():
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body):
    """Основная функция для отправки электронной почты."""
    app = current_app._get_current_object()
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    
    # Запускаем отправку письма в отдельном потоке
    Thread(target=send_async_email, args=(app, msg)).start()


def send_order_status_notification(order):
    """Отправка уведомления об изменении статуса заказа."""
    # Если у заказа есть пользователь и у пользователя есть email
    if not order.user or not order.user.email:
        return
      # Email магазина
    sender = current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@tbmp.com')
    
    # Статусы на русском
    status_text = {
        'new': 'Новый',
        'processing': 'В обработке',
        'shipped': 'Отправлен',
        'delivered': 'Доставлен',
        'cancelled': 'Отменён'
    }
    
    # Тема письма
    subject = f'Статус заказа №{order.id} изменен на "{status_text.get(order.status, "Неизвестно")}"'
    
    # Получатель
    recipients = [order.user.email]
    
    # Текст письма (обычный текст)
    text_body = render_template('email/order_status_notification.txt', 
                               order=order, 
                               status_text=status_text.get(order.status, "Неизвестно"))
                               
    # HTML-версия письма
    html_body = render_template('email/order_status_notification.html', 
                               order=order, 
                               status_text=status_text.get(order.status, "Неизвестно"))
    
    # Отправляем письмо
    send_email(subject, sender, recipients, text_body, html_body)


def send_tariff_subscription_notification_admin(subscription):
    """Отправка уведомления администратору о новой заявке на подключение тарифа."""
    # Получаем список администраторов из базы данных
    from .models import User
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"Начало отправки уведомления администраторам о подписке #{subscription.id}")
    
    try:
        # Используем текущий контекст приложения
        admin_users = User.query.filter_by(is_admin=True).all()
        
        if not admin_users:
            logger.warning("Не найдено ни одного администратора для отправки уведомления о подписке")
            return
        
        logger.info(f"Найдено {len(admin_users)} администраторов")
          # Email магазина
        sender = current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@tbmp.com')
        
        # Тема письма
        subject = f'Новая заявка на подключение тарифа от {subscription.user.username}'
        
        # Получатели - все администраторы
        recipients = [admin.email for admin in admin_users if admin.email]
        
        if not recipients:
            logger.warning("У администраторов не указаны email-адреса для отправки уведомлений")
            return
            
        logger.info(f"Подготовлена отправка уведомления на адреса: {', '.join(recipients)}")
        
        # Статусы на русском
        status_text = {
            'pending': 'Ожидает подтверждения',
            'active': 'Активирован',
            'cancelled': 'Отменен',
            'expired': 'Истек срок'
        }
        
        # Текст письма (обычный текст)
        text_body = f"""
        Новая заявка на подключение тарифа
        
        Пользователь: {subscription.user.username} ({subscription.user.email})
        Тариф: {subscription.tariff.name}
        Цена: {subscription.tariff.price} руб. / {subscription.tariff.period}
        Статус: {status_text.get(subscription.status, 'Неизвестно')}
        Дата заявки: {subscription.created_at.strftime('%d.%m.%Y %H:%M')}
        
        Для управления заявками перейдите в панель администратора.
        """
        
        # HTML-версия письма
        html_body = f"""
        <h2>Новая заявка на подключение тарифа</h2>
        
        <p><strong>Пользователь:</strong> {subscription.user.username} ({subscription.user.email})</p>
        <p><strong>Тариф:</strong> {subscription.tariff.name}</p>
        <p><strong>Цена:</strong> {subscription.tariff.price} руб. / {subscription.tariff.period}</p>
        <p><strong>Статус:</strong> {status_text.get(subscription.status, 'Неизвестно')}</p>
        <p><strong>Дата заявки:</strong> {subscription.created_at.strftime('%d.%m.%Y %H:%M')}</p>
        
        <p><a href="{current_app.config.get('SITE_URL', '')}admin/tariff_subscriptions">Перейти к управлению заявками</a></p>
        """
        
        # Отправляем письмо
        try:
            send_email(subject, sender, recipients, text_body, html_body)
            logger.info(f"Уведомление о подписке #{subscription.id} отправлено администраторам: {', '.join(recipients)}")
        except Exception as mail_error:
            logger.error(f"Ошибка при отправке уведомления по email: {str(mail_error)}")
            logger.error(f"Получатели: {recipients}")
            logger.error(f"Отправитель: {sender}")
            logger.error(f"Тема: {subject}")
            logger.error(f"Настройки почты: сервер={current_app.config.get('MAIL_SERVER')}, порт={current_app.config.get('MAIL_PORT')}, TLS={current_app.config.get('MAIL_USE_TLS')}")
            
    except Exception as e:
        logger.error(f"Общая ошибка при отправке уведомления администраторам: {str(e)}")
        # Не вызываем исключение дальше, чтобы не прерывать основной процесс


def send_tariff_subscription_notification_user(subscription, action="updated"):
    """Отправка уведомления пользователю об изменении статуса заявки на тариф."""
    # Если у подписки есть пользователь и у пользователя есть email
    if not subscription.user or not subscription.user.email:
        return
    
    # Статусы на русском
    status_text = {
        'pending': 'Ожидает подтверждения',
        'active': 'Активирован',
        'cancelled': 'Отменен',
        'expired': 'Истек срок'
    }
      # Email магазина
    sender = current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@tbmp.com')
    
    # Определяем тему в зависимости от действия
    if action == "created":
        subject = f'Заявка на подключение тарифа "{subscription.tariff.name}" принята'
    else:
        subject = f'Статус заявки на тариф "{subscription.tariff.name}" изменен на "{status_text.get(subscription.status, "Неизвестно")}"'
    
    # Получатель
    recipients = [subscription.user.email]
    
    # Текст письма (обычный текст)
    text_body = f"""
    Уважаемый(ая) {subscription.user.username},
    
    Информация о вашей заявке на подключение тарифа:
    
    Тариф: {subscription.tariff.name}
    Цена: {subscription.tariff.price} руб. / {subscription.tariff.period}
    Текущий статус: {status_text.get(subscription.status, 'Неизвестно')}
    """
    
    if subscription.admin_comment:
        text_body += f"\nКомментарий от администратора: {subscription.admin_comment}\n"
    
    if subscription.status == 'active' and subscription.activated_at:
        text_body += f"\nДата активации: {subscription.activated_at.strftime('%d.%m.%Y')}"
        if subscription.expires_at:
            text_body += f"\nДействует до: {subscription.expires_at.strftime('%d.%m.%Y')}"
    
    text_body += "\n\nС уважением, команда TBMP"
    
    # HTML-версия письма
    html_body = f"""
    <h2>Информация о заявке на тариф</h2>
    
    <p>Уважаемый(ая) {subscription.user.username},</p>
    
    <p>Информация о вашей заявке на подключение тарифа:</p>
    
    <ul>
        <li><strong>Тариф:</strong> {subscription.tariff.name}</li>
        <li><strong>Цена:</strong> {subscription.tariff.price} руб. / {subscription.tariff.period}</li>
        <li><strong>Текущий статус:</strong> {status_text.get(subscription.status, 'Неизвестно')}</li>
    """
    
    if subscription.admin_comment:
        html_body += f"<li><strong>Комментарий от администратора:</strong> {subscription.admin_comment}</li>"
    
    if subscription.status == 'active' and subscription.activated_at:
        html_body += f"<li><strong>Дата активации:</strong> {subscription.activated_at.strftime('%d.%m.%Y')}</li>"
        if subscription.expires_at:
            html_body += f"<li><strong>Действует до:</strong> {subscription.expires_at.strftime('%d.%m.%Y')}</li>"
    
    html_body += "</ul><p>С уважением,<br>Команда TBMP</p>"
    
    # Отправляем письмо
    send_email(subject, sender, recipients, text_body, html_body)
