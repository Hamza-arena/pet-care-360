from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, NumberRange, Optional


class VaccinationRecordForm(FlaskForm):
    pet_id = SelectField('Pet', coerce=int, validators=[DataRequired()])
    vaccine_id = SelectField('Vaccine', coerce=int, validators=[DataRequired()])
    doctor_id = SelectField('Administering Doctor', coerce=int, validators=[DataRequired()])
    administration_date = DateField('Administration Date', validators=[DataRequired()])
    dose_number = IntegerField('Dose #', validators=[DataRequired(), NumberRange(min=1)], default=1)
    batch_number = StringField('Vaccine Batch #', validators=[Optional()])
    next_due_date = DateField('Next Booster Due Date', validators=[Optional()])
    site_of_administration = SelectField('Injection Site', choices=[
        ('Right Shoulder (SC)', 'Right Shoulder (SC)'),
        ('Left Shoulder (SC)', 'Left Shoulder (SC)'),
        ('Right Hind Leg (SC)', 'Right Hind Leg (SC)'),
        ('Left Hind Leg (SC)', 'Left Hind Leg (SC)'),
        ('Intranasal', 'Intranasal'),
        ('Oral', 'Oral')
    ], default='Right Shoulder (SC)')
    reaction = TextAreaField('Adverse Reactions (if any)', validators=[Optional()])
    notes = TextAreaField('Clinical Notes', validators=[Optional()])
    submit = SubmitField('Record Vaccination')


class DewormingRecordForm(FlaskForm):
    pet_id = SelectField('Pet', coerce=int, validators=[DataRequired()])
    doctor_id = SelectField('Doctor / Tech', coerce=int, validators=[Optional()])
    medication_name = StringField('Dewormer Medication Name', validators=[DataRequired()])
    administration_date = DateField('Administration Date', validators=[DataRequired()])
    dosage = StringField('Dosage Administered', validators=[Optional()])
    next_due_date = DateField('Next Treatment Due Date', validators=[Optional()])
    weight_at_time = StringField('Weight at Time (kg)', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Record Deworming')

