from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    
    # User type: 'patient', 'doctor', 'nurse', 'admin'
    user_type = db.Column(db.String(20), nullable=False, default='patient')
    
    # Staff specific fields
    specialty = db.Column(db.String(100))  # For doctors
    license_number = db.Column(db.String(50))  # For medical staff
    department = db.Column(db.String(100))
    
    # Profile picture filename
    profile_picture = db.Column(db.String(200))
    
    # Status and timestamps
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient_appointments = db.relationship('Appointment', foreign_keys='Appointment.patient_id', backref='patient', lazy='dynamic')
    doctor_appointments = db.relationship('Appointment', foreign_keys='Appointment.doctor_id', backref='doctor', lazy='dynamic')
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy='dynamic')
    medical_records = db.relationship('MedicalRecord', backref='patient', lazy='dynamic', foreign_keys='MedicalRecord.patient_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def is_staff(self):
        return self.user_type in ['doctor', 'nurse', 'admin']
    
    def __repr__(self):
        return f'<User {self.username}>'

class Appointment(db.Model):
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    appointment_date = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=30)
    
    # Appointment details
    reason = db.Column(db.String(200))
    notes = db.Column(db.Text)
    
    # Status: 'scheduled', 'confirmed', 'completed', 'cancelled', 'no_show'
    status = db.Column(db.String(20), default='scheduled')
    
    # Payment status
    fee_amount = db.Column(db.Numeric(10, 2))
    payment_status = db.Column(db.String(20), default='pending')  # 'pending', 'paid', 'refunded'
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Appointment {self.id}: {self.patient.full_name} with {self.doctor.full_name}>'

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    subject = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Message {self.id}: from {self.sender.full_name} to {self.recipient.full_name}>'

class MedicalRecord(db.Model):
    __tablename__ = 'medical_records'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'))
    
    # Record details
    diagnosis = db.Column(db.Text)
    symptoms = db.Column(db.Text)
    treatment = db.Column(db.Text)
    prescription = db.Column(db.Text)
    
    # Vital signs
    blood_pressure = db.Column(db.String(20))
    heart_rate = db.Column(db.Integer)
    temperature = db.Column(db.Numeric(4, 1))
    weight = db.Column(db.Numeric(5, 2))
    height = db.Column(db.Numeric(5, 2))
    
    # File attachments
    file_path = db.Column(db.String(200))
    file_name = db.Column(db.String(100))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    doctor = db.relationship('User', foreign_keys=[doctor_id])
    appointment = db.relationship('Appointment', backref='medical_records')
    
    def __repr__(self):
        return f'<MedicalRecord {self.id}: {self.patient.full_name}>'

class Medicine(db.Model):
    __tablename__ = 'medicines'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    manufacturer = db.Column(db.String(100))
    
    # Pricing and inventory
    price = db.Column(db.Numeric(10, 2))
    stock_quantity = db.Column(db.Integer, default=0)
    
    # Medicine details
    dosage_form = db.Column(db.String(50))  # tablet, capsule, syrup, etc.
    strength = db.Column(db.String(50))
    category = db.Column(db.String(50))
    
    # Status
    is_prescription_required = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Medicine {self.name}>'

class MedicineOrder(db.Model):
    __tablename__ = 'medicine_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Order details
    order_number = db.Column(db.String(50), unique=True)
    total_amount = db.Column(db.Numeric(10, 2))
    
    # Status: 'pending', 'confirmed', 'shipped', 'delivered', 'cancelled'
    status = db.Column(db.String(20), default='pending')
    
    # Address
    delivery_address = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='medicine_orders')
    order_items = db.relationship('MedicineOrderItem', backref='order', lazy='dynamic')
    
    def __repr__(self):
        return f'<MedicineOrder {self.order_number}>'

class MedicineOrderItem(db.Model):
    __tablename__ = 'medicine_order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('medicine_orders.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2))
    total_price = db.Column(db.Numeric(10, 2))
    
    # Relationships
    medicine = db.relationship('Medicine', backref='order_items')

class LabTest(db.Model):
    __tablename__ = 'lab_tests'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    
    # Pricing and details
    price = db.Column(db.Numeric(10, 2))
    preparation_instructions = db.Column(db.Text)
    sample_type = db.Column(db.String(50))  # blood, urine, etc.
    
    # Timing
    fasting_required = db.Column(db.Boolean, default=False)
    result_time_hours = db.Column(db.Integer, default=24)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<LabTest {self.name}>'

class LabTestBooking(db.Model):
    __tablename__ = 'lab_test_bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lab_test_id = db.Column(db.Integer, db.ForeignKey('lab_tests.id'), nullable=False)
    
    # Booking details
    booking_date = db.Column(db.DateTime, nullable=False)
    sample_collection_date = db.Column(db.DateTime)
    
    # Status: 'booked', 'sample_collected', 'in_progress', 'completed', 'cancelled'
    status = db.Column(db.String(20), default='booked')
    
    # Payment
    amount_paid = db.Column(db.Numeric(10, 2))
    payment_status = db.Column(db.String(20), default='pending')
    
    # Results
    result_file_path = db.Column(db.String(200))
    result_notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='lab_test_bookings')
    lab_test = db.relationship('LabTest', backref='bookings')
    
    def __repr__(self):
        return f'<LabTestBooking {self.id}: {self.user.full_name} - {self.lab_test.name}>'

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    # Notification type: 'appointment', 'payment', 'system', 'message'
    notification_type = db.Column(db.String(20), default='system')
    
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='notifications')
    
    def __repr__(self):
        return f'<Notification {self.id}: {self.title}>'
