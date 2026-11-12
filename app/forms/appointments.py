from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, SubmitField, TextAreaField, TimeField
from wtforms.validators import DataRequired, Optional


class AppointmentForm(FlaskForm):
    pet_id = SelectField('Pet', coerce=int, validators=[DataRequired(message='Please select a pet.')])
    doctor_id = SelectField('Attending Doctor', coerce=int, validators=[DataRequired(message='Please assign a doctor.')])
    clinic_id = SelectField('Clinic Branch', coerce=int, validators=[DataRequired(message='Please choose clinic.')])
    appointment_type_id = SelectField('Service / Visit Type', coerce=int, validators=[DataRequired()])
    appointment_date = DateField('Appointment Date', validators=[DataRequired()])
    appointment_time = TimeField('Appointment Time', validators=[DataRequired()])
    reason = TextAreaField('Reason for Visit', validators=[DataRequired()])
    notes = TextAreaField('Internal Clinic Notes', validators=[Optional()])
    submit = SubmitField('Book Appointment')


class StatusUpdateForm(FlaskForm):
    new_status = SelectField('New Status', choices=[
        ('Scheduled', 'Scheduled'),
        ('Checked-In', 'Checked-In'),
        ('In-Consultation', 'In-Consultation'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
        ('No-Show', 'No-Show')
    ], validators=[DataRequired()])
    notes = TextAreaField('Status Change Notes', validators=[Optional()])
    submit = SubmitField('Update Status')

