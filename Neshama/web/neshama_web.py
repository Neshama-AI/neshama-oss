"""
Neshama Web Application v0.4
"""

import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# API Configuration
API_BASE_URL = os.environ.get('NESAMA_API_URL', 'https://api.neshama.ai')
API_KEY = os.environ.get('NESAMA_API_KEY', '')

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'version': '0.4.0'})

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat API endpoint"""
    data = request.get_json()
    message = data.get('message', '')
    
    # TODO: Integrate with Neshama API
    response = {
        'reply': f'Neshama v0.4 received: {message}',
        'version': '0.4.0'
    }
    return jsonify(response)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
