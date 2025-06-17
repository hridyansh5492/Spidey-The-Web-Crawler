from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from crawler import WebCrawler
import json

app = Flask(__name__)
CORS(app)

# Initialize crawler
crawler = WebCrawler()

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/crawl', methods=['POST'])
def start_crawl():
    """Start a new crawling session"""
    try:
        data = request.get_json()
        
        start_url = data.get('url')
        max_pages = int(data.get('max_pages', 50))
        delay = float(data.get('delay', 1.0))
        
        if not start_url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Add http:// if no protocol specified
        if not start_url.startswith(('http://', 'https://')):
            start_url = 'http://' + start_url
        
        session_id = crawler.start_crawl(start_url, max_pages, delay)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Crawling started successfully'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Get all crawl sessions"""
    try:
        sessions = crawler.get_sessions()
        return jsonify({'sessions': sessions})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions/<int:session_id>/pages', methods=['GET'])
def get_session_pages(session_id):
    """Get pages for a specific session"""
    try:
        pages = crawler.get_session_pages(session_id)
        return jsonify({'pages': pages})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions/<int:session_id>/status', methods=['GET'])
def get_session_status(session_id):
    """Get status of a specific session"""
    try:
        sessions = crawler.get_sessions()
        session = next((s for s in sessions if s['id'] == session_id), None)
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        return jsonify({'session': session})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

'''Export Error in this
@app.route('/api/sessions/<int:session_id>/export', methods=['GET'])
def export_session_data(session_id):
    """Export session data as JSON"""
    try:
        sessions = crawler.get_sessions()
        session = next((s for s in sessions if s['id'] == session_id), None)
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        pages = crawler.get_session_pages(session_id)
        
        export_data = {
            'session': session,
            'pages': pages,
            'export_time': crawler._get_current_timestamp()
        }
        
        return jsonify(export_data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500'''

@app.route('/api/sessions/<int:session_id>/export', methods=['GET'])
def export_session_data(session_id):
    try:
        export_path = crawler.export_session_data(session_id, format_type='json')

        if not export_path or not os.path.exists(export_path):
            return jsonify({'error': 'Export failed or file not found'}), 500

        # Load the exported file and return its JSON content
        with open(export_path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))

    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get overall crawling statistics"""
    try:
        import sqlite3
        
        conn = sqlite3.connect(crawler.db_path)
        cursor = conn.cursor()
        
        # Get total sessions
        cursor.execute('SELECT COUNT(*) FROM crawl_sessions')
        total_sessions = cursor.fetchone()[0]
        
        # Get total pages crawled
        cursor.execute('SELECT COUNT(*) FROM pages')
        total_pages = cursor.fetchone()[0]
        
        # Get total links found
        cursor.execute('SELECT COUNT(*) FROM links')
        total_links = cursor.fetchone()[0]
        
        # Get active sessions
        cursor.execute("SELECT COUNT(*) FROM crawl_sessions WHERE status = 'running'")
        active_sessions = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_sessions': total_sessions,
            'total_pages': total_pages,
            'total_links': total_links,
            'active_sessions': active_sessions
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Create database directory if it doesn't exist
    os.makedirs('database', exist_ok=True)
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)