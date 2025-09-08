from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, SelectField, DateField, DateTimeField, DecimalField, IntegerField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, Optional
from wtforms.widgets import TextArea
from models import User
from datetime import datetime

class DateTimeLocalField(DateTimeField):
    """
    Custom DateTimeField to handle HTML5 datetime-local input format.
    """
    def __init__(self, label=None, validators=None, format='%Y-%m-%dT%H:%M', **kwargs):
        super().__init__(label, validators, format=format, **kwargs)

    def process_formdata(self, valuelist):
        if valuelist:
            date_str = valuelist[0]
            try:
                self.data = datetime.strptime(date_str, self.format[0] if isinstance(self.format, list) else self.format)
            except ValueError:
                self.data = None
                raise ValueError('Not a valid datetime value')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Password', validators=[DataRequired()])

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    date_of_birth = DateField('Date of Birth', validators=[Optional()])
    gender = SelectField('Gender', choices=[('', 'Select Gender'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], validators=[Optional()])
    user_type = SelectField('Account Type', choices=[('patient', 'Patient'), ('doctor', 'Doctor'), ('nurse', 'Nurse')], validators=[DataRequired()])
    
    # Staff specific fields
    specialty = StringField('Specialty', validators=[Optional(), Length(max=100)])
    license_number = StringField('License Number', validators=[Optional(), Length(max=50)])
    department = StringField('Department', validators=[Optional(), Length(max=100)])

class AppointmentForm(FlaskForm):
    doctor_id = SelectField('Doctor', coerce=int, validators=[DataRequired()])
    appointment_date = DateTimeLocalField('Appointment Date & Time', validators=[DataRequired()])
    reason = StringField('Reason for Visit', validators=[DataRequired(), Length(max=200)])
    notes = TextAreaField('Additional Notes', validators=[Optional()])

class MessageForm(FlaskForm):
    recipient_id = SelectField('To', coerce=int, validators=[DataRequired()])
    subject = StringField('Subject', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Message', validators=[DataRequired()], widget=TextArea())

class MedicalRecordForm(FlaskForm):
    patient_id = SelectField('Patient', coerce=int, validators=[DataRequired()])
    diagnosis = TextAreaField('Diagnosis', validators=[Optional()])
    symptoms = TextAreaField('Symptoms', validators=[Optional()])
    treatment = TextAreaField('Treatment', validators=[Optional()])
    prescription = TextAreaField('Prescription', validators=[Optional()])
    
    # Vital signs
    blood_pressure = StringField('Blood Pressure', validators=[Optional(), Length(max=20)])
    heart_rate = IntegerField('Heart Rate (BPM)', validators=[Optional(), NumberRange(min=40, max=200)])
    temperature = DecimalField('Temperature (°F)', validators=[Optional(), NumberRange(min=90, max=110)], places=1)
    weight = DecimalField('Weight (lbs)', validators=[Optional(), NumberRange(min=1, max=1000)], places=2)
    height = DecimalField('Height (inches)', validators=[Optional(), NumberRange(min=12, max=96)], places=2)
    
    # File upload
    file_upload = FileField('Upload File', validators=[FileAllowed(['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'], 'Images and documents only!')])

class MedicineOrderForm(FlaskForm):
    delivery_address = TextAreaField('Delivery Address', validators=[DataRequired()])

class LabTestBookingForm(FlaskForm):
    lab_test_id = SelectField('Lab Test', coerce=int, validators=[DataRequired()])
    booking_date = DateTimeLocalField('Preferred Date & Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    sample_collection_date = DateTimeLocalField('Sample Collection Date', format='%Y-%m-%dT%H:%M', validators=[Optional()])

class ProfileForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    address = TextAreaField('Address', validators=[Optional()])
    date_of_birth = DateField('Date of Birth', validators=[Optional()])
    gender = SelectField('Gender', choices=[('', 'Select Gender'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], validators=[Optional()])
    
    # Profile picture upload
    profile_picture = FileField('Profile Picture', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    
    # Staff specific fields
    specialty = StringField('Specialty', validators=[Optional(), Length(max=100)])
    license_number = StringField('License Number', validators=[Optional(), Length(max=50)])
    department = StringField('Department', validators=[Optional(), Length(max=100)])

class SearchForm(FlaskForm):
    query = StringField('Search', validators=[DataRequired()])
    search_type = SelectField('Search In', choices=[
        ('all', 'All'),
        ('patients', 'Patients'),
        ('doctors', 'Doctors'),
        ('appointments', 'Appointments'),
        ('medicines', 'Medicines'),
        ('lab_tests', 'Lab Tests')
    ], default='all')
