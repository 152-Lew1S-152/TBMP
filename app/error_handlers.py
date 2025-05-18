# Обработчики ошибок для приложения Flask
from flask import render_template, Blueprint

# Создаем Blueprint для обработчиков ошибок
errors_bp = Blueprint('errors', __name__)

@errors_bp.app_errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@errors_bp.app_errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500

@errors_bp.app_errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

@errors_bp.app_errorhandler(400)
def bad_request(e):
    return render_template('errors/400.html'), 400

def init_error_handlers(app):
    app.register_blueprint(errors_bp)
