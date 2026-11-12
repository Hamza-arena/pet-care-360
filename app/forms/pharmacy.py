from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    FloatField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class MedicineForm(FlaskForm):
    name = StringField('Brand Name', validators=[DataRequired(), Length(max=100)])
    generic_name = StringField('Generic / Scientific Name', validators=[Optional(), Length(max=100)])
    category = SelectField('Category', choices=[
        ('Antibiotic', 'Antibiotic'),
        ('Analgesic', 'Analgesic / Pain Relief'),
        ('Anti-inflammatory', 'Anti-inflammatory'),
        ('Vaccine', 'Vaccine'),
        ('Supplement', 'Supplement / Vitamin'),
        ('Antiparasitic', 'Antiparasitic / Dewormer'),
        ('Dermatological', 'Dermatological'),
        ('Other', 'Other')
    ], default='Antibiotic')
    description = TextAreaField('Description / Indications', validators=[Optional()])
    manufacturer = StringField('Manufacturer', validators=[Optional(), Length(max=100)])
    unit = SelectField('Unit Form', choices=[
        ('Tablet', 'Tablet'),
        ('Capsule', 'Capsule'),
        ('Syrup', 'Syrup (ml)'),
        ('Injection', 'Injection (vial)'),
        ('Cream', 'Cream / Ointment'),
        ('Drops', 'Eye/Ear Drops')
    ], default='Tablet')
    strength = StringField('Strength (e.g. 500mg, 10mg/ml)', validators=[Optional(), Length(max=50)])
    base_price = FloatField('Base Unit Price (PKR)', validators=[DataRequired(), NumberRange(min=0)])
    requires_prescription = BooleanField('Prescription Required', default=True)
    minimum_stock = IntegerField('Minimum Reorder Threshold', validators=[DataRequired(), NumberRange(min=0)], default=10)
    submit = SubmitField('Save Medicine')


class MedicineBatchForm(FlaskForm):
    batch_number = StringField('Batch / Lot #', validators=[DataRequired(), Length(max=50)])
    quantity_received = IntegerField('Quantity Received', validators=[DataRequired(), NumberRange(min=1)])
    purchase_price = FloatField('Purchase Cost (PKR)', validators=[Optional(), NumberRange(min=0)])
    selling_price = FloatField('Selling Price (PKR)', validators=[Optional(), NumberRange(min=0)])
    manufacture_date = DateField('Manufacturing Date', validators=[Optional()])
    expiry_date = DateField('Expiration Date', validators=[DataRequired()])
    supplier = StringField('Supplier / Distributor', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Receive Batch')


class DispenseForm(FlaskForm):
    batch_id = SelectField('From Batch', coerce=int, validators=[Optional()])
    quantity = IntegerField('Quantity to Dispense', validators=[DataRequired(), NumberRange(min=1)])
    notes = TextAreaField('Dispense Notes', validators=[Optional()])
    submit = SubmitField('Dispense & Deduct Stock')

