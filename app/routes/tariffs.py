from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from ..models import db, Tariff, Service

bp = Blueprint('tariffs', __name__, url_prefix='/tariffs')

@bp.route('/')
def index():
    """Страница со всеми тарифами"""
    # Получаем параметры фильтрации из запроса
    price_range = request.args.get('priceRange', 'all')
    internet_filter = request.args.get('internetFilter', 'all')
    minutes_filter = request.args.get('minutesFilter', 'all')
    
    # Начинаем с базового запроса
    query = Tariff.query
    
    # Фильтрация по цене
    if price_range != 'all':
        if price_range == '0-300':
            query = query.filter(Tariff.price <= 300)
        elif price_range == '300-500':
            query = query.filter(Tariff.price > 300, Tariff.price <= 500)
        elif price_range == '500-1000':
            query = query.filter(Tariff.price > 500, Tariff.price <= 1000)
        elif price_range == '1000+':
            query = query.filter(Tariff.price > 1000)
    
    # Фильтрация по интернету и минутам
    # Это требует анализа поля features, которое хранит JSON
    tariffs = query.all()
    filtered_tariffs = []
    
    for tariff in tariffs:
        # Обрабатываем JSON features один раз для обоих фильтров
        import json
        features = {}
        try:
            if tariff.features:
                features = json.loads(tariff.features)
        except Exception as e:
            # В случае ошибки при разборе JSON, просто продолжаем с пустым словарем
            features = {}
        
        # Проверяем соответствие интернет-фильтру
        if internet_filter != 'all':
            internet_value = str(features.get('internet', ''))
            
            # Проверка на безлимитный интернет
            is_unlimited = 'безлимит' in internet_value.lower()
            
            # Пытаемся извлечь числовое значение, если это не безлимит
            internet_gb = 0
            if not is_unlimited and 'ГБ' in internet_value:
                try:
                    internet_gb = float(internet_value.replace('ГБ', '').strip())
                except:
                    internet_gb = 0
            
            # Применяем фильтр
            if internet_filter == '0-10' and (internet_gb <= 10 and not is_unlimited):
                pass  # Тариф подходит
            elif internet_filter == '10-30' and (10 < internet_gb <= 30):
                pass  # Тариф подходит
            elif internet_filter == '30+' and internet_gb > 30:
                pass  # Тариф подходит
            elif internet_filter == 'unlimited' and is_unlimited:
                pass  # Тариф подходит
            else:
                continue  # Тариф не подходит, переходим к следующему
        
        # Проверяем соответствие фильтру минут
        if minutes_filter != 'all':
            minutes_value = str(features.get('minutes', '0'))
            
            # Проверка на безлимит
            is_unlimited_minutes = 'безлимит' in minutes_value.lower()
            
            # Получаем числовое значение
            minutes_count = 0
            if not is_unlimited_minutes:
                try:
                    minutes_count = int(minutes_value)
                except:
                    minutes_count = 0
            
            # Применяем фильтр
            if minutes_filter == '0-300' and minutes_count <= 300 and not is_unlimited_minutes:
                pass  # Тариф подходит
            elif minutes_filter == '300-600' and 300 < minutes_count <= 600 and not is_unlimited_minutes:
                pass  # Тариф подходит
            elif minutes_filter == '600+' and minutes_count > 600 and not is_unlimited_minutes:
                pass  # Тариф подходит
            elif minutes_filter == 'unlimited' and is_unlimited_minutes:
                pass  # Тариф подходит
            else:
                continue  # Тариф не подходит, переходим к следующему
                
        filtered_tariffs.append(tariff)
    
    return render_template('tariffs/index.html', 
                          tariffs=filtered_tariffs,
                          price_range=price_range,
                          internet_filter=internet_filter,
                          minutes_filter=minutes_filter)

@bp.route('/tariff/<int:tariff_id>')
def tariff_detail(tariff_id):
    """Детальная страница тарифа"""
    from flask_login import current_user
    
    tariff = Tariff.query.get_or_404(tariff_id)
    
    # Проверяем, есть ли у текущего пользователя активные подписки на этот тариф
    user_subscription = None
    if current_user.is_authenticated:
        from ..models import TariffSubscription
        user_subscription = TariffSubscription.query.filter_by(
            user_id=current_user.id, 
            tariff_id=tariff_id
        ).order_by(TariffSubscription.created_at.desc()).first()
    
    return render_template('tariffs/tariff_detail.html', 
                          tariff=tariff,
                          user_subscription=user_subscription)

@bp.route('/services')
def services():
    """Страница со всеми услугами"""
    # Получаем параметр фильтра по категории
    category = request.args.get('category', 'all')
    
    # Получаем все услуги
    all_services = Service.query.all()
    
    # Фильтруем услуги по категории, если указана
    if category == 'all':
        filtered_services = all_services
    else:
        # Сначала проверяем, есть ли услуги с установленной категорией
        filtered_by_column = [s for s in all_services if hasattr(s, 'category') and s.category == category]
        
        # Если есть услуги с заданной категорией, используем их
        if filtered_by_column:
            filtered_services = filtered_by_column
        # Иначе используем старый метод фильтрации по ключевым словам
        else:
            filtered_services = []
            for service in all_services:
                # Получаем нижний регистр имени и описания для поиска
                service_name = service.name.lower() if service.name else ""
                service_desc = service.description.lower() if service.description else ""
                
                # Проверяем категорию по ключевым словам
                if category == 'internet':
                    internet_keywords = ['интернет', 'гб', 'трафик', 'безлимит', 'соцсет', 'онлайн', 'youtube', 'интернета']
                    if any(keyword in service_name or keyword in service_desc for keyword in internet_keywords):
                        filtered_services.append(service)
                elif category == 'calls':
                    calls_keywords = ['звон', 'минут', 'вызов', 'связь', 'разговор', 'голосов', 'сим', 'номер']
                    if any(keyword in service_name or keyword in service_desc for keyword in calls_keywords):
                        filtered_services.append(service)
                elif category == 'security':
                    security_keywords = ['безопас', 'защит', 'блок', 'спам', 'контрол', 'антивирус', 'фильтр', 'родител']
                    if any(keyword in service_name or keyword in service_desc for keyword in security_keywords):
                        filtered_services.append(service)
    
    return render_template('tariffs/services.html', 
                          services=filtered_services,
                          all_services=all_services,
                          selected_category=category)

@bp.route('/service/<int:service_id>')
def service_detail(service_id):
    """Детальная страница услуги"""
    service = Service.query.get_or_404(service_id)
    
    # Получаем другие услуги из той же категории
    related_services = []
    if service.category:
        related_services = Service.query.filter(
            Service.category == service.category,
            Service.id != service.id
        ).limit(5).all()
    
    return render_template('tariffs/service_detail.html', service=service, services=related_services)

@bp.route('/compare')
def compare():
    """Страница для сравнения тарифов"""
    tariffs = Tariff.query.all()
    return render_template('tariffs/compare.html', tariffs=tariffs)


@bp.route('/subscribe/<int:tariff_id>', methods=['POST'])
def subscribe_to_tariff(tariff_id):
    """Подать заявку на подключение тарифа"""
    from flask_login import login_required, current_user
    from ..models import TariffSubscription
    from ..email import send_tariff_subscription_notification_admin, send_tariff_subscription_notification_user
    from datetime import datetime, timedelta
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"Получен запрос на подключение тарифа ID: {tariff_id} от пользователя: {current_user.username if current_user.is_authenticated else 'неавторизованный'}")
    
    # Требуем авторизацию
    if not current_user.is_authenticated:
        flash('Для подключения тарифа необходимо войти в систему.', 'danger')
        return redirect(url_for('auth.login'))
    
    tariff = Tariff.query.get_or_404(tariff_id)
    
    # Проверяем, нет ли уже активной подписки на этот тариф
    existing_active = TariffSubscription.query.filter_by(
        user_id=current_user.id,
        tariff_id=tariff_id,
        status='active'
    ).first()
    
    if existing_active:
        flash(f'У вас уже есть активная подписка на тариф "{tariff.name}".', 'warning')
        return redirect(url_for('tariffs.tariff_detail', tariff_id=tariff_id))
    
    # Проверяем, нет ли уже ожидающей подписки
    existing_pending = TariffSubscription.query.filter_by(
        user_id=current_user.id,
        tariff_id=tariff_id,
        status='pending'
    ).first()
    
    if existing_pending:
        flash(f'У вас уже есть ожидающая подтверждения заявка на тариф "{tariff.name}". Дождитесь её рассмотрения.', 'info')
        return redirect(url_for('tariffs.tariff_detail', tariff_id=tariff_id))
    
    # Создаем новую подписку
    subscription = TariffSubscription(
        user_id=current_user.id,
        tariff_id=tariff_id,
        status='pending'
    )
    
    db.session.add(subscription)
    db.session.commit()
      # Отправляем уведомления с обработкой ошибок
    try:
        # Уведомление администраторам
        send_tariff_subscription_notification_admin(subscription)
        # Уведомление пользователю
        send_tariff_subscription_notification_user(subscription, action="created")
        
        flash(f'Заявка на подключение тарифа "{tariff.name}" успешно отправлена и ждет подтверждения администратором.', 'success')
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при отправке уведомлений о подписке #{subscription.id}: {str(e)}")
        flash(f'Заявка на подключение тарифа "{tariff.name}" создана, но могут возникнуть проблемы с уведомлениями.', 'warning')
    
    return redirect(url_for('tariffs.tariff_detail', tariff_id=tariff_id))


@bp.route('/my-subscriptions')
@bp.route('/my-tariffs')  # Альтернативный URL
def my_subscriptions():
    """Страница с подписками пользователя на тарифы"""
    from flask_login import login_required, current_user
    from ..models import TariffSubscription
    
    # Требуем авторизацию
    if not current_user.is_authenticated:
        flash('Для просмотра подписок необходимо войти в систему.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Получаем все подписки пользователя
    subscriptions = TariffSubscription.query.filter_by(
        user_id=current_user.id
    ).order_by(TariffSubscription.created_at.desc()).all()
    
    return render_template(
        'tariffs/my_subscriptions.html',
        subscriptions=subscriptions,
        title='Мои тарифы'
    )
