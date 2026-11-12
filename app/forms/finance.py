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


class InvoiceForm(FlaskForm):
    owner_id = SelectField('Pet Owner', coerce=int, validators=[DataRequired()])
    pet_id = SelectField('Pet', coerce=int, validators=[Optional()])
    due_date = DateField('Payment Due Date', validators=[Optional()])
    discount_amount = FloatField('Discount (PKR)', validators=[Optional(), NumberRange(min=0)], default=0.0)
    tax_amount = FloatField('Tax (PKR)', validators=[Optional(), NumberRange(min=0)], default=0.0)
    notes = TextAreaField('Invoice Notes / Payment Terms', validators=[Optional()])
    submit = SubmitField('Create Invoice')


class InvoiceItemForm(FlaskForm):
    description = StringField('Service or Item Description', validators=[DataRequired()])
    item_type = SelectField('Item Type', choices=[
        ('Consultation', 'Doctor Consultation'),
        ('Vaccine', 'Vaccination'),
        ('Laboratory', 'Laboratory Test'),
        ('Surgery', 'Surgical Procedure'),
        ('Pharmacy', 'Pharmacy / Medication'),
        ('Boarding', 'Boarding & Grooming'),
        ('Other', 'Other Service')
    ], default='Consultation')
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)], default=1)
    unit_price = FloatField('Unit Price (PKR)', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Add Item')


class PaymentForm(FlaskForm):
    payment_method_id = SelectField('Payment Method', coerce=int, validators=[DataRequired()])
    amount = FloatField('Payment Amount (PKR)', validators=[DataRequired(), NumberRange(min=0.01)])
    transaction_reference = StringField('Transaction Ref / Receipt #', validators=[Optional()])
    notes = TextAreaField('Payment Notes', validators=[Optional()])
    submit = SubmitField('Record Payment')

