from flask import Flask, request, jsonify
from flask_cors import CORS
from urllib.parse import urlparse
import re

app = Flask(__name__)
CORS(app)  
def extract_features(url):
    features = {}
    
    features['url_length'] = len(url)
    
    features['num_digits'] = sum(c.isdigit() for c in url)
    
    features['num_special_chars'] = sum(not c.isalnum() for c in url)
    
    try:
        parsed = urlparse(url)
        features['has_ip'] = 1 if re.match(r'^\d+\.\d+\.\d+\.\d+$', parsed.netloc) else 0
    except:
        features['has_ip'] = 0
    
    features['has_at'] = 1 if '@' in url else 0
    
    try:
        parsed = urlparse(url)
        subdomains = parsed.netloc.split('.')
        features['num_subdomains'] = len(subdomains) - 2  # Subtract domain and TLD
    except:
        features['num_subdomains'] = 0
    
    features['is_https'] = 1 if url.startswith('https') else 0
    
    shorteners = ['bit.ly', 'goo.gl', 'tinyurl', 't.co', 'ow.ly', 'is.gd', 'buff.ly', 'adf.ly', 'bit.do']
    features['is_shortened'] = 1 if any(shortener in url for shortener in shorteners) else 0
    
    suspicious_keywords = ['secure', 'account', 'webscr', 'login', 'signin', 'verify', 'banking', 'confirm', 'password']
    features['suspicious_words'] = sum(1 for word in suspicious_keywords if word in url.lower())
    
    return features

def extract_url_from_message(message):
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*\??[/\w\.-=&%]*'
    urls_found = re.findall(url_pattern, message)
    return urls_found[0] if urls_found else None


@app.route('/', methods=['GET'])
def test_url():
    return "Test OK"    

@app.route('/analyze', methods=['POST'])
def analyze_url():
    data = request.get_json()
    
    if not data or 'message' not in data:
        return jsonify({'error': 'Please provide a message containing a URL'}), 400
    
    message = data['message']
    
    url = extract_url_from_message(message)
    
    if not url:
        return jsonify({'error': 'No URL found in the provided message'}), 400
    
    features = extract_features(url)
    
    features['extracted_url'] = url
    
    return jsonify(features)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)