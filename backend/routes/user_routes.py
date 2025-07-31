from flask import jsonify, request
from models import db, User, ParkingLot, ParkingSpot, Reservation
from auth import token_required, user_required

def register_user_routes(app):
    
    @app.route('/user/dashboard')
    @token_required
    @user_required
    def user_dashboard_page():
        try:
            reservations = Reservation.query.filter_by(user_id=request.user_id).order_by(Reservation.parking_timestamp.desc()).limit(5).all()
            
            lots = ParkingLot.query.all()
            lots_info = []
            for lot in lots:
                free = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
                lots_info.append({
                    'id': lot.id,
                    'prime_location_name': lot.prime_location_name,
                    'address': lot.address,
                    'pin_code': lot.pin_code,
                    'price_per_hour': lot.price_per_hour,
                    'available_spots': free
                })
            
            user = db.session.get(User, request.user_id)
            
            return jsonify({
                'message': 'User Dashboard',
                'user': user.to_dict(),
                'my_reservations': [
                    {
                        'id': res.id,
                        'spot_id': res.spot_id,
                        'parking_timestamp': res.parking_timestamp.isoformat() if res.parking_timestamp else None,
                        'leaving_timestamp': res.leaving_timestamp.isoformat() if res.leaving_timestamp else None,
                        'parking_cost': res.parking_cost
                    } for res in reservations
                ],
                'available_parking_lots': lots_info
            }), 200
        except Exception as e:
            return jsonify({'error': 'Failed to load user dashboard', 'message': str(e)}), 500

    @app.route('/api/user/dashboard')
    @token_required
    @user_required
    def api_user_dashboard():
        reservations = Reservation.query.filter_by(user_id=request.user_id).order_by(Reservation.parking_timestamp.desc()).limit(5).all()
        
        lots = ParkingLot.query.all()
        lots_info = []
        for lot in lots:
            free = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
            lots_info.append({
                'id': lot.id,
                'prime_location_name': lot.prime_location_name,
                'address': lot.address,
                'pin_code': lot.pin_code,
                'price_per_hour': lot.price_per_hour,
                'available_spots': free
            })
        
        user = db.session.get(User, request.user_id)
        
        return jsonify({
            'message': 'User Dashboard',
            'user': user.to_dict(),
            'my_reservations': [
                {
                    'id': res.id,
                    'spot_id': res.spot_id,
                    'parking_timestamp': res.parking_timestamp.isoformat() if res.parking_timestamp else None,
                    'leaving_timestamp': res.leaving_timestamp.isoformat() if res.leaving_timestamp else None,
                    'parking_cost': res.parking_cost
                } for res in reservations
            ],
            'available_parking_lots': lots_info
        }), 200

    @app.route('/api/user/profile')
    @token_required
    @user_required
    def get_user_profile():
        user = db.session.get(User, request.user_id)
        return jsonify({
            'user': user.to_dict()
        }), 200

    @app.route('/api/user/reservations')
    @token_required
    @user_required
    def get_user_reservations():
        reservations = Reservation.query.filter_by(user_id=request.user_id).order_by(Reservation.parking_timestamp.desc()).all()
        
        return jsonify({
            'reservations': [
                {
                    'id': res.id,
                    'spot_id': res.spot_id,
                    'parking_timestamp': res.parking_timestamp.isoformat() if res.parking_timestamp else None,
                    'leaving_timestamp': res.leaving_timestamp.isoformat() if res.leaving_timestamp else None,
                    'parking_cost': res.parking_cost,
                    'status': 'active' if not res.leaving_timestamp else 'completed'
                } for res in reservations
            ]
        }), 200