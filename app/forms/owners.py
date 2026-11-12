from flask_wtf import FlaskForm
from wtforms import DateField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional


class OwnerForm(FlaskForm):
    first_name = StringField('First Name', validators=[
        DataRequired(message='First name is required.'),
        Length(max=50)
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(message='Last name is required.'),
        Length(max=50)
    ])
    email = StringField('Email Address', validators=[
        Optional(),
        Email(message='Please enter a valid email address.'),
        Length(max=120)
    ])
    phone = StringField('Primary Phone', validators=[
        DataRequired(message='Phone number is required.'),
        Length(max=20)
    ])
    emergency_contact = StringField('Emergency Contact Phone', validators=[
        Optional(),
        Length(max=20)
    ])
    date_of_birth = DateField('Date of Birth', validators=[Optional()])
    national_id = StringField('National ID / Passport', validators=[
        Optional(),
        Length(max=20)
    ])
    # Address details (for primary address)
    street_address = StringField('Street Address', validators=[Optional(), Length(max=200)])
    city = StringField('City', validators=[Optional(), Length(max=100)])
    state = StringField('State / Province', validators=[Optional(), Length(max=100)])
    postal_code = StringField('Postal Code', validators=[Optional(), Length(max=20)])
    notes = TextAreaField('Client Notes / Preferences', validators=[Optional()])
    submit = SubmitField('Save Owner')

