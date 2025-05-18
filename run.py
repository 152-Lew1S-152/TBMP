from app import create_app
from app.models import db
import os
import logging
from datetime import datetime
from app.db_utils import configure_sqlite

# Настройка логирования - вывод как в файл, так и в консоль
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Обработчик для записи в файл
file_handler = logging.FileHandler('app_run.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(console_handler)

app = create_app()

# Настройка SQLite для лучшей производительности
with app.app_context():
    configure_sqlite(db.engine, timeout=60)
    logger.info("SQLite настроен с увеличенным timeout и оптимизациями")

# Добавляем datetime в глобальный контекст шаблонов
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8000)
