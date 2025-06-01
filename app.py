from flask import Flask, render_template, jsonify, request
from app.models import Database
from app.stock_tracker import StockTracker
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Initialize database and tracker
db = Database()
tracker = StockTracker(check_interval=10)

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/items', methods=['GET'])
def get_items():
    """Get all tracked items"""
    items = db.get_all_items()
    for item in items:
        # Format timestamps for display
        if item['last_checked']:
            item['last_checked'] = datetime.fromisoformat(item['last_checked']).strftime('%Y-%m-%d %H:%M:%S')
        if item['created_at']:
            item['created_at'] = datetime.fromisoformat(item['created_at']).strftime('%Y-%m-%d %H:%M:%S')
    return jsonify(items)

@app.route('/api/items', methods=['POST'])
def add_item():
    """Add a new item to track"""
    data = request.json
    
    # Validate required fields
    required_fields = ['url', 'name', 'rule_pattern', 'rule_count']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    try:
        item_id = db.add_item(
            url=data['url'],
            name=data['name'],
            rule_pattern=data['rule_pattern'],
            rule_count=int(data['rule_count'])
        )
        
        # Force check the new item
        tracker.force_check_item(item_id)
        
        return jsonify({'id': item_id, 'message': 'Item added successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    """Update an existing item"""
    data = request.json
    
    # Validate required fields
    required_fields = ['url', 'name', 'rule_pattern', 'rule_count']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    try:
        db.update_item(
            item_id=item_id,
            url=data['url'],
            name=data['name'],
            rule_pattern=data['rule_pattern'],
            rule_count=int(data['rule_count'])
        )
        
        # Force check the updated item
        tracker.force_check_item(item_id)
        
        return jsonify({'message': 'Item updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    """Delete an item"""
    try:
        db.delete_item(item_id)
        return jsonify({'message': 'Item deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/items/<int:item_id>/check', methods=['POST'])
def force_check_item(item_id):
    """Force check an item immediately"""
    if tracker.force_check_item(item_id):
        return jsonify({'message': 'Check initiated'}), 200
    else:
        return jsonify({'error': 'Item not found'}), 404

@app.route('/api/emails', methods=['GET'])
def get_emails():
    """Get all email addresses"""
    emails = db.get_all_emails()
    return jsonify(emails)

@app.route('/api/emails', methods=['POST'])
def add_email():
    """Add a new email address"""
    data = request.json
    
    if 'email' not in data:
        return jsonify({'error': 'Missing required field: email'}), 400
    
    # Basic email validation
    email = data['email'].strip()
    if not '@' in email or not '.' in email.split('@')[1]:
        return jsonify({'error': 'Invalid email format'}), 400
    
    try:
        db.add_email(email)
        return jsonify({'message': 'Email added successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emails/<int:email_id>', methods=['DELETE'])
def delete_email(email_id):
    """Delete an email address"""
    try:
        db.delete_email(email_id)
        return jsonify({'message': 'Email deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tracker/status', methods=['GET'])
def get_tracker_status():
    """Get tracker status"""
    return jsonify({
        'running': tracker.running,
        'check_interval': tracker.check_interval
    })

if __name__ == '__main__':
    # Start the tracker
    tracker.start()
    
    # Run the Flask app
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    finally:
        # Stop the tracker when app exits
        tracker.stop() 