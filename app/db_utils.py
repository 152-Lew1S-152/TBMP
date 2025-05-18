import time
import logging
from functools import wraps
from sqlalchemy.exc import OperationalError
from .models import db

logger = logging.getLogger(__name__)

def safe_db_operation(operation, fallback_value=None, max_retries=3, retry_delay=1):
    """
    Выполняет операцию с базой данных с обработкой ошибок и повторными попытками.
    
    Args:
        operation: Функция, которая выполняет операцию с базой данных.
        fallback_value: Значение, возвращаемое в случае ошибки.
        max_retries: Максимальное количество повторных попыток (по умолчанию 3).
        retry_delay: Задержка между повторными попытками в секундах (по умолчанию 1).
        
    Returns:
        Результат операции или fallback_value в случае ошибки.
    """
    retries = 0
    while retries < max_retries:
        try:
            result = operation()
            return result
        except OperationalError as e:
            retries += 1
            db.session.rollback()  # Откатываем транзакцию
            
            logger.warning(f"БД заблокирована (attempt {retries}/{max_retries}): {str(e)}")
            
            if "database is locked" in str(e) and retries < max_retries:
                # Если БД заблокирована, ждем некоторое время и повторяем попытку
                time.sleep(retry_delay)
                continue
            else:
                logger.error(f"Ошибка базы данных после {retries} попыток: {str(e)}")
                return fallback_value
        except Exception as e:
            db.session.rollback()
            logger.error(f"Неожиданная ошибка при работе с базой данных: {str(e)}")
            return fallback_value
    
    return fallback_value

def configure_sqlite(db_engine, timeout=30, journal_mode='WAL'):
    """
    Настраивает SQLite для лучшей производительности и надежности.
    
    Args:
        db_engine: Экземпляр SQLAlchemy engine
        timeout: Время ожидания в секундах перед выбрасыванием ошибки блокировки
        journal_mode: Режим журнала для SQLite ('DELETE', 'TRUNCATE', 'PERSIST', 'MEMORY', 'WAL', 'OFF')
    """
    from sqlalchemy import event
    
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(f"PRAGMA busy_timeout = {timeout * 1000}")  # в миллисекундах
        
        # Проверяем, поддерживается ли WAL режим
        try:
            cursor.execute(f"PRAGMA journal_mode = {journal_mode}")
            result = cursor.fetchone()
            logger.info(f"SQLite journal mode set to: {result[0]}")
        except Exception as e:
            logger.warning(f"Не удалось установить режим журнала SQLite: {str(e)}")
            
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA cache_size = 5000")
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()
        
    # Регистрируем функцию обработки события подключения
    event.listen(db_engine, 'connect', set_sqlite_pragma)