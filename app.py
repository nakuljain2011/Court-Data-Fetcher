from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from models import db, QueryLog, CaseData
from scraper import DelhiHighCourtScraper
from config import Config
import json
import os
from datetime import datetime, timezone
import logging
import traceback
from functools import wraps
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

# DEMO MODE CONFIGURATION
DEMO_MODE = True  # Set to True for demo video, False for real scraping

# Initialize database
db.init_app(app)

# Initialize scraper
scraper = DelhiHighCourtScraper()

# Global variable to store active scraping sessions
active_sessions = {}

def generate_demo_case_data(case_type, case_number, filing_year):
    """Generate realistic demo data for showcasing functionality"""
    
    # Create different case scenarios based on case type
    case_scenarios = {
        "Civil Appeal": {
            'parties_petitioner': 'M/s Delhi Construction Company Ltd.',
            'parties_respondent': 'Municipal Corporation of Delhi & Ors.',
            'filing_date': f'15-Jan-{filing_year}',
            'next_hearing_date': '25-Aug-2025',
            'case_status': 'Arguments concluded, judgment reserved',
            'judge_name': 'Hon\'ble Justice Rajesh Kumar',
        },
        "Criminal Appeal": {
            'parties_petitioner': f'Appellant No. {case_number}',
            'parties_respondent': 'State of Delhi',
            'filing_date': f'10-Mar-{filing_year}',
            'next_hearing_date': '30-Aug-2025',
            'case_status': 'Matter for final hearing',
            'judge_name': 'Hon\'ble Justice Priya Sharma',
        },
        "Writ Petition (Civil)": {
            'parties_petitioner': f'Citizen Petitioner {case_number}',
            'parties_respondent': 'Union of India & Ors.',
            'filing_date': f'05-Jun-{filing_year}',
            'next_hearing_date': '15-Sep-2025',
            'case_status': 'Notice issued, awaiting response',
            'judge_name': 'Hon\'ble Justice A.K. Mehta',
        }
    }
    
    # Get scenario data or use default
    scenario = case_scenarios.get(case_type, case_scenarios["Civil Appeal"])
    
    case_data = {
        'parties_petitioner': scenario['parties_petitioner'],
        'parties_respondent': scenario['parties_respondent'],
        'filing_date': scenario['filing_date'],
        'next_hearing_date': scenario['next_hearing_date'],
        'case_status': scenario['case_status'],
        'judge_name': scenario['judge_name'],
        'order_pdf_links': [
            {
                'url': 'https://example.com/demo_order.pdf',
                'text': f'Order dated 01-Aug-2025 in {case_type} {case_number}/{filing_year}',
                'type': 'Order'
            },
            {
                'url': 'https://example.com/demo_judgment.pdf', 
                'text': f'Judgment dated 15-Jul-2025',
                'type': 'Judgment'
            }
        ],
        'case_history': [
            {'date': f'15-Jan-{filing_year}', 'proceedings': f'{case_type} filed and registered'},
            {'date': f'20-Jan-{filing_year}', 'proceedings': 'Notice issued to respondent parties'},
            {'date': '05-Feb-2025', 'proceedings': 'Counter affidavit filed by respondent'},
            {'date': '15-Mar-2025', 'proceedings': 'Rejoinder filed by petitioner'},
            {'date': '01-Aug-2025', 'proceedings': 'Arguments heard, matter reserved for judgment'}
        ],
        'scraped_at': datetime.now().isoformat(),
        'source_url': 'https://delhihighcourt.nic.in/app/get-case-type-status (Demo Mode)'
    }
    return case_data, None

# Error handling decorator
def handle_errors(f):
    """Decorator to handle errors gracefully"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            flash(f'An unexpected error occurred: {str(e)}', 'error')
            return redirect(url_for('index'))
    return decorated_function

# Replace @app.before_first_request with this initialization
def create_tables():
    """Create database tables"""
    # Ensure data directory exists
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Ensure static/captcha directory exists
    captcha_dir = os.path.join(os.path.dirname(__file__), 'static', 'captcha')
    os.makedirs(captcha_dir, exist_ok=True)
    
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise

# Initialize database tables immediately
with app.app_context():
    create_tables()

@app.route('/')
def index():
    """Main page with search form"""
    # Enhanced case types for demo
    case_types = [
        "Civil Appeal",
        "Criminal Appeal", 
        "Writ Petition (Civil)",
        "Writ Petition (Criminal)",
        "Company Petition",
        "Arbitration Petition",
        "Criminal Misc. Application",
        "Civil Misc. Application",
        "Contempt Petition",
        "Execution Petition",
        "Review Petition",
        "Transfer Petition"
    ]
    
    logger.info(f"Using {len(case_types)} case types ({'Demo Mode' if DEMO_MODE else 'Live Mode'})")
    return render_template('index.html', case_types=case_types, demo_mode=DEMO_MODE)

@app.route('/search', methods=['POST'])
@handle_errors
def search_case():
    """Enhanced search with demo mode support"""
    case_type = request.form.get('case_type', '').strip()
    case_number = request.form.get('case_number', '').strip()
    filing_year = request.form.get('filing_year', '').strip()
    captcha_solution = request.form.get('captcha_solution', '').strip()
    
    # Enhanced validation
    if not all([case_type, case_number, filing_year]):
        flash('All fields are required', 'error')
        return redirect(url_for('index'))
    
    # Validate case number (should be numeric)
    if not case_number.isdigit():
        flash('Case number must be numeric', 'error')
        return redirect(url_for('index'))
    
    # Validate filing year
    current_year = datetime.now().year
    try:
        year = int(filing_year)
        if year < 1950 or year > current_year:
            flash(f'Filing year must be between 1950 and {current_year}', 'error')
            return redirect(url_for('index'))
    except ValueError:
        flash('Invalid filing year', 'error')
        return redirect(url_for('index'))
    
    # Check for cached data first
    existing_case = CaseData.query.filter_by(
        case_type=case_type,
        case_number=case_number,
        filing_year=filing_year
    ).first()
    
    cache_valid = False
    if existing_case and existing_case.last_updated:
        time_diff = datetime.now(timezone.utc) - existing_case.last_updated.replace(tzinfo=timezone.utc)
        cache_valid = time_diff.total_seconds() < 86400  # 24 hours
    
    if cache_valid and not captcha_solution:
        logger.info("Using cached case data")
        query_log = QueryLog(
            case_type=case_type,
            case_number=case_number,
            filing_year=filing_year,
            success=True,
            raw_response="Used cached data"
        )
        db.session.add(query_log)
        db.session.commit()
        
        return render_template('results.html', 
                             case_data=existing_case,
                             pdf_links=json.loads(existing_case.order_pdf_links or '[]'),
                             cached=True)
    
    try:
        # DEMO MODE: Use mock data for reliable demonstration
        if DEMO_MODE:
            logger.info("Demo mode active - generating mock case data")
            time.sleep(2)  # Simulate realistic search delay
            case_data, error = generate_demo_case_data(case_type, case_number, filing_year)
            
            # Add demo mode indicator to flash message
            flash('Demo Mode: Displaying sample case data for demonstration purposes', 'info')
        else:
            # Real scraping mode
            case_data, error = scraper.fetch_case_data_with_captcha(
                case_type, case_number, filing_year, captcha_solution
            )
        
        if case_data == "captcha_required":
            # CAPTCHA detected - redirect to CAPTCHA solving interface
            return redirect(url_for('solve_captcha', 
                                  case_type=case_type, 
                                  case_number=case_number,
                                  filing_year=filing_year))
        
        if error:
            query_log = QueryLog(
                case_type=case_type,
                case_number=case_number,
                filing_year=filing_year,
                success=False,
                error_message=error
            )
            db.session.add(query_log)
            db.session.commit()
            
            if "captcha" in error.lower():
                flash('Incorrect CAPTCHA solution. Please try again.', 'warning')
                return redirect(url_for('solve_captcha',
                                      case_type=case_type,
                                      case_number=case_number, 
                                      filing_year=filing_year))
            elif "timeout" in error.lower() or "timed out" in error.lower():
                flash('The court website is responding very slowly. Please try again in a few minutes.', 'warning')
            elif "maintenance" in error.lower():
                flash('The court website is under maintenance. Please try again later.', 'warning')
            else:
                flash(f'Error: {error}', 'error')
            
            return redirect(url_for('index'))
        
        if not case_data:
            query_log = QueryLog(
                case_type=case_type,
                case_number=case_number,
                filing_year=filing_year,
                success=False,
                error_message="No case data found"
            )
            db.session.add(query_log)
            db.session.commit()
            
            flash('Case not found. Please verify case details.', 'warning')
            return redirect(url_for('index'))
        
        # Save successful result
        if existing_case:
            # Update existing
            existing_case.parties_petitioner = case_data.get('parties_petitioner', '')
            existing_case.parties_respondent = case_data.get('parties_respondent', '')
            existing_case.filing_date = case_data.get('filing_date', '')
            existing_case.next_hearing_date = case_data.get('next_hearing_date', '')
            existing_case.case_status = case_data.get('case_status', '')
            existing_case.judge_name = case_data.get('judge_name', '')
            existing_case.order_pdf_links = json.dumps(case_data.get('order_pdf_links', []))
            existing_case.last_updated = datetime.now(timezone.utc)
            case_record = existing_case
        else:
            # Create new
            case_record = CaseData(
                case_type=case_type,
                case_number=case_number,
                filing_year=filing_year,
                parties_petitioner=case_data.get('parties_petitioner', ''),
                parties_respondent=case_data.get('parties_respondent', ''),
                filing_date=case_data.get('filing_date', ''),
                next_hearing_date=case_data.get('next_hearing_date', ''),
                case_status=case_data.get('case_status', ''),
                judge_name=case_data.get('judge_name', ''),
                order_pdf_links=json.dumps(case_data.get('order_pdf_links', []))
            )
            db.session.add(case_record)
        
        # Log successful query
        query_log = QueryLog(
            case_type=case_type,
            case_number=case_number,
            filing_year=filing_year,
            success=True,
            raw_response=json.dumps(case_data)
        )
        db.session.add(query_log)
        db.session.commit()
        
        flash('Case data retrieved successfully!', 'success')
        return render_template('results.html',
                             case_data=case_record,
                             pdf_links=case_data.get('order_pdf_links', []),
                             cached=False,
                             case_history=case_data.get('case_history', []),
                             demo_mode=DEMO_MODE)
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        logger.error(traceback.format_exc())
        
        query_log = QueryLog(
            case_type=case_type,
            case_number=case_number,
            filing_year=filing_year,
            success=False,
            error_message=str(e)
        )
        db.session.add(query_log)
        db.session.commit()
        
        flash('An error occurred while searching. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/solve-captcha')
def solve_captcha():
    """CAPTCHA solving interface"""
    case_type = request.args.get('case_type')
    case_number = request.args.get('case_number')
    filing_year = request.args.get('filing_year')
    
    if not all([case_type, case_number, filing_year]):
        flash('Missing case information', 'error')
        return redirect(url_for('index'))
    
    # Check for CAPTCHA session file
    captcha_session_file = os.path.join('data', 'captcha_session.json')
    captcha_data = None
    
    if os.path.exists(captcha_session_file):
        try:
            with open(captcha_session_file, 'r') as f:
                captcha_data = json.load(f)
        except Exception as e:
            logger.error(f"Error reading CAPTCHA session: {str(e)}")
    
    return render_template('captcha_solver.html',
                         case_type=case_type,
                         case_number=case_number,
                         filing_year=filing_year,
                         captcha_data=captcha_data,
                         demo_mode=DEMO_MODE)

@app.route('/api/captcha-status')
def captcha_status():
    """API to check CAPTCHA status"""
    captcha_session_file = os.path.join('data', 'captcha_session.json')
    
    if os.path.exists(captcha_session_file):
        try:
            with open(captcha_session_file, 'r') as f:
                captcha_data = json.load(f)
            
            return jsonify({
                'status': 'available',
                'image_path': captcha_data.get('image_path'),
                'timestamp': captcha_data.get('timestamp')
            })
        except Exception as e:
            logger.error(f"Error checking CAPTCHA status: {str(e)}")
    
    return jsonify({'status': 'not_available'})

@app.route('/download_pdf')
def download_pdf():
    """Download PDF from court website (demo version)"""
    pdf_url = request.args.get('url')
    if not pdf_url:
        flash('No PDF URL provided', 'error')
        return redirect(url_for('index'))
    
    if DEMO_MODE:
        # In demo mode, return a sample PDF instead of the flash message
        from flask import send_file
        import io
        
        try:
            # Create a simple sample PDF content
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            # Create PDF in memory
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            
            # Add content to the sample PDF
            p.drawString(100, 750, "DEMO COURT DOCUMENT")
            p.drawString(100, 720, "Delhi High Court - Sample Document")
            p.drawString(100, 690, f"Generated in Demo Mode")
            p.drawString(100, 660, f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            p.drawString(100, 630, "")
            p.drawString(100, 600, "This is a sample PDF generated for demonstration purposes.")
            p.drawString(100, 570, "In live mode, this would be an actual court document.")
            
            p.save()
            buffer.seek(0)
            
            return send_file(
                buffer,
                as_attachment=True,
                download_name=f'demo_court_document_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
                mimetype='application/pdf'
            )
            
        except ImportError:
            # If reportlab is not installed, show the original message
            flash('Demo Mode: PDF download functionality implemented. In live mode, this would download the actual court document.', 'info')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Demo Mode: PDF generation error - {str(e)}', 'warning')
            return redirect(url_for('index'))
    
    # Live mode - original functionality
    try:
        import requests
        response = requests.get(pdf_url, timeout=30, stream=True)
        response.raise_for_status()
        
        # Get filename from URL or use default
        filename = pdf_url.split('/')[-1]
        if not filename.endswith('.pdf'):
            filename = f'court_document_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        # Return file as download
        from flask import Response
        
        def generate():
            for chunk in response.iter_content(chunk_size=8192):
                yield chunk
        
        return Response(
            generate(),
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'application/pdf'
            }
        )
        
    except Exception as e:
        logger.error(f"Error downloading PDF: {str(e)}")
        flash(f'Error downloading PDF: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/test-connection')
def test_connection():
    """Test connection to court website"""
    try:
        if DEMO_MODE:
            return jsonify({
                'status': 'success',
                'message': 'Demo Mode: Connection testing disabled for demo purposes',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        connection_ok, message = scraper.test_connection()
        return jsonify({
            'status': 'success' if connection_ok else 'error',
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

@app.route('/search-history')
def search_history():
    """View search history"""
    try:
        # Get recent searches
        recent_searches = QueryLog.query.order_by(QueryLog.query_timestamp.desc()).limit(50).all()
        
        return render_template('search_history.html', searches=recent_searches, demo_mode=DEMO_MODE)
    except Exception as e:
        logger.error(f"Error fetching search history: {str(e)}")
        flash('Error loading search history', 'error')
        return redirect(url_for('index'))

@app.route('/stats')
def stats():
    """Application statistics"""
    try:
        total_searches = QueryLog.query.count()
        successful_searches = QueryLog.query.filter_by(success=True).count()
        total_cases = CaseData.query.count()
        
        success_rate = (successful_searches / total_searches * 100) if total_searches > 0 else 0
        
        stats_data = {
            'total_searches': total_searches,
            'successful_searches': successful_searches,
            'success_rate': round(success_rate, 2),
            'total_cases': total_cases,
            'demo_mode': DEMO_MODE,
            'last_update': datetime.now(timezone.utc).isoformat()
        }
        
        return jsonify(stats_data)
    except Exception as e:
        logger.error(f"Error generating stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        
        if DEMO_MODE:
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'mode': 'demo',
                'court_website': 'demo mode - not tested',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        # Test court website connection
        connection_ok, connection_msg = scraper.test_connection()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'mode': 'live',
            'court_website': 'connected' if connection_ok else 'disconnected',
            'court_website_message': connection_msg,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    logger.error(f"Internal server error: {str(error)}")
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Internal server error"), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    # Docker-friendly configuration
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

