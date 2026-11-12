from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateTimeLocalField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Optional


class LabOrderForm(FlaskForm):
    pet_id = SelectField('Pet', coerce=int, validators=[DataRequired()])
    doctor_id = SelectField('Ordering Doctor', coerce=int, validators=[DataRequired()])
    lab_test_id = SelectField('Diagnostic Test', coerce=int, validators=[DataRequired()])
    priority = SelectField('Priority', choices=[
        ('Routine', 'Routine'),
        ('Urgent', 'Urgent'),
        ('STAT', 'STAT (Emergency)')
    ], default='Routine')
    notes = TextAreaField('Clinical Indications / Notes', validators=[Optional()])
    submit = SubmitField('Submit Lab Order')


class LabResultForm(FlaskForm):
    result_value = StringField('Numerical / Short Result Value', validators=[Optional()])
    result_text = TextAreaField('Detailed Findings & Interpretation', validators=[DataRequired()])
    is_abnormal = BooleanField('Flag as Abnormal / Critical')
    notes = TextAreaField('Technician Notes', validators=[Optional()])
    submit = SubmitField('Record Lab Result')


class SurgeryForm(FlaskForm):
    pet_id = SelectField('Pet', coerce=int, validators=[DataRequired()])
    doctor_id = SelectField('Lead Surgeon', coerce=int, validators=[DataRequired()])
    room_id = SelectField('Operating Theater / Room', coerce=int, validators=[Optional()])
    surgery_type = StringField('Surgical Procedure Name', validators=[DataRequired()])
    scheduled_date = DateTimeLocalField('Scheduled Date & Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    description = TextAreaField('Pre-Op Notes & Procedure Plan', validators=[Optional()])
    anesthesia_type = StringField('Anesthesia Protocol', validators=[Optional()])
    submit = SubmitField('Schedule Surgery')

