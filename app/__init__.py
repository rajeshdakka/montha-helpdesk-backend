from flask import Flask
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import os

bcrypt = Bcrypt()

def create_app():
    load_dotenv()

    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

    bcrypt.init_app(app)

    from .routes.auth_routes import auth_bp
    from .routes.report_routes import report_bp
    from .routes.admin_routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(admin_bp)

    return app