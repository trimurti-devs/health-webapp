import os
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_, func
from sqlalchemy.exc import IntegrityError
from app import app, db
from models import User, Appointment, Message, MedicalRecord, Medicine, MedicineOrder, MedicineOrderItem, LabTest, LabTestBooking, Notification
from forms import LoginForm, RegistrationForm, AppointmentForm, MessageForm, MedicalRecordForm, MedicineOrderForm, LabTestBookingForm, ProfileForm, SearchForm
from utils import allowed_file, create_notification, get_dashboard_stats

# Authentication Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=True)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if username or email already exists
        existing_user = User.query.filter(
            or_(User.username == form.username.data, User.email == form.email.data)
        ).first()
        
        if existing_user:
            flash('Username or email already exists', 'danger')
            return render_template('register.html', form=form)
        
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            date_of_birth=form.date_of_birth.data,
            gender=form.gender.data,
            user_type=form.user_type.data,
            specialty=form.specialty.data if form.user_type.data in ['doctor', 'nurse'] else None,
            license_number=form.license_number.data if form.user_type.data in ['doctor', 'nurse'] else None,
            department=form.department.data if form.user_type.data in ['doctor', 'nurse'] else None
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        # Create welcome notification
        create_notification(
            user.id,
            'Welcome to Healthcare24/7!',
            'Thank you for registering with us. Your account has been created successfully.',
            'system'
        )
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Patient Dashboard Routes
@app.route('/patient/dashboard')
@login_required
def patient_dashboard():
    if current_user.is_staff():
        return redirect(url_for('staff_dashboard'))
    
    # Get recent appointments
    recent_appointments = Appointment.query.filter_by(patient_id=current_user.id)\
        .order_by(Appointment.appointment_date.desc()).limit(5).all()
    
    # Get unread messages
    unread_messages = Message.query.filter_by(recipient_id=current_user.id, is_read=False)\
        .order_by(Message.created_at.desc()).limit(5).all()
    
    # Get recent notifications
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).limit(5).all()
    
    # Get medical records count
    medical_records_count = MedicalRecord.query.filter_by(patient_id=current_user.id).count()
    
    stats = {
        'total_appointments': Appointment.query.filter_by(patient_id=current_user.id).count(),
        'upcoming_appointments': Appointment.query.filter(
            and_(Appointment.patient_id == current_user.id, 
                 Appointment.appointment_date > datetime.utcnow(),
                 Appointment.status.in_(['scheduled', 'confirmed']))
        ).count(),
        'unread_messages': len(unread_messages),
        'pending_lab_results': LabTestBooking.query.filter(
            and_(LabTestBooking.user_id == current_user.id,
                 LabTestBooking.status == 'in_progress')
        ).count(),
        'medical_records': medical_records_count
    }
    
    return render_template('patient_dashboard.html', 
                         appointments=recent_appointments,
                         messages=unread_messages,
                         notifications=notifications,
                         stats=stats)

# Patient Profile Route
@app.route('/patient/profile')
@login_required
def patient_profile():
    if current_user.is_staff():
        return redirect(url_for('staff_dashboard'))
    
    # Fetch any additional data if needed, e.g., appointments, medical records
    appointments = Appointment.query.filter_by(patient_id=current_user.id).order_by(Appointment.appointment_date.desc()).all()
    medical_records = MedicalRecord.query.filter_by(patient_id=current_user.id).order_by(MedicalRecord.created_at.desc()).all()
    
    return render_template('patient_profile.html',
                           appointments=appointments,
                           medical_records=medical_records)

@app.route('/patient/settings', methods=['GET', 'POST'])
@login_required
def patient_settings():
    if current_user.is_staff():
        return redirect(url_for('staff_dashboard'))
    
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        form.populate_obj(current_user)
        # Handle profile picture upload
        if form.profile_picture.data and not isinstance(form.profile_picture.data, str):
            file = form.profile_picture.data
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            # Save only the filename string, not the FileStorage object
            current_user.profile_picture = filename
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('patient_settings'))
    
    return render_template('patient_settings.html', form=form)

# Staff Dashboard Routes
@app.route('/staff/dashboard')
@login_required
def staff_dashboard():
    if not current_user.is_staff():
        return redirect(url_for('patient_dashboard'))
    
    stats = get_dashboard_stats(current_user)
    
    # Get today's appointments
    today = datetime.utcnow().date()
    todays_appointments = Appointment.query.filter(
        and_(Appointment.doctor_id == current_user.id,
             func.date(Appointment.appointment_date) == today)
    ).order_by(Appointment.appointment_date).all()
    
    # Get recent messages
    recent_messages = Message.query.filter_by(recipient_id=current_user.id)\
        .order_by(Message.created_at.desc()).limit(5).all()
    
    return render_template('staff_dashboard.html', 
                         stats=stats,
                         appointments=todays_appointments,
                         messages=recent_messages)

# Patient Settings Route
# Removed duplicate patient_settings route to fix AssertionError

# Patient Messages List Route
@app.route('/patient/messages')
@login_required
def patient_messages():
    if current_user.is_staff():
        return redirect(url_for('staff_dashboard'))
    
    page = request.args.get('page', 1, type=int)
    messages = Message.query.filter_by(recipient_id=current_user.id)\
        .order_by(Message.created_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    
    return render_template('patient_messages.html', messages=messages)

@app.route('/patient/appointment/<int:appointment_id>')
@login_required
def patient_appointment_detail(appointment_id):
    if current_user.is_staff():
        return redirect(url_for('staff_dashboard'))
    
    appointment = Appointment.query.filter_by(id=appointment_id, patient_id=current_user.id).first_or_404()
    
    return render_template('patient_appointment_detail.html', appointment=appointment)

@app.route('/patient/appointments')
@login_required
def patient_appointments():
    if current_user.is_staff():
        return redirect(url_for('staff_dashboard'))
    
    filter_type = request.args.get('filter', 'all')
    query = Appointment.query.filter_by(patient_id=current_user.id)
    
    if filter_type == 'upcoming':
        query = query.filter(Appointment.appointment_date > datetime.utcnow())
    
    appointments = query.order_by(Appointment.appointment_date.desc()).all()
    
    return render_template('patient_appointments.html', appointments=appointments)

# Staff Calendar Route
@app.route('/staff/calendar')
@login_required
def staff_calendar():
    if not current_user.is_staff():
        return redirect(url_for('patient_dashboard'))
    
    return render_template('staff_calendar.html')

# API endpoint to serve calendar events
@app.route('/api/staff/calendar-events')
@login_required
def staff_calendar_events():
    if not current_user.is_staff():
        return jsonify([])

    appointments = Appointment.query.filter_by(doctor_id=current_user.id).all()
    events = []
    for appt in appointments:
        events.append({
            'title': f'Appointment with {appt.patient.full_name}',
            'start': appt.appointment_date.isoformat(),
            'url': url_for('staff_patient_profile', patient_id=appt.patient_id)
        })
    return jsonify(events)

@app.route('/staff/appointments')
@login_required
def staff_appointments():
    if not current_user.is_staff():
        return redirect(url_for('patient_dashboard'))
    
    page = request.args.get('page', 1, type=int)
    appointments = Appointment.query.filter_by(doctor_id=current_user.id)\
        .order_by(Appointment.appointment_date.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    
    return render_template('staff_appointments.html', appointments=appointments)

@app.route('/staff/patients')
@login_required
def staff_patients():
    if not current_user.is_staff():
        return redirect(url_for('patient_dashboard'))
    
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    
    # Get patients who have appointments with this doctor
    patients_query = db.session.query(User).join(Appointment, User.id == Appointment.patient_id)\
        .filter(Appointment.doctor_id == current_user.id, User.user_type == 'patient')\
        .distinct()
    
    if search_query:
        patients_query = patients_query.filter(
            or_(User.first_name.contains(search_query),
                User.last_name.contains(search_query),
                User.email.contains(search_query))
        )
    
    patients = patients_query.paginate(page=page, per_page=10, error_out=False)
    
    return render_template('staff_patients.html', patients=patients, search_query=search_query)

@app.route('/staff/patient/<int:patient_id>')
@login_required
def staff_patient_profile(patient_id):
    if not current_user.is_staff():
        return redirect(url_for('patient_dashboard'))
    
    patient = User.query.get_or_404(patient_id)
    if patient.user_type != 'patient':
        flash('Invalid patient ID', 'danger')
        return redirect(url_for('staff_patients'))
    
    # Get patient's medical records
    medical_records = MedicalRecord.query.filter_by(patient_id=patient.id)\
        .order_by(MedicalRecord.created_at.desc()).all()
    
    # Get patient's appointments
    appointments = Appointment.query.filter_by(patient_id=patient.id)\
        .order_by(Appointment.appointment_date.desc()).all()
    
    return render_template('staff_profile.html', 
                         patient=patient,
                         medical_records=medical_records,
                         appointments=appointments)

@app.route('/staff/messages')
@login_required
def staff_messages():
    if not current_user.is_staff():
        return redirect(url_for('patient_dashboard'))
    
    page = request.args.get('page', 1, type=int)
    messages = Message.query.filter_by(recipient_id=current_user.id)\
        .order_by(Message.created_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    
    return render_template('staff_messages.html', messages=messages)

@app.route('/staff/notifications')
@login_required
def staff_notifications():
    if not current_user.is_staff():
        return redirect(url_for('patient_dashboard'))
    
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).all()
    
    return render_template('staff_notifications.html', notifications=notifications)

@app.route('/staff/payment-info')
@login_required
def staff_payment_info():
    if not current_user.is_staff():
        return redirect(url_for('patient_dashboard'))
    
    # Get payment statistics
    recent_payments = Appointment.query.filter(
        and_(Appointment.doctor_id == current_user.id,
             Appointment.payment_status == 'paid')
    ).order_by(Appointment.updated_at.desc()).limit(10).all()
    
    pending_payments = Appointment.query.filter(
        and_(Appointment.doctor_id == current_user.id,
             Appointment.payment_status == 'pending')
    ).order_by(Appointment.appointment_date.desc()).limit(10).all()
    
    # Monthly summary
    today = datetime.utcnow()
    first_day = today.replace(day=1)
    
    monthly_collected = db.session.query(func.sum(Appointment.fee_amount)).filter(
        and_(Appointment.doctor_id == current_user.id,
             Appointment.payment_status == 'paid',
             Appointment.updated_at >= first_day)
    ).scalar() or 0
    
    monthly_pending = db.session.query(func.sum(Appointment.fee_amount)).filter(
        and_(Appointment.doctor_id == current_user.id,
             Appointment.payment_status == 'pending',
             Appointment.created_at >= first_day)
    ).scalar() or 0
    
    # Fix template name to plural
    return render_template('staff_payments_info.html', 
                         recent_payments=recent_payments,
                         pending_payments=pending_payments,
                         monthly_collected=monthly_collected,
                         monthly_pending=monthly_pending)

@app.route('/staff/settings', methods=['GET', 'POST'])
@login_required
def staff_settings():
    if not current_user.is_staff():
        return redirect(url_for('patient_dashboard'))

    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        try:
            form.populate_obj(current_user)
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('staff_settings'))
        except IntegrityError:
            db.session.rollback()
            flash('Email address already exists. Please use a different email.', 'danger')
            return redirect(url_for('staff_settings'))

    return render_template('staff_settings.html', form=form)

# Appointment Management
@app.route('/book-appointment', methods=['GET', 'POST'])
@login_required
def book_appointment():
    # Removed staff user redirect to allow access
    # if current_user.is_staff():
    #     return redirect(url_for('staff_dashboard'))
    
    form = AppointmentForm()
    
    # Populate doctor choices
    doctors = User.query.filter_by(user_type='doctor', is_active=True).all()
    form.doctor_id.choices = [(d.id, f"Dr. {d.full_name} - {d.specialty or 'General'}") for d in doctors]
    
    if form.validate_on_submit():
        # Check if appointment slot is available
        existing_appointment = Appointment.query.filter(
            and_(Appointment.doctor_id == form.doctor_id.data,
                 Appointment.appointment_date == form.appointment_date.data,
                 Appointment.status.in_(['scheduled', 'confirmed']))
        ).first()
        
        if existing_appointment:
            flash('This appointment slot is not available. Please choose a different time.', 'danger')
        else:
            appointment = Appointment(
                patient_id=current_user.id,
                doctor_id=form.doctor_id.data,
                appointment_date=form.appointment_date.data,
                reason=form.reason.data,
                notes=form.notes.data,
                fee_amount=150.00  # Default fee
            )
            
            db.session.add(appointment)
            db.session.commit()
            
            # Create notifications
            doctor = User.query.get(form.doctor_id.data)
            create_notification(
                doctor.id,
                'New Appointment Scheduled',
                f'New appointment with {current_user.full_name} on {form.appointment_date.data.strftime("%B %d, %Y at %I:%M %p")}',
                'appointment'
            )
            
            create_notification(
                current_user.id,
                'Appointment Confirmation',
                f'Your appointment with Dr. {doctor.full_name} has been scheduled for {form.appointment_date.data.strftime("%B %d, %Y at %I:%M %p")}',
                'appointment'
            )
            
            flash('Appointment booked successfully!', 'success')
            return redirect(url_for('patient_dashboard'))
    
    return render_template('find_doctors.html', form=form, doctors=doctors)

@app.route('/find-doctors')
@login_required
def find_doctors():
    search_query = request.args.get('search', '')
    doctors_query = User.query.filter_by(user_type='doctor', is_active=True)
    if search_query:
        doctors_query = doctors_query.filter(
            or_(
                User.first_name.contains(search_query),
                User.last_name.contains(search_query),
                User.specialty.contains(search_query)
            )
        )
    doctors = doctors_query.all()
    # Remove redirect to staff_dashboard to prevent redirection
    return render_template('find_doctors.html', doctors=doctors)

# Medicine Management
@app.route('/buy-medicines')
@login_required
def buy_medicines():
    search_query = request.args.get('search', '')
    category = request.args.get('category', '')
    page = request.args.get('page', 1, type=int)
    
    medicines_query = Medicine.query.filter_by(is_active=True)
    
    if search_query:
        medicines_query = medicines_query.filter(
            or_(Medicine.name.contains(search_query),
                Medicine.description.contains(search_query))
        )
    
    if category:
        medicines_query = medicines_query.filter_by(category=category)
    
    medicines = medicines_query.paginate(page=page, per_page=12, error_out=False)
    
    # Get categories for filter
    categories = db.session.query(Medicine.category).filter(Medicine.category.isnot(None)).distinct().all()
    categories = [cat[0] for cat in categories]
    
    return render_template('buy_medicines.html', 
                         medicines=medicines,
                         categories=categories,
                         search_query=search_query,
                         current_category=category)

@app.route('/add-to-cart/<int:medicine_id>')
@login_required
def add_to_cart(medicine_id):
    medicine = Medicine.query.get_or_404(medicine_id)
    
    # Get or create cart in session
    cart = session.get('cart', {})
    cart_key = str(medicine_id)
    
    if cart_key in cart:
        cart[cart_key]['quantity'] += 1
    else:
        cart[cart_key] = {
            'id': medicine.id,
            'name': medicine.name,
            'price': float(medicine.price),
            'quantity': 1
        }
    
    session['cart'] = cart
    flash(f'{medicine.name} added to cart!', 'success')
    
    return redirect(url_for('buy_medicines'))

@app.route('/cart')
@login_required
def view_cart():
    cart = session.get('cart', {})
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    
    return render_template('cart.html', cart=cart, total=total)

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('buy_medicines'))
    
    form = MedicineOrderForm()
    if form.validate_on_submit():
        # Create order
        order = MedicineOrder(
            user_id=current_user.id,
            order_number=f'ORD{datetime.utcnow().strftime("%Y%m%d%H%M%S")}',
            delivery_address=form.delivery_address.data,
            total_amount=sum(item['price'] * item['quantity'] for item in cart.values())
        )
        
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        # Create order items
        for item in cart.values():
            order_item = MedicineOrderItem(
                order_id=order.id,
                medicine_id=item['id'],
                quantity=item['quantity'],
                unit_price=item['price'],
                total_price=item['price'] * item['quantity']
            )
            db.session.add(order_item)
        
        db.session.commit()
        
        # Clear cart
        session.pop('cart', None)
        
        # Create notification
        create_notification(
            current_user.id,
            'Order Confirmation',
            f'Your medicine order #{order.order_number} has been placed successfully.',
            'system'
        )
        
        flash(f'Order placed successfully! Order number: {order.order_number}', 'success')
        return redirect(url_for('patient_dashboard'))
    
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    return render_template('checkout.html', form=form, cart=cart, total=total)

# Lab Tests
@app.route('/lab-tests')
@login_required
def lab_tests():
    search_query = request.args.get('search', '')
    category = request.args.get('category', '')
    page = request.args.get('page', 1, type=int)
    
    tests_query = LabTest.query.filter_by(is_active=True)
    
    if search_query:
        tests_query = tests_query.filter(
            or_(LabTest.name.contains(search_query),
                LabTest.description.contains(search_query))
        )
    
    if category:
        tests_query = tests_query.filter_by(category=category)
    
    tests = tests_query.paginate(page=page, per_page=12, error_out=False)
    
    # Get categories for filter
    categories = db.session.query(LabTest.category).filter(LabTest.category.isnot(None)).distinct().all()
    categories = [cat[0] for cat in categories]
    
    return render_template('lab_tests.html', 
                         tests=tests,
                         categories=categories,
                         search_query=search_query,
                         current_category=category)

@app.route('/book-lab-test/<int:test_id>', methods=['GET', 'POST'])
@login_required
def book_lab_test(test_id):
    test = LabTest.query.get_or_404(test_id)
    form = LabTestBookingForm()
    
    if form.validate_on_submit():
        booking = LabTestBooking(
            user_id=current_user.id,
            lab_test_id=test.id,
            booking_date=form.booking_date.data,
            sample_collection_date=form.sample_collection_date.data,
            amount_paid=test.price
        )
        
        db.session.add(booking)
        db.session.commit()
        
        # Create notification
        create_notification(
            current_user.id,
            'Lab Test Booked',
            f'Your {test.name} test has been booked successfully.',
            'system'
        )
        
        flash(f'{test.name} test booked successfully!', 'success')
        return redirect(url_for('patient_dashboard'))
    
    return render_template('book_lab_test.html', form=form, test=test)

# Messages
@app.route('/send-message', methods=['GET', 'POST'])
@login_required
def send_message():
    form = MessageForm()
    
    # Populate recipient choices based on user type
    if current_user.is_staff():
        # Staff can message patients and other staff
        recipients = User.query.filter(User.id != current_user.id, User.is_active == True).all()
    else:
        # Patients can message staff only
        recipients = User.query.filter(User.user_type.in_(['doctor', 'nurse', 'admin']), User.is_active == True).all()
    
    form.recipient_id.choices = [(r.id, f"{r.full_name} ({r.user_type.title()})") for r in recipients]
    
    if form.validate_on_submit():
        message = Message(
            sender_id=current_user.id,
            recipient_id=form.recipient_id.data,
            subject=form.subject.data,
            content=form.content.data
        )
        
        db.session.add(message)
        db.session.commit()
        
        # Create notification for recipient
        recipient = User.query.get(form.recipient_id.data)
        create_notification(
            recipient.id,
            'New Message',
            f'You have received a new message from {current_user.full_name}',
            'message'
        )
        
        flash('Message sent successfully!', 'success')
        return redirect(url_for('staff_messages') if current_user.is_staff() else url_for('patient_dashboard'))
    
    return render_template('send_message.html', form=form)

@app.route('/message/<int:message_id>')
@login_required
def view_message(message_id):
    app.logger.debug(f"View message requested: message_id={message_id}, current_user_id={current_user.id}")
    message = Message.query.get_or_404(message_id)
    app.logger.debug(f"Message sender_id={message.sender_id}, recipient_id={message.recipient_id}")
    
    # Check if user is authorized to view this message
    if message.sender_id != current_user.id and message.recipient_id != current_user.id:
        app.logger.warning(f"Unauthorized access attempt by user {current_user.id} to message {message_id}")
        flash('You are not authorized to view this message.', 'danger')
        return redirect(url_for('staff_messages') if current_user.is_staff() else url_for('patient_dashboard'))
    
    # Mark as read if user is the recipient
    if message.recipient_id == current_user.id and not message.is_read:
        message.is_read = True
        message.read_at = datetime.utcnow()
        db.session.commit()
    
    return render_template('view_message.html', message=message)

# Medical Records (Staff only)
@app.route('/add-medical-record/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def add_medical_record(patient_id):
    if not current_user.is_staff():
        return redirect(url_for('patient_dashboard'))
    
    patient = User.query.get_or_404(patient_id)
    form = MedicalRecordForm()
    
    if form.validate_on_submit():
        record = MedicalRecord(
            patient_id=patient.id,
            doctor_id=current_user.id,
            diagnosis=form.diagnosis.data,
            symptoms=form.symptoms.data,
            treatment=form.treatment.data,
            prescription=form.prescription.data,
            blood_pressure=form.blood_pressure.data,
            heart_rate=form.heart_rate.data,
            temperature=form.temperature.data,
            weight=form.weight.data,
            height=form.height.data
        )
        
        # Handle file upload
        if form.file_upload.data:
            file = form.file_upload.data
            if allowed_file(file.filename):
                filename = secure_filename(f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                record.file_path = file_path
                record.file_name = file.filename
        
        db.session.add(record)
        db.session.commit()
        
        # Create notification for patient
        create_notification(
            patient.id,
            'Medical Record Updated',
            f'Dr. {current_user.full_name} has added a new medical record to your profile.',
            'system'
        )
        
        flash('Medical record added successfully!', 'success')
        return redirect(url_for('staff_patient_profile', patient_id=patient.id))
    
    return render_template('add_medical_record.html', form=form, patient=patient)

# Notifications
@app.route('/mark-notification-read/<int:notification_id>')
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    
    if notification.user_id != current_user.id:
        flash('You are not authorized to perform this action.', 'danger')
        return redirect(url_for('index'))
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.session.commit()
    
    return redirect(request.referrer or url_for('index'))

# Search
@app.route('/search')
@login_required
def search():
    form = SearchForm()
    results = {}
    
    if request.args.get('query'):
        query = request.args.get('query')
        search_type = request.args.get('search_type', 'all')
        
        if search_type in ['all', 'patients'] and current_user.is_staff():
            results['patients'] = User.query.filter(
                and_(User.user_type == 'patient',
                     or_(User.first_name.contains(query),
                         User.last_name.contains(query),
                         User.email.contains(query)))
            ).limit(10).all()
        
        if search_type in ['all', 'doctors']:
            results['doctors'] = User.query.filter(
                and_(User.user_type == 'doctor',
                     User.is_active == True,
                     or_(User.first_name.contains(query),
                         User.last_name.contains(query),
                         User.specialty.contains(query)))
            ).limit(10).all()
        
        if search_type in ['all', 'medicines']:
            results['medicines'] = Medicine.query.filter(
                and_(Medicine.is_active == True,
                     or_(Medicine.name.contains(query),
                         Medicine.description.contains(query)))
            ).limit(10).all()
        
        if search_type in ['all', 'lab_tests']:
            results['lab_tests'] = LabTest.query.filter(
                and_(LabTest.is_active == True,
                     or_(LabTest.name.contains(query),
                         LabTest.description.contains(query)))
            ).limit(10).all()
    
    return render_template('search_results.html', form=form, results=results, query=request.args.get('query'))

# Talk Support (Chat)
@app.route('/talk-support')
@login_required
def talk_support():
    return render_template('talk_support.html')



# File serving
@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Health Records Page
@app.route('/health-records')
@login_required
def health_records():
    return render_template('health_records.html')


# API endpoints for AJAX requests
@app.route('/api/unread-messages-count')
@login_required
def unread_messages_count():
    count = Message.query.filter_by(recipient_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})

@app.route('/api/unread-notifications-count')
@login_required
def unread_notifications_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})

@app.route('/api/message/<int:message_id>')
@login_required
def api_get_message(message_id):
    try:
        message = Message.query.get_or_404(message_id)
        if message.sender_id != current_user.id and message.recipient_id != current_user.id:
            app.logger.warning(f"Unauthorized API access attempt by user {current_user.id} to message {message_id}")
            return jsonify({'error': 'Unauthorized access'}), 403
        return jsonify({
            'id': message.id,
            'subject': message.subject,
            'content': message.content,
            'sender_full_name': message.sender.full_name if message.sender else 'Unknown',
            'sender_user_type': message.sender.user_type.title() if message.sender else 'Unknown',
            'created_at': message.created_at.strftime('%B %d, %Y at %I:%M %p')
        })
    except Exception as e:
        app.logger.error(f"Error fetching message {message_id}: {e}")
        return jsonify({'error': 'Failed to fetch message details'}), 500

@app.route('/api/message/mark-read/<int:message_id>', methods=['POST'])
@login_required
def api_mark_message_read(message_id):
    try:
        message = Message.query.get_or_404(message_id)
        if message.recipient_id != current_user.id:
            app.logger.warning(f"Unauthorized mark-read attempt by user {current_user.id} on message {message_id}")
            return jsonify({'error': 'Unauthorized access'}), 403
        if not message.is_read:
            message.is_read = True
            message.read_at = datetime.utcnow()
            db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error marking message {message_id} as read: {e}")
        return jsonify({'error': 'Failed to mark message as read'}), 500

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
