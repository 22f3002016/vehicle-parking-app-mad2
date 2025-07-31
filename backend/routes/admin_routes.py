from flask import jsonify, request
from models import db, User, ParkingLot, ParkingSpot, Reservation
from auth import token_required, admin_required

def register_admin_routes(app):
    
    @app.route('/admin/dashboard')
    @token_required
    @admin_required
    def admin_dashboard():
        try:
            users_count = User.query.filter_by(role='user').count()
            lots_count = ParkingLot.query.count()
            spots_count = ParkingSpot.query.count()
            available = ParkingSpot.query.filter_by(status='A').count()
            occupied = ParkingSpot.query.filter_by(status='O').count()
            reservations_count = Reservation.query.count()
            
            try:
                recent = User.query.filter_by(role='user').order_by(User.created_at.desc()).limit(5).all()
            except:
                recent = User.query.filter_by(role='user').limit(5).all()
            
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
                    'number_of_spots': lot.number_of_spots,
                    'available_spots': free,
                    'utilization': round((lot.number_of_spots - free) / lot.number_of_spots * 100, 2) if lot.number_of_spots > 0 else 0
                })
            
            response_data = {
                'message': 'Admin Dashboard',
                'statistics': {
                    'total_users': users_count,
                    'total_lots': lots_count,
                    'total_spots': spots_count,
                    'available_spots': available,
                    'occupied_spots': occupied,
                    'total_reservations': reservations_count
                },
                'recent_users': [user.to_dict() for user in recent],
                'parking_lots': lots_info
            }
            
            return jsonify(response_data), 200
        except Exception as e:
            return jsonify({'error': 'Failed to load admin dashboard', 'message': str(e)}), 500

    @app.route('/api/admin/lots', methods=['POST'])
    @token_required 
    @admin_required
    def create_lot():
        data = request.get_json()
        lot = ParkingLot(
            prime_location_name=data['prime_location_name'],
            address=data['address'],
            pin_code=data['pin_code'],
            price_per_hour=data['price_per_hour'],
            number_of_spots=data['number_of_spots']
        )
        db.session.add(lot)
        db.session.commit()
        
        for i in range(1, lot.number_of_spots + 1):
            spot = ParkingSpot(lot_id=lot.id, spot_number=f"A{i}", status='A')
            db.session.add(spot)
        db.session.commit()
        
        return jsonify({'message': 'Lot created', 'lot_id': lot.id}), 201

    @app.route('/api/admin/lots/<int:lot_id>', methods=['PUT'])
    @token_required
    @admin_required
    def edit_lot(lot_id):
        lot = ParkingLot.query.get_or_404(lot_id)
        data = request.get_json()
        old_total = lot.number_of_spots
        
        lot.prime_location_name = data.get('prime_location_name', lot.prime_location_name)
        lot.address = data.get('address', lot.address)
        lot.pin_code = data.get('pin_code', lot.pin_code)
        lot.price_per_hour = data.get('price_per_hour', lot.price_per_hour)
        new_total = data.get('number_of_spots', old_total)
        if new_total > old_total:
            for i in range(old_total + 1, new_total + 1):
                spot = ParkingSpot(lot_id=lot.id, spot_number=f"A{i}", status='A')
                db.session.add(spot)
        elif new_total < old_total:
            occupied = ParkingSpot.query.filter_by(lot_id=lot.id, status='O').count()
            if occupied > new_total:
                return jsonify({'message': 'Cannot reduce spots below occupied count'}), 400
            extra_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').order_by(ParkingSpot.id.desc()).limit(old_total - new_total).all()
            for spot in extra_spots:
                db.session.delete(spot)
        lot.number_of_spots = new_total
        db.session.commit()
        
        return jsonify({'message': 'Lot updated'}), 200

    @app.route('/api/admin/lots/<int:lot_id>', methods=['DELETE'])
    @token_required
    @admin_required
    def delete_lot(lot_id):
        lot = ParkingLot.query.get_or_404(lot_id)
        occupied = ParkingSpot.query.filter_by(lot_id=lot.id, status='O').count()
        if occupied > 0:
            return jsonify({'message': 'Cannot delete lot with occupied spots'}), 400
        ParkingSpot.query.filter_by(lot_id=lot.id).delete()
        db.session.delete(lot)
        db.session.commit()
        
        return jsonify({'message': 'Lot deleted'}), 200

    @app.route('/api/admin/lots', methods=['GET'])
    @token_required
    @admin_required
    def admin_list_lots():
        lots = ParkingLot.query.all()
        result = []
        for lot in lots:
            total = ParkingSpot.query.filter_by(lot_id=lot.id).count()
            available = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
            occupied = ParkingSpot.query.filter_by(lot_id=lot.id, status='O').count()
            result.append({
                'id': lot.id,
                'prime_location_name': lot.prime_location_name,
                'address': lot.address,
                'pin_code': lot.pin_code,
                'price_per_hour': lot.price_per_hour,
                'number_of_spots': lot.number_of_spots,
                'available_spots': available,
                'occupied_spots': occupied
            })
        return jsonify(result), 200

    @app.route('/api/admin/lots/<int:lot_id>', methods=['GET'])
    @token_required
    @admin_required
    def lot_details(lot_id):
        lot = ParkingLot.query.get_or_404(lot_id)
        spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
        spot_list = []
        for spot in spots:
            spot_list.append({
                'id': spot.id,
                'spot_number': spot.spot_number,
                'status': spot.status
            })
        return jsonify({
            'id': lot.id,
            'prime_location_name': lot.prime_location_name,
            'address': lot.address,
            'pin_code': lot.pin_code,
            'price_per_hour': lot.price_per_hour,
            'number_of_spots': lot.number_of_spots,
            'spots': spot_list
        }), 200

    @app.route('/api/admin/lots/<int:lot_id>/spots', methods=['GET'])
    @token_required
    @admin_required
    def admin_list_spots(lot_id):
        spots = ParkingSpot.query.filter_by(lot_id=lot_id).all()
        result = []
        for spot in spots:
            result.append({
                'id': spot.id,
                'spot_number': spot.spot_number,
                'status': spot.status
            })
        return jsonify(result), 200

    @app.route('/api/admin/users', methods=['GET'])
    @token_required
    @admin_required
    def admin_list_users():
        users = User.query.filter(User.role == 'user').all()
        result = []
        for user in users:
            reservation = Reservation.query.filter_by(user_id=user.id).order_by(Reservation.id.desc()).first()
            spot = None
            if reservation and reservation.leaving_timestamp is None:
                spot = reservation.spot_id
            result.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'current_spot': spot,
                'created_at': user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None
            })
        return jsonify(result), 200

    @app.route('/api/admin/search', methods=['GET'])
    @token_required
    @admin_required
    def admin_search():
        query = request.args.get('q', '').strip()
        search_type = request.args.get('type', 'all')  
        
        if not query:
            return jsonify({'message': 'Search query is required'}), 400
        
        results = {
            'lots': [],
            'users': [],
            'spots': []
        }
        
        query_lower = query.lower()
        
        if search_type in ['all', 'lots']:
            lots = ParkingLot.query.all()
            for lot in lots:
                if (lot.prime_location_name and query_lower in lot.prime_location_name.lower()) or \
                   (lot.address and query_lower in lot.address.lower()) or \
                   (lot.pin_code and query in lot.pin_code):
                    
                    total = ParkingSpot.query.filter_by(lot_id=lot.id).count()
                    available = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
                    occupied = ParkingSpot.query.filter_by(lot_id=lot.id, status='O').count()
                    
                    results['lots'].append({
                        'id': lot.id,
                        'prime_location_name': lot.prime_location_name,
                        'address': lot.address,
                        'pin_code': lot.pin_code,
                        'price_per_hour': lot.price_per_hour,
                        'number_of_spots': lot.number_of_spots,
                        'available_spots': available,
                        'occupied_spots': occupied
                    })
        
        if search_type in ['all', 'users']:
            users = User.query.filter(User.role == 'user').all()
            for user in users:
                if query_lower in user.username.lower() or \
                   query_lower in user.email.lower() or \
                   query in str(user.id):
                    
                    reservation = Reservation.query.filter_by(user_id=user.id).order_by(Reservation.id.desc()).first()
                    spot = None
                    if reservation and reservation.leaving_timestamp is None:
                        spot = reservation.spot_id
                    
                    results['users'].append({
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'current_spot': spot,
                        'created_at': user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None
                    })
        
        if search_type in ['all', 'spots']:
            spots = ParkingSpot.query.all()
            for spot in spots:
                if query_lower in spot.spot_number.lower() or query in str(spot.id):
                    lot = db.session.get(ParkingLot, spot.lot_id)
                    results['spots'].append({
                        'id': spot.id,
                        'spot_number': spot.spot_number,
                        'status': spot.status,
                        'lot_id': spot.lot_id,
                        'lot_name': lot.prime_location_name if lot else 'Unknown'
                    })
        
        return jsonify(results), 200

    @app.route('/api/admin/export-csv', methods=['POST'])
    @token_required
    @admin_required
    def export_csv():
        from celery_app import generate_parking_report
        from models import User
        
        # Get current admin user's email
        admin_user = User.query.get(request.user_id)
        admin_email = admin_user.email if admin_user else None
        
        if not admin_email:
            return jsonify({
                'message': 'Could not find admin email address',
                'status': 'error'
            }), 400
        
        task = generate_parking_report.delay(admin_email)
        
        return jsonify({
            'message': 'CSV export started',
            'task_id': task.id,
            'status': f'Your CSV report is being generated. You will receive an email at {admin_email} when ready.'
        }), 202