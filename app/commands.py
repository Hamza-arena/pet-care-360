import click
from flask.cli import with_appcontext

from app.extensions import db
from app.models.auth import Role, User, UserRole


@click.command('create-admin')
@click.option('--email', prompt='Email', help='Admin email address')
@click.option('--username', prompt='Username', help='Admin username')
@click.option('--first-name', prompt='First Name', default='System', help='First name')
@click.option('--last-name', prompt='Last Name', default='Admin', help='Last name')
@click.option('--password', prompt='Password', hide_input=True, confirmation_prompt=True, help='Admin password')
@with_appcontext
def create_admin_command(email, username, first_name, last_name, password):
    """Create or update an administrative user via CLI."""
    email = email.strip().lower()
    username = username.strip()

    admin_role = Role.query.filter_by(name='Admin').first()
    if not admin_role:
        admin_role = Role(name='Admin', description='Complete system-wide administrative control')
        db.session.add(admin_role)
        db.session.commit()

    user = User.query.filter((User.email == email) | (User.username == username)).first()
    if user:
        click.echo(f"User with email '{email}' or username '{username}' already exists. Updating credentials.")
        user.email = email
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.set_password(password)
        user.is_active = True
        user.is_deleted = False
    else:
        user = User(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

    existing_ur = UserRole.query.filter_by(user_id=user.id, role_id=admin_role.id).first()
    if not existing_ur:
        ur = UserRole(user_id=user.id, role_id=admin_role.id)
        db.session.add(ur)

    db.session.commit()
    click.echo(f"Admin account '{email}' configured successfully.")


@click.command('seed-demo')
@with_appcontext
def seed_demo_command():
    """Seed the database with sample clinical demo data."""
    from seed import seed_database
    seed_database()
    click.echo("Demo data seeding completed.")


def register_commands(app):
    app.cli.add_command(create_admin_command)
    app.cli.add_command(seed_demo_command)
