from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    FloatField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class PetForm(FlaskForm):
    name = StringField('Pet Name', validators=[
        DataRequired(message='Pet name is required.'),
        Length(max=100)
    ])
    owner_id = SelectField('Owner', coerce=int, validators=[DataRequired(message='Owner is required.')])
    species_id = SelectField('Species', coerce=int, validators=[DataRequired(message='Species is required.')])
    breed_id = SelectField('Breed', coerce=int, validators=[Optional()])
    gender = SelectField('Gender', choices=[
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Unknown', 'Unknown')
    ], default='Male')
    date_of_birth = DateField('Date of Birth', validators=[Optional()])
    color = StringField('Color / Markings', validators=[Optional(), Length(max=50)])
    weight = FloatField('Weight (kg)', validators=[Optional(), NumberRange(min=0, max=500)])
    microchip_number = StringField('Microchip #', validators=[Optional(), Length(max=50)])
    is_neutered = BooleanField('Neutered / Spayed')
    insurance_number = StringField('Insurance Policy #', validators=[Optional(), Length(max=50)])
    notes = TextAreaField('Medical & Behavioral Notes', validators=[Optional()])
    submit = SubmitField('Save Pet')


class AllergyForm(FlaskForm):
    allergen = StringField('Allergen', validators=[DataRequired(), Length(max=100)])
    severity = SelectField('Severity', choices=[
        ('Mild', 'Mild'),
        ('Moderate', 'Moderate'),
        ('Severe', 'Severe')
    ], default='Moderate')
    reaction = TextAreaField('Reaction Description', validators=[Optional()])
    diagnosed_date = DateField('Diagnosed Date', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Add Allergy')

