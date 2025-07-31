from celery import Celery
from mail import send_mail, send_html_mail, send_mail_with_attachment
from datetime import datetime, timedelta
import os
import csv
import io

celery = Celery('tasks')
celery.conf.update(
    broker_url=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
)

@celery.task(bind=True)
def send_email_task(self, to_email, subject, body):
    try:
        result = send_mail(to_email, subject, body)
        if result:
            return f"Email sent successfully to {to_email}"
        else:
            return f"Failed to send email to {to_email}"
    except Exception as e:
        return f"Error sending email: {str(e)}"

@celery.task(bind=True)
def send_html_email_task(self, to_email, subject, html_body):
    try:
        result = send_html_mail(to_email, subject, html_body)
        if result:
            return f"HTML email sent successfully to {to_email}"
        else:
            return f"Failed to send HTML email to {to_email}"
    except Exception as e:
        return f"Error sending HTML email: {str(e)}"

@celery.task(bind=True)
def send_reservation_confirmation(self, user_email, reservation_details):
    subject = "Parking Reservation Confirmation - ParkEasy"
    body = f"""
Dear Customer,

Your parking reservation has been confirmed!

Reservation Details:
- Reservation ID: {reservation_details.get('id', 'N/A')}
- Parking Lot: {reservation_details.get('lot_name', 'N/A')}
- Spot Number: {reservation_details.get('spot_number', 'N/A')}
- Start Time: {reservation_details.get('start_time', 'N/A')}
- End Time: {reservation_details.get('end_time', 'N/A')}
- Total Amount: ₹{reservation_details.get('total_amount', 'N/A')}

Thank you for choosing ParkEasy!

Best regards,
ParkEasy Team
    """
    
    return send_email_task.delay(user_email, subject, body)

@celery.task(bind=True)
def send_reservation_reminder(self, user_email, reservation_details):
    subject = "Parking Reservation Reminder - ParkEasy"
    body = f"""
Dear Customer,

This is a reminder that your parking reservation is starting soon!

Reservation Details:
- Reservation ID: {reservation_details.get('id', 'N/A')}
- Parking Lot: {reservation_details.get('lot_name', 'N/A')}
- Spot Number: {reservation_details.get('spot_number', 'N/A')}
- Start Time: {reservation_details.get('start_time', 'N/A')}
- End Time: {reservation_details.get('end_time', 'N/A')}

Please arrive on time to secure your parking spot.

Best regards,
ParkEasy Team
    """
    
    return send_email_task.delay(user_email, subject, body)

@celery.task(bind=True)
def send_welcome_email(self, user_email, username):
    subject = "Welcome to ParkEasy!"
    body = f"""
Dear {username},

Welcome to ParkEasy! 

Your account has been successfully created. You can now:
- Search for parking spots
- Make reservations
- Manage your bookings
- View your parking history

Thank you for choosing ParkEasy for your parking needs!

Best regards,
ParkEasy Team
    """
    
    return send_email_task.delay(user_email, subject, body)

@celery.task(bind=True)
def send_cancellation_email(self, user_email, reservation_details):
    subject = "Parking Reservation Cancelled - ParkEasy"
    body = f"""
Dear Customer,

Your parking reservation has been cancelled.

Cancelled Reservation Details:
- Reservation ID: {reservation_details.get('id', 'N/A')}
- Parking Lot: {reservation_details.get('lot_name', 'N/A')}
- Spot Number: {reservation_details.get('spot_number', 'N/A')}
- Start Time: {reservation_details.get('start_time', 'N/A')}
- End Time: {reservation_details.get('end_time', 'N/A')}

If you have any questions, please contact our support team.

Best regards,
ParkEasy Team
    """
    
    return send_email_task.delay(user_email, subject, body)

# Periodic tasks setup
from celery.schedules import crontab

celery.conf.beat_schedule = {
    'send-test-email': {
        'task': 'tasks.send_email_task',
        'schedule': crontab(minute='*/30'), 
        'args': ('test@example.com', 'Test Email', 'This is a test email from Celery')
    },
}

celery.conf.timezone = 'UTC'

@celery.task(bind=True)
def generate_parking_report(self, admin_email):
    """Generate a comprehensive parking report and email it as CSV attachment"""
    try:
        import sqlite3
        import os
        
        # Connect to SQLite database directly
        db_path = os.path.join(os.path.dirname(__file__), 'instance', 'parking.db')
        
        if not os.path.exists(db_path):
            return {
                'status': 'error',
                'message': f'Database file not found at {db_path}'
            }
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query all reservations with related data using raw SQL
        query = """
        SELECT 
            r.id as reservation_id,
            u.username,
            u.email,
            pl.prime_location_name,
            pl.address,
            ps.spot_number,
            r.parking_timestamp,
            r.leaving_timestamp,
            r.parking_cost
        FROM reservation r
        JOIN user u ON r.user_id = u.id
        JOIN parking_spot ps ON r.spot_id = ps.id
        JOIN parking_lot pl ON ps.lot_id = pl.id
        ORDER BY r.parking_timestamp DESC
        """
        
        cursor.execute(query)
        reservations = cursor.fetchall()
        
        # Create CSV content
        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer)
        
        # Write headers
        csv_writer.writerow([
            'Reservation ID',
            'Username',
            'Email',
            'Parking Lot',
            'Address',
            'Spot Number',
            'Parking Time',
            'Leaving Time',
            'Duration (Hours)',
            'Cost (₹)',
            'Status'
        ])
        
        # Write data and calculate statistics
        total_reservations = len(reservations)
        completed_reservations = 0
        total_revenue = 0
        
        for reservation in reservations:
            reservation_id, username, email, location_name, address, spot_number, parking_time, leaving_time, cost = reservation
            
            # Calculate duration and status
            duration = "N/A"
            status = "Active"
            
            if leaving_time:
                try:
                    # Parse timestamps
                    parking_dt = datetime.fromisoformat(parking_time.replace('Z', '+00:00'))
                    leaving_dt = datetime.fromisoformat(leaving_time.replace('Z', '+00:00'))
                    duration_delta = leaving_dt - parking_dt
                    duration = round(duration_delta.total_seconds() / 3600, 2)  # Convert to hours
                    status = "Completed"
                    completed_reservations += 1
                except:
                    duration = "N/A"
            
            total_revenue += cost if cost else 0
            
            csv_writer.writerow([
                reservation_id,
                username,
                email,
                location_name,
                address,
                spot_number,
                parking_time,
                leaving_time if leaving_time else 'N/A',
                duration,
                f"₹{cost:.2f}" if cost else "₹0.00",
                status
            ])
        
        # Add summary rows
        active_reservations = total_reservations - completed_reservations
        
        csv_writer.writerow([])  # Empty row
        csv_writer.writerow(['SUMMARY STATISTICS'])
        csv_writer.writerow(['Total Reservations', total_reservations])
        csv_writer.writerow(['Completed Reservations', completed_reservations])
        csv_writer.writerow(['Active Reservations', active_reservations])
        csv_writer.writerow(['Total Revenue', f"₹{total_revenue:.2f}"])
        csv_writer.writerow(['Report Generated', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')])
        
        conn.close()
        
        # Get CSV content
        csv_content = csv_buffer.getvalue()
        csv_buffer.close()
        
        # Save CSV file to a temporary location
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"parking_report_{timestamp}.csv"
        
        # Create reports directory in the backend folder
        reports_dir = os.path.join(os.path.dirname(__file__), 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        filepath = os.path.join(reports_dir, filename)
        
        # Write CSV file
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            f.write(csv_content)
        
        # Send email with CSV attachment
        email_subject = "ParkEasy - Parking Report CSV Export"
        email_body = f"""
Dear Admin,

Your parking report has been generated successfully!

Report Summary:
- Total Reservations: {total_reservations}
- Completed Reservations: {completed_reservations}
- Active Reservations: {active_reservations}
- Total Revenue: ₹{total_revenue:.2f}
- Generated At: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

Please find the detailed CSV report attached to this email.

Best regards,
ParkEasy System
        """
        
        # Send email with attachment
        email_sent = send_mail_with_attachment(
            to_email=admin_email,
            subject=email_subject,
            body=email_body,
            attachment_path=filepath,
            attachment_name=filename
        )
        
        if email_sent:
            status_msg = f'Report generated and emailed successfully to {admin_email}'
        else:
            status_msg = f'Report generated but failed to send email to {admin_email}'
        
        return {
            'status': 'success' if email_sent else 'partial_success',
            'message': status_msg,
            'filename': filename,
            'filepath': filepath,
            'total_records': total_reservations,
            'total_revenue': total_revenue,
            'email_sent': email_sent
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error generating parking report: {str(e)}'
        }
