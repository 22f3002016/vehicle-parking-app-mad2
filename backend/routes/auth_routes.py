from flask import jsonify, request
from models import db, User
from auth import generate_token, token_required

def register_auth_routes(app):
    
    @app.route('/auth/register', methods=['POST'])
    def register():
        data = request.get_json()
        
        if not data or not all(k in data for k in ['username', 'email', 'phone_number', 'password', 'address', 'pincode']):
            return jsonify({'message': 'Missing required fields'}), 400
        
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'message': 'Username already exists'}), 400
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'message': 'Email already exists'}), 400
        
        user = User(
            username=data['username'], 
            email=data['email'],
            phone_number=data['phone_number'],
            address=data['address'],
            pincode=data['pincode'],
            role='user'
        )
        user.set_password(data['password'])
        
        try:
            db.session.add(user)
            db.session.commit()
            token = generate_token(user.id, user.username, user.role)
            return jsonify({
                'message': 'User registered successfully',
                'token': token,
                'user': user.to_dict(),
                'redirect': '/user/dashboard'
            }), 201
        except:
            db.session.rollback()
            return jsonify({'message': 'Registration failed'}), 500

    @app.route('/auth/login', methods=['POST'])
    def login():
        data = request.get_json()
        
        if not data or not all(k in data for k in ['username', 'password']):
            return jsonify({'message': 'Missing username or password'}), 400
        
        user = User.query.filter_by(username=data['username']).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'message': 'Invalid username or password'}), 401
        
        token = generate_token(user.id, user.username, user.role)
        redirect_url = '/admin/dashboard' if user.role == 'admin' else '/user/dashboard'
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': user.to_dict(),
            'redirect': redirect_url
        }), 200

    @app.route('/auth/admin-login', methods=['POST'])
    def admin_login():
        data = request.get_json()
        
        if not data or not all(k in data for k in ['username', 'password']):
            return jsonify({'message': 'Missing username or password'}), 400
        
        user = User.query.filter_by(username=data['username'], role='admin').first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'message': 'Invalid admin credentials'}), 401
        
        token = generate_token(user.id, user.username, user.role)
        return jsonify({
            'message': 'Admin login successful',
            'token': token,
            'user': user.to_dict(),
            'redirect': '/admin/dashboard'
        }), 200

    @app.route('/auth/logout', methods=['POST'])
    @token_required
    def logout():
        return jsonify({
            'message': 'Logged out successfully',
            'redirect': '/'
        }), 200