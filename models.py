from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class QueryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_type = db.Column(db.String(100), nullable=False)
    case_number = db.Column(db.String(100), nullable=False)
    filing_year = db.Column(db.String(10), nullable=False)
    query_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    success = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.Text)
    raw_response = db.Column(db.Text)
    
    def __repr__(self):
        return f'<QueryLog {self.case_type}/{self.case_number}/{self.filing_year}>'

class CaseData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_type = db.Column(db.String(100), nullable=False)
    case_number = db.Column(db.String(100), nullable=False)
    filing_year = db.Column(db.String(10), nullable=False)
    parties_petitioner = db.Column(db.Text)
    parties_respondent = db.Column(db.Text)
    filing_date = db.Column(db.String(50))
    next_hearing_date = db.Column(db.String(50))
    case_status = db.Column(db.String(100))
    judge_name = db.Column(db.String(200))
    order_pdf_links = db.Column(db.Text)  # JSON string of links
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CaseData {self.case_type}/{self.case_number}/{self.filing_year}>'
