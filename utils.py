from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import and_, func
from app import db
from models import Notification, Appointment, Message, User, MedicalRecord

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_notification(user_id, title, message, notification_type='system'):
    """Create a new notification for a user"""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type
    )
    db.session.add(notification)
    db.session.commit()
    return notification

def get_dashboard_stats(user):
    """Get dashboard statistics for a user"""
    if not user.is_staff():
        # Patient stats
        stats = {
            'total_appointments': Appointment.query.filter_by(patient_id=user.id).count(),
            'upcoming_appointments': Appointment.query.filter(
                and_(Appointment.patient_id == user.id,
                     Appointment.appointment_date > datetime.utcnow(),
                     Appointment.status.in_(['scheduled', 'confirmed']))
            ).count(),
            'unread_messages': Message.query.filter_by(recipient_id=user.id, is_read=False).count(),
            'medical_records': MedicalRecord.query.filter_by(patient_id=user.id).count()
        }
    else:
        # Staff stats
        today = datetime.utcnow().date()
        
        if user.user_type == 'doctor':
            stats = {
                'todays_appointments': Appointment.query.filter(
                    and_(Appointment.doctor_id == user.id,
                         func.date(Appointment.appointment_date) == today)
                ).count(),
                'total_patients': db.session.query(User.id).join(
                    Appointment, User.id == Appointment.patient_id
                ).filter(Appointment.doctor_id == user.id).distinct().count(),
                'unread_messages': Message.query.filter_by(recipient_id=user.id, is_read=False).count(),
                'pending_payments': db.session.query(func.sum(Appointment.fee_amount)).filter(
                    and_(Appointment.doctor_id == user.id,
                         Appointment.payment_status == 'pending')
                ).scalar() or 0
            }
        else:
            # General staff stats
            stats = {
                'total_appointments': Appointment.query.count(),
                'total_patients': User.query.filter_by(user_type='patient').count(),
                'unread_messages': Message.query.filter_by(recipient_id=user.id, is_read=False).count(),
                'total_staff': User.query.filter(User.user_type.in_(['doctor', 'nurse'])).count()
            }
    
    return stats

def format_currency(amount):
    """Format amount as currency"""
    if amount is None:
        return "$0.00"
    return f"${float(amount):,.2f}"

def get_appointment_status_color(status):
    """Get Bootstrap color class for appointment status"""
    color_map = {
        'scheduled': 'warning',
        'confirmed': 'success',
        'completed': 'primary',
        'cancelled': 'danger',
        'no_show': 'secondary'
    }
    return color_map.get(status, 'secondary')

def get_payment_status_color(status):
    """Get Bootstrap color class for payment status"""
    color_map = {
        'pending': 'warning',
        'paid': 'success',
        'refunded': 'info',
        'failed': 'danger'
    }
    return color_map.get(status, 'secondary')

def calculate_age(birth_date):
    """Calculate age from birth date"""
    if not birth_date:
        return None
    
    today = datetime.utcnow().date()
    age = today.year - birth_date.year
    
    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1
    
    return age

def get_next_available_slots(doctor_id, days_ahead=7):
    """Get next available appointment slots for a doctor"""
    slots = []
    start_date = datetime.utcnow().date() + timedelta(days=1)  # Start from tomorrow
    
    # Working hours: 9 AM to 5 PM, 30-minute slots
    working_hours = list(range(9, 17))  # 9 AM to 4:30 PM (last slot)
    
    for day_offset in range(days_ahead):
        current_date = start_date + timedelta(days=day_offset)
        
        # Skip weekends (assuming Monday=0, Sunday=6)
        if current_date.weekday() >= 5:  # Saturday and Sunday
            continue
        
        # Check existing appointments for this day
        existing_appointments = Appointment.query.filter(
            and_(Appointment.doctor_id == doctor_id,
                 func.date(Appointment.appointment_date) == current_date,
                 Appointment.status.in_(['scheduled', 'confirmed']))
        ).all()
        
        existing_times = [apt.appointment_date.time() for apt in existing_appointments]
        
        # Generate available slots
        for hour in working_hours:
            for minute in [0, 30]:  # 30-minute intervals
                slot_time = datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))
                
                if slot_time.time() not in existing_times:
                    slots.append(slot_time)
    
    return slots[:20]  # Return first 20 available slots

def send_appointment_reminder():
    """Send appointment reminders (to be called by a scheduled task)"""
    # Get appointments for tomorrow
    tomorrow = datetime.utcnow().date() + timedelta(days=1)
    
    appointments = Appointment.query.filter(
        and_(func.date(Appointment.appointment_date) == tomorrow,
             Appointment.status.in_(['scheduled', 'confirmed']))
    ).all()
    
    for appointment in appointments:
        # Create reminder notification for patient
        create_notification(
            appointment.patient_id,
            'Appointment Reminder',
            f'You have an appointment with Dr. {appointment.doctor.full_name} tomorrow at {appointment.appointment_date.strftime("%I:%M %p")}',
            'appointment'
        )
        
        # Create reminder notification for doctor
        create_notification(
            appointment.doctor_id,
            'Appointment Reminder',
            f'You have an appointment with {appointment.patient.full_name} tomorrow at {appointment.appointment_date.strftime("%I:%M %p")}',
            'appointment'
        )

def cleanup_old_notifications(days_old=30):
    """Clean up old read notifications"""
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    
    old_notifications = Notification.query.filter(
        and_(Notification.is_read == True,
             Notification.created_at < cutoff_date)
    ).all()
    
    for notification in old_notifications:
        db.session.delete(notification)
    
    db.session.commit()
    return len(old_notifications)
