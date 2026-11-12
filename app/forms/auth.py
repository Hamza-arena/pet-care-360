from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email


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

