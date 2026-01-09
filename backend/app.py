from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)
# Ensure an absolute path for SQLite to avoid 'unable to open database file' errors
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_DIR = os.path.join(ROOT_DIR, 'data')
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, 'app.db')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{DB_PATH}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    details = db.Column(db.Text)
    confidence = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def as_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'details': self.details,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat()
        }

@app.route('/api/health')
def health():
    return jsonify({'status':'ok'})

@app.route('/api/incidents')
def incidents():
    items = Incident.query.order_by(Incident.created_at.desc()).limit(20).all()
    return jsonify([i.as_dict() for i in items])

@app.route('/api/incidents', methods=['POST'])
def create_incident():
    body = request.json or {}
    i = Incident(title=body.get('title','Alert'), details=body.get('details',''), confidence=float(body.get('confidence',0)))
    db.session.add(i)
    db.session.commit()
    return jsonify(i.as_dict())

@app.route('/api/compatibility', methods=['POST'])
def check_compat():
    payload = request.json or {}
    # simple heuristic
    score = 50
    if payload.get('user_auth'): score += 20
    if payload.get('file_access'): score += 20
    if payload.get('email'): score += 5
    if payload.get('psych'): score += 3
    if payload.get('usb'): score += 2
    score = min(100,score)
    status = 'High' if score >= 80 else 'Moderate' if score >= 50 else 'Low'
    return jsonify({'score':score, 'status': status})

if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    # Ensure DB tables exist within app context
    with app.app_context():
        db.create_all()
        # Seed a demo incident if none exist
        if Incident.query.count() == 0:
            demo = Incident(title='Demo Alert: Suspicious Export', details='Large export detected (50GB).', confidence=0.94)
            db.session.add(demo)
            db.session.commit()
    # Run without the reloader in dev to avoid forking issues in some Windows environments
    app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False)
