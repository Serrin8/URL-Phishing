from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import hashlib
import re
import pickle
import numpy as np
from urllib.parse import urlparse

app = Flask(__name__)
CORS(app)

model = pickle.load(open("ensemble_model.pkl", "rb"))


TRUSTED_DOMAINS = [
    "amazon.in",
    "amazon.com",
    "jiomart.com",
    "flipkart.com",
    "meesho.com",
    "google.com",
    "youtube.com",
     "surveysparrow.com",
      "rbi.org.in",
    "gov.in",
    "onelink.me",
    "sprw.io"
]

SHORTENER_DOMAINS = [
    "bit.ly",
    "tinyurl.com",
    "mlpl.link",
    "t.co",
    "goo.gl"
]

BRANDS = [
    "amazon",
    "flipkart",
    "paypal",
    "netflix",
    "facebook",
    "google",
    "apple"
]


db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'trustnet_db'
}

def create_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        print("DB Connection Error:", e)
        return None

def init_database():

    connection = create_connection()

    if connection:

        cursor = connection.cursor()

        cursor.execute("CREATE DATABASE IF NOT EXISTS trustnet_db")
        cursor.execute("USE trustnet_db")

        create_table_query = """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            phone VARCHAR(20) UNIQUE,
            email VARCHAR(100) UNIQUE,
            password VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        cursor.execute(create_table_query)

        connection.commit()
        cursor.close()
        connection.close()

        print("Database initialized")



def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email)

def validate_phone(phone):
    pattern = r'^\+?[\d\s-]{10,}$'
    return re.match(pattern, phone)

def get_domain(url):
    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "")

def detect_fake_brand(domain):

    for brand in BRANDS:

        if brand in domain:

            for trusted in TRUSTED_DOMAINS:

                if brand in trusted and trusted in domain:
                    return False

            return True

    return False


def extract_features(url):

    parsed = urlparse(url)

    features = {}

    features["length_url"] = len(url)
    features["length_hostname"] = len(parsed.netloc)
    features["ip"] = 1 if re.match(r"\d+\.\d+\.\d+\.\d+", parsed.netloc) else 0
    features["nb_dots"] = url.count(".")
    features["nb_hyphens"] = url.count("-")
    features["nb_at"] = url.count("@")
    features["nb_qm"] = url.count("?")
    features["nb_and"] = url.count("&")
    features["nb_or"] = url.count("|")
    features["nb_eq"] = url.count("=")
    features["nb_underscore"] = url.count("_")
    features["nb_tilde"] = url.count("~")
    features["nb_percent"] = url.count("%")
    features["nb_slash"] = url.count("/")
    features["nb_star"] = url.count("*")
    features["nb_colon"] = url.count(":")
    features["nb_comma"] = url.count(",")
    features["nb_semicolumn"] = url.count(";")
    features["nb_dollar"] = url.count("$")
    features["nb_space"] = url.count(" ")
    features["nb_www"] = url.count("www")
    features["nb_com"] = url.count(".com")
    features["nb_dslash"] = url.count("//")
    features["http_in_path"] = 1 if "http" in parsed.path else 0
    features["https_token"] = 1 if "https" in url else 0

    while len(features) < 87:
        features[f"f{len(features)}"] = 0

    return list(features.values())



@app.route('/signup', methods=['POST'])
def signup():

    try:

        data = request.get_json()

        required = ['name', 'phone', 'email', 'password']

        for field in required:
            if field not in data or not data[field]:
                return jsonify({"success": False, "message": f"{field} required"}), 400

        if not validate_email(data['email']):
            return jsonify({"success": False, "message": "Invalid email"}), 400

        if not validate_phone(data['phone']):
            return jsonify({"success": False, "message": "Invalid phone"}), 400

        if len(data['password']) < 6:
            return jsonify({"success": False, "message": "Password min 6 chars"}), 400

        connection = create_connection()

        cursor = connection.cursor(dictionary=True)

        check_query = "SELECT id FROM users WHERE email=%s OR phone=%s"
        cursor.execute(check_query, (data['email'], data['phone']))

        if cursor.fetchone():
            return jsonify({"success": False, "message": "User exists"}), 409

        insert_query = """
        INSERT INTO users (name,phone,email,password)
        VALUES (%s,%s,%s,%s)
        """

        cursor.execute(insert_query, (
            data['name'],
            data['phone'],
            data['email'],
            hash_password(data['password'])
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({"success": True, "message": "User registered"}), 201

    except Exception as e:

        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/login', methods=['POST'])
def login():

    try:

        data = request.get_json()

        connection = create_connection()

        cursor = connection.cursor(dictionary=True)

        query = """
        SELECT id,name,email,phone
        FROM users
        WHERE email=%s AND password=%s
        """

        cursor.execute(query, (
            data['email'],
            hash_password(data['password'])
        ))

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user:
            return jsonify({
                "success": True,
                "message": "Login success",
                "user": user
            })

        return jsonify({
            "success": False,
            "message": "Invalid credentials"
        }), 401

    except Exception as e:

        return jsonify({"success": False, "error": str(e)}), 500




@app.route('/predict', methods=['POST'])
def predict():

    try:

        data = request.get_json()
        url = data.get("url")

        if not url:
            return jsonify({"error": "URL required"}), 400

        if not url.startswith("http"):
            url = "http://" + url

        domain = get_domain(url)


        for trusted in TRUSTED_DOMAINS:
            if trusted in domain:
                return jsonify({
                    "url": url,
                    "prediction": "legitimate",
                    "reason": "trusted domain"
                })


        for short in SHORTENER_DOMAINS:
            if short in domain:
                return jsonify({
                    "url": url,
                    "prediction": "suspicious",
                    "reason": "shortened link"
                })

  
        if detect_fake_brand(domain):
            return jsonify({
                "url": url,
                "prediction": "phishing",
                "reason": "fake brand domain"
            })


        features = extract_features(url)

        features = np.array(features).reshape(1, -1)

        prediction = model.predict(features)[0]

        result = "phishing" if prediction == 1 else "legitimate"

        return jsonify({
            "url": url,
            "prediction": result
        })

    except Exception as e:

        return jsonify({"error": str(e)}), 500


@app.route('/test', methods=['GET'])
def test():
    return jsonify({
        "message": "TrustNet API Running",
        "status": "OK"
    })


if __name__ == "__main__":

    init_database()

    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True
    )