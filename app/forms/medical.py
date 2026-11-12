from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    FloatField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, NumberRange, Optional


class MedicalRecordForm(FlaskForm):
    chief_complaint = TextAreaField('Chief Complaint / Symptoms', validators=[DataRequired()])
    examination_notes = TextAreaField('Physical Examination Findings', validators=[Optional()])
    temperature = FloatField('Body Temp (°C)', validators=[Optional(), NumberRange(min=30, max=45)])
    weight = FloatField('Weight (kg)', validators=[Optional(), NumberRange(min=0, max=500)])
    heart_rate = IntegerField('Heart Rate (bpm)', validators=[Optional(), NumberRange(min=20, max=300)])
    respiratory_rate = IntegerField('Respiratory Rate (breaths/min)', validators=[Optional(), NumberRange(min=5, max=150)])
    blood_pressure = StringField('Blood Pressure (e.g. 120/80)', validators=[Optional()])
    follow_up_date = DateField('Follow-Up Date', validators=[Optional()])
    follow_up_notes = TextAreaField('Follow-Up Instructions', validators=[Optional()])
    
    # Primary Diagnosis & Initial Treatment
    diagnosis_id = SelectField('Diagnosis', coerce=int, validators=[Optional()])
    treatment_description = TextAreaField('Treatment Plan / Interventions', validators=[Optional()])
    submit = SubmitField('Save Medical Record')


class PrescriptionItemForm(FlaskForm):
    medicine_id = SelectField('Medicine', coerce=int, validators=[DataRequired()])
    dosage = StringField('Dosage (e.g. 250mg)', validators=[DataRequired()])
    frequency = StringField('Frequency (e.g. Twice daily after meals)', validators=[DataRequired()])
    duration = StringField('Duration (e.g. 7 days)', validators=[Optional()])
    quantity = IntegerField('Quantity to Dispense', validators=[DataRequired(), NumberRange(min=1)])
    instructions = TextAreaField('Special Instructions', validators=[Optional()])
    submit = SubmitField('Add to Prescription')

