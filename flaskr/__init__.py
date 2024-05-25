from flask import Flask
import os
import click
from flask.cli import with_appcontext

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.secret_key = "some random value"

    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Import Blueprints
    from .main import bp as main_bp
    from .auth import bp as auth_bp
    from .admin import bp as admin_bp
    from .stock import bp as stock_bp
    from .profile import bp as profile_bp

    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(stock_bp)
    app.register_blueprint(profile_bp)

    from .db import get_db, close_db
    app.teardown_appcontext(close_db)

    # Define a function to initialize the database
    def init_db():
        db = get_db()
        with app.open_resource('schema.sql') as f:
            db.executescript(f.read().decode('utf8'))
        db.commit()

    # Define a command that can be called from the command line
    @click.command('init-db')
    @with_appcontext
    def init_db_command():
        """Clear existing data and create new tables."""
        init_db()
        click.echo('Initialized the database.')

    # Register commands into Flask application
    app.cli.add_command(init_db_command)

    return app


