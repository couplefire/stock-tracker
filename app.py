from flask import Flask, render_template, jsonify, request
from app.models import Database
from app.stock_tracker import StockTracker
import os
from datetime import datetime
import atexit
import threading
from dotenv import load_dotenv

load_dotenv()

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] app.py module loading, PID: {os.getpid()}")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Initialize database
db = Database()

# Global tracker instance - ensure only one is created
_tracker_instance = None
_tracker_lock = threading.Lock()

def get_tracker():
    """Get or create the single tracker instance"""
    global _tracker_instance
    with _tracker_lock:
        if _tracker_instance is None:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Creating tracker instance, PID: {os.getpid()}")
            # For low-resource environments (1 CPU, 1GB RAM), use only 1 concurrent check
            # This prevents multiple browser instances from overwhelming the system
            max_concurrent = int(os.environ.get('MAX_CONCURRENT_CHECKS', '1'))
            check_interval = int(os.environ.get('CHECK_INTERVAL', '60'))  # Default to 60s for low resources
            _tracker_instance = StockTracker(
                check_interval=check_interval, 
                max_concurrent_checks=max_concurrent
            )
    return _tracker_instance

# Initialize tracker at module level if we're in the main process
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Initializing tracker in main process, PID: {os.getpid()}")
    tracker = get_tracker()
    tracker.start()
else:
    tracker = None

# Register cleanup
def cleanup_tracker():
    if tracker and tracker.running:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Cleaning up tracker, PID: {os.getpid()}")
        tracker.stop()

atexit.register(cleanup_tracker)

def ensure_tracker():
    """Ensure tracker is initialized and started"""
    global tracker
    if tracker is None:
        tracker = get_tracker()
        if not tracker.running:
            tracker.start()
    return tracker

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
        
        # Queue the new item for checking (non-blocking)
        try:
            ensure_tracker().force_check_item(item_id)
            check_status = 'queued'
        except:
            check_status = 'pending'
        
        return jsonify({
            'id': item_id, 
            'message': 'Item added successfully',
            'check_status': check_status
        }), 201
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
        
        # Queue the updated item for checking (non-blocking)
        try:
            ensure_tracker().force_check_item(item_id)
            check_status = 'queued'
        except:
            check_status = 'pending'
        
        return jsonify({
            'message': 'Item updated successfully',
            'check_status': check_status
        }), 200
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
    try:
        # Instead of waiting for the check to complete, just queue it
        if ensure_tracker().force_check_item(item_id):
            return jsonify({
                'message': 'Check queued successfully',
                'status': 'queued',
                'note': 'The item will be checked shortly'
            }), 202  # 202 Accepted - request accepted for processing
        else:
            return jsonify({'error': 'Item not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to queue check: {str(e)}'}), 500

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
    current_tracker = ensure_tracker()
    return jsonify({
        'running': current_tracker.running,
        'check_interval': current_tracker.check_interval
    })

if __name__ == '__main__':
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Main block executing, PID: {os.getpid()}")
    
    # Get debug mode from environment variable
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # If debug mode, use the reloader properly
    if debug_mode:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running in debug mode")
        # Let Flask's reloader handle everything
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=True)
    else:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running in production mode")
        # In production mode, manually start the tracker since there's no reloader
        tracker = get_tracker()
        if not tracker.running:
            tracker.start()
        
        try:
            app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
        finally:
            if tracker and tracker.running:
                tracker.stop() 
