from flask import Flask, jsonify
from config import Config
from models import db, User, ParkingLot, ParkingSpot
from flask_cors import CORS
from tasks import send_email_task, send_reservation_confirmation, send_welcome_email

from routes.auth_routes import register_auth_routes
from routes.api_routes import register_api_routes
from routes.admin_routes import register_admin_routes
from routes.user_routes import register_user_routes

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"], 
     allow_headers=["Content-Type", "Authorization"], 
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

db.init_app(app)

@app.route('/')
def home():
    return "Parking App Running!"

@app.route('/test-email')
def test_email():
    task = send_email_task.delay(
        'test@example.com', 
        'Test Email from ParkEasy', 
        'This is a test email to check if Celery is working!'
    )
    return jsonify({
        'message': 'Email task queued successfully!',
        'task_id': task.id,
        'status': 'Check your email and Celery worker logs'
    })

@app.route('/test-welcome-email')
def test_welcome_email():
    task = send_welcome_email.delay('test@example.com', 'TestUser')
    return jsonify({
        'message': 'Welcome email task queued!',
        'task_id': task.id,
        'status': 'Check your email and Celery worker logs'
    })

@app.route('/test-reservation-email')
def test_reservation_email():
    reservation_details = {
        'id': '12345',
        'lot_name': 'Test Mall Parking',
        'spot_number': 'A15',
        'start_time': '2025-07-31 10:00 AM',
        'end_time': '2025-07-31 2:00 PM',
        'total_amount': '60'
    }
    task = send_reservation_confirmation.delay('test@example.com', reservation_details)
    return jsonify({
        'message': 'Reservation confirmation email task queued!',
        'task_id': task.id,
        'reservation_details': reservation_details,
        'status': 'Check your email and Celery worker logs'
    })

@app.route('/celery-status')
def celery_status():
    try:
        from tasks import celery
        inspect = celery.control.inspect()
        stats = inspect.stats()
        active = inspect.active()
        
        if stats:
            return jsonify({
                'status': 'Celery is working!',
                'workers': list(stats.keys()),
                'active_tasks': len(active.get(list(stats.keys())[0], [])) if active else 0
            })
        else:
            return jsonify({
                'status': 'No Celery workers found',
                'message': 'Make sure to run: celery -A celery_app worker --loglevel=info'
            })
    except Exception as e:
        return jsonify({
            'status': 'Celery connection failed',
            'error': str(e),
            'message': 'Make sure Redis is running and Celery worker is started'
        })

@app.route('/setup')
def setup_db():
    db.create_all()
    
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@test.com', phone_number='9999999999', address='Admin Office', pincode='000000', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
    
    if not ParkingLot.query.first():
        lot = ParkingLot(prime_location_name='Mall Parking', address='Downtown Mall', 
                        pin_code='400001', price_per_hour=15, number_of_spots=20)
        db.session.add(lot)
        db.session.commit()
        
        for i in range(1, 21):
            spot = ParkingSpot(lot_id=lot.id, spot_number=f'A{i}', status='A')
            db.session.add(spot)
        
        db.session.commit()
    
    return "Database setup complete!"

@app.route('/debug')
def debug():
    return jsonify({
        'message': 'Flask is working!',
        'routes_count': len(list(app.url_map.iter_rules())),
        'debug_mode': app.debug
    })

@app.route('/test-summary')
def test_summary():
    try:
        from models import Reservation
        users_count = User.query.filter_by(role='user').count()
        lots_count = ParkingLot.query.count()
        spots_count = ParkingSpot.query.count()
        available = ParkingSpot.query.filter_by(status='A').count()
        occupied = ParkingSpot.query.filter_by(status='O').count()
        reservations_count = Reservation.query.count()
        
        return jsonify({
            'message': 'Test Summary Data',
            'statistics': {
                'total_users': users_count,
                'total_lots': lots_count,
                'total_spots': spots_count,
                'available_spots': available,
                'occupied_spots': occupied,
                'total_reservations': reservations_count
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

register_auth_routes(app)
register_api_routes(app)
register_admin_routes(app)
register_user_routes(app)

if __name__ == '__main__':
    try:
        with app.app_context():
            db.create_all()    
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin', email='admin@test.com', phone_number='9999999999', address='Admin Office', pincode='000000', role='admin')
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("✅ Admin user created successfully!")
        
        print("Parking App Server starting on http://localhost:5000")
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"❌ Error starting Flask app: {e}")
        import traceback
        traceback.print_exc()