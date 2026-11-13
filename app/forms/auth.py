from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[
        DataRequired(message='Email is required.'),
        Email(message='Please enter a valid email address.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.')
    ])
    remember_me = BooleanField('Keep me signed in')
    submit = SubmitField('Sign In')


class RegisterForm(FlaskForm):
    first_name = StringField('First Name', validators=[
        DataRequired(message='First name is required.'),
        Length(max=50)
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(message='Last name is required.'),
        Length(max=50)
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message='Email is required.'),
        Email(message='Please enter a valid email address.'),
        Length(max=120)
    ])
    phone = StringField('Phone Number', validators=[
        DataRequired(message='Phone number is required.'),
        Length(max=20)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.'),
        Length(min=4, message='Password must be at least 4 characters long.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password.'),
        EqualTo('password', message='Passwords must match.')
    ])
    # Optional first pet details
    pet_name = StringField('Pet Name (Optional)', validators=[Optional(), Length(max=50)])
    pet_species = StringField('Pet Species (e.g. Dog, Cat)', validators=[Optional(), Length(max=50)])
    submit = SubmitField('Create Account')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message='Current password is required.')
    ])
    new_password = PasswordField('New Password', validators=[
        DataRequired(message='New password is required.'),
        Length(min=4, message='Password must be at least 4 characters long.')
    ])
    confirm_new_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message='Please confirm your new password.'),
        EqualTo('new_password', message='New passwords must match.')
    ])
    submit = SubmitField('Update Password')


