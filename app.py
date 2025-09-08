import os
import logging
from dotenv import load_dotenv
load_dotenv()

from flask import Flask

def nl2br(value):
    """Convert newlines to <br> tags."""
    if value is None:
        return ''
    return value.replace('\n', '<br>\n')

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.jinja_env.filters['nl2br'] = nl2br

# Secret key handling (stable across restarts in production)
app.secret_key = os.environ.get("SESSION_SECRET") or os.environ.get("SECRET_KEY") or "dev-secret-please-change"
if not os.environ.get("SESSION_SECRET") and not os.environ.get("SECRET_KEY"):
    logging.warning("SESSION_SECRET not set. Using a development secret key. Set SESSION_SECRET in the environment for production.")

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Ensure instance folder exists for SQLite fallback
instance_path = os.path.join(os.path.dirname(__file__), "instance")
os.makedirs(instance_path, exist_ok=True)

# Configure the database with robust defaults
raw_database_url = (os.environ.get("DATABASE_URL", "").strip())
if raw_database_url.startswith("postgres://"):
    # SQLAlchemy 2.x requires explicit driver; ensure compatibility
    raw_database_url = raw_database_url.replace("postgres://", "postgresql+psycopg2://", 1)

if raw_database_url:
    app.config["SQLALCHEMY_DATABASE_URI"] = raw_database_url
else:
    sqlite_path = os.path.join(instance_path, "health_web.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite_path}"
    logging.info(f"No DATABASE_URL provided. Falling back to SQLite at {sqlite_path}")

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# File upload configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Create tables
with app.app_context():
    # Import models to register them
    import models  # noqa: F401
    import routes  # Import routes to register all route handlers
    db.create_all()
    logging.info("Database tables created")

# Create upload directory
import os
os.makedirs('uploads', exist_ok=True)
