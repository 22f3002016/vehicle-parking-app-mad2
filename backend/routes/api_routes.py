from flask import jsonify, request
from models import db, User, ParkingLot, ParkingSpot, Reservation
from auth import token_required, admin_required, user_required
from cache import cache_get, cache_set, cache_delete, cache_clear_pattern, cache_key
from datetime import datetime

def register_api_routes(app):
    
    @app.route('/api/users')
    @token_required
    @admin_required
    def get_all_users():
        users = User.query.all()
        return jsonify([user.to_dict() for user in users]), 200

    @app.route('/api/lots')
    @token_required
    def get_lots():
        # Try cache first
        cache_key_name = cache_key("api", "lots")
        cached_result = cache_get(cache_key_name)
        if cached_result:
            return jsonify(cached_result), 200
        
        lots = ParkingLot.query.all()
        result = []
        for lot in lots:
            free = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
            result.append({
                'id': lot.id,
                'prime_location_name': lot.prime_location_name,
                'address': lot.address,
                'pin_code': lot.pin_code,
                'price_per_hour': lot.price_per_hour,
                'number_of_spots': lot.number_of_spots,
                'available_spots': free
            })
        
        # Cache for 60 seconds
        cache_set(cache_key_name, result, 60)
        return jsonify(result), 200

    @app.route('/api/spots')
    @token_required
    def get_spots():
        try:
            # Try cache first
            cache_key_name = cache_key("api", "spots")
            cached_result = cache_get(cache_key_name)
            if cached_result:
                return jsonify(cached_result), 200
            
            spots = ParkingSpot.query.join(ParkingLot).all()
            result = []
            for spot in spots:
                lot = db.session.get(ParkingLot, spot.lot_id)
                result.append({
                    'id': spot.id,
                    'lot_id': spot.lot_id,
                    'spot_number': spot.spot_number,
                    'status': spot.status,
                    'lot_name': lot.prime_location_name if lot else 'Unknown',
                    'lot_address': lot.address if lot else 'Unknown'
                })
            
            # Cache for 30 seconds (spots change frequently)
            cache_set(cache_key_name, result, 30)
            return jsonify(result), 200
        except Exception as e:
            print(f"Error in get_spots: {e}")
            return jsonify({'error': 'Failed to fetch spots', 'message': str(e)}), 500

    @app.route('/api/status')
    @token_required
    @admin_required
    def status():
        users = User.query.count()
        lots = ParkingLot.query.count()
        spots = ParkingSpot.query.count()
        
        return jsonify({
            'users': users,
            'lots': lots,
            'spots': spots
        }), 200

    @app.route('/api/reserve', methods=['POST'])
    @token_required
    @user_required
    def reserve_spot():
        data = request.get_json()
        lot_id = data.get('lot_id')
        if not lot_id:
            return jsonify({'message': 'Missing lot_id'}), 400
        
        active_res = Reservation.query.filter_by(user_id=request.user_id, leaving_timestamp=None).first()
        if active_res:
            return jsonify({'message': 'You already have an active reservation'}), 400
        
        spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()
        if not spot:
            return jsonify({'message': 'No available spots in this lot'}), 400
        
        reservation = Reservation(
            user_id=request.user_id, 
            spot_id=spot.id, 
            parking_timestamp=datetime.utcnow()
        )
        spot.status = 'O'
        
        user = db.session.get(User, request.user_id)
        if user:
            user.last_visit = datetime.utcnow()
        
        db.session.add(reservation)
        db.session.commit()
        
        # Clear cache after spot reservation
        cache_clear_pattern("api:spots*")
        cache_clear_pattern("api:lots*")
        
        return jsonify({
            'message': 'Parking spot allocated successfully',
            'reservation': {
                'id': reservation.id,
                'spot_id': reservation.spot_id,
                'spot_number': spot.spot_number,
                'parking_timestamp': reservation.parking_timestamp.isoformat(),
                'parking_cost': reservation.parking_cost
            }
        }), 201

    @app.route('/api/release', methods=['POST'])
    @token_required
    @user_required
    def release_spot():
        data = request.get_json()
        reservation_id = data.get('reservation_id')
        if not reservation_id:
            return jsonify({'message': 'Missing reservation_id'}), 400
        
        reservation = Reservation.query.filter_by(id=reservation_id, user_id=request.user_id, leaving_timestamp=None).first()
        if not reservation:
            return jsonify({'message': 'Active reservation not found'}), 404
        
        reservation.leaving_timestamp = datetime.utcnow()
        spot = db.session.get(ParkingSpot, reservation.spot_id)
        lot = db.session.get(ParkingLot, spot.lot_id)
        
        duration_hours = (reservation.leaving_timestamp - reservation.parking_timestamp).total_seconds() / 3600
        if duration_hours < 1:
            duration_hours = 1
        
        calculated_cost = round(duration_hours * lot.price_per_hour, 2)
        reservation.parking_cost = calculated_cost
        spot.status = 'A'
        
        db.session.commit()
        
        # Clear cache after spot release
        cache_clear_pattern("api:spots*")
        cache_clear_pattern("api:lots*")
        
        return jsonify({
            'message': 'Parking session completed successfully', 
            'parking_cost': calculated_cost,
            'duration_hours': round(duration_hours, 2)
        }), 200

    @app.route('/api/search', methods=['GET'])
    @token_required
    def search_parking():
        query = request.args.get('q', '').strip()
        search_type = request.args.get('type', 'lots')
        
        if not query:
            return jsonify({'message': 'Search query is required'}), 400
        
        query_lower = query.lower()
        lots = ParkingLot.query.all()
        results = []
        
        for lot in lots:
            if (lot.prime_location_name and query_lower in lot.prime_location_name.lower()) or \
               (lot.address and query_lower in lot.address.lower()) or \
               (lot.pin_code and query in lot.pin_code):
                
                available_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
                if search_type == 'available' and available_spots == 0:
                    continue
                
                results.append({
                    'id': lot.id,
                    'prime_location_name': lot.prime_location_name,
                    'address': lot.address,
                    'pin_code': lot.pin_code,
                    'price_per_hour': lot.price_per_hour,
                    'number_of_spots': lot.number_of_spots,
                    'available_spots': available_spots
                })
        
        return jsonify({
            'query': query,
            'results': results,
            'count': len(results)
        }), 200