# 🏛️ Delhi High Court Case Fetcher

Professional web application for fetching case information from Delhi High Court with automated search, manual CAPTCHA handling, dark/light themes & Docker deployment.  
Built with **Flask**, **Selenium**, and **Bootstrap**.


---

## 📽️ Demo Video
[![Watch the video](https://img.youtube.com/vi/NIxutg4qars/maxresdefault.jpg)](https://youtu.be/NIxutg4qars)


---

## 🖼️ Screenshots
<img width="1340" height="638" alt="Screenshot (98)" src="https://github.com/user-attachments/assets/d9b8e9f6-0c9b-46df-b037-2df488860aac" />

<img width="1366" height="622" alt="Screenshot (99)" src="https://github.com/user-attachments/assets/b6d5d573-0fbf-4a6c-b4d7-335557862040" />




---

## 🎯 Overview
A comprehensive **Court Data Fetcher & Mini-Dashboard** that allows users to search for case information from the Delhi High Court with professional UI and manual CAPTCHA handling.

---

## 🏛️ Court Chosen
**Target Court:** Delhi High Court  
**Primary URL:** [https://delhihighcourt.nic.in/app/get-case-type-status](https://delhihighcourt.nic.in/app/get-case-type-status)  

**Why chosen:**
- Well-structured search system
- Comprehensive metadata
- Multiple case types
- Accessible PDF documents

---

## ✨ Features
- 🎨 **Dark/Light Theme Toggle** – Modern UI with smooth transitions  
- 🔍 **Comprehensive Case Search** – By Case Type, Case Number, Filing Year  
- 🛡️ **Manual CAPTCHA Handling** – Legal & user-friendly  
- 📊 **Case Data Parsing** – Extract parties, dates, status, judge info  
- 📄 **PDF Document Access** – Download court orders and judgments  
- ⏰ **Case History Timeline** – Visual representation of proceedings  
- 💾 **SQLite Database** – Logs all queries, 24-hour cache  
- 📱 **Responsive Design** – Works on all devices  
- 🚀 **Docker Support** – One-command deployment  

---

## 🚀 Installation

**Prerequisites:** Python 3.8+, Google Chrome, Git

```bash
# Clone repository
git clone https://github.com/yourusername/delhi-court-fetcher.git
cd delhi-court-fetcher
```

# Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

# Install dependencies
```bash
pip install -r requirements.txt
```

# Run application
```bash
python app.py
```
# Access at: http://localhost:5000

---

### 🛡️ CAPTCHA Strategy – Professional & Legal Approach

Implementation Philosophy:
Our CAPTCHA handling strategy prioritizes legal compliance and user experience over aggressive automation, demonstrating professional software development practices that respect website terms of service while maintaining functionality.

Why This Approach Works:
- Robust Detection – Handles various CAPTCHA implementations
- Fallback Mechanisms – Multiple selectors ensure reliability across website changes
- Future-Proof – Adapts to layout modifications in court website

### 1️⃣ Professional CAPTCHA Workflow:
1. Automatic Detection → Scraper identifies CAPTCHA elements using multiple selectors
2. Image Capture → Screenshot CAPTCHA and save to static/captcha/ directory
3. User Notification → Redirect to clean, accessible solving interface
4. Manual Resolution → User inputs CAPTCHA solution through professional UI
5. Workflow Resume → Automated process continues after verification

### CAPTCHA Handling Function

```python
def _handle_captcha(self, driver):
    """Professional CAPTCHA handling with user interface"""
    if captcha_found and captcha_image and captcha_input:
        captcha_filename = self._save_captcha_image(captcha_image, driver)
        # Save session data for manual solving workflow
        return "manual_required"
    return True
```
### 2️⃣ User-Friendly CAPTCHA Interface

- **Clean Design** – Professional `/solve-captcha` route with intuitive interface  
- **Clear Instructions** – Step-by-step guidance for users  
- **Progress Indicators** – Visual feedback during solving process  
- **Error Handling** – Graceful handling of incorrect solutions with retry options  
- **Session Management** – Secure temporary session handling for workflow continuity  



## 📜 Legal & Ethical Compliance Framework

### Why Manual Solving is Superior

**Legal Advantages:**
- ✅ No Terms of Service Violations  
- ✅ Ethical Compliance  
- ✅ Professional Standards  
- ✅ Audit Trail  

**Technical Advantages:**
- ✅ 100% Success Rate  
- ✅ Universal Compatibility  
- ✅ No API Costs  
- ✅ Privacy Conscious  

---

## 🐳 Docker Deployment  

Quick Start  
# Clone and navigate 
```bash
git clone https://github.com/yourusername/delhi-court-fetcher.git  
cd delhi-court-fetcher
``` 

# Build and run with Docker Compose 
```bash
docker-compose up --build
```

# Access application  

open http://localhost:5000  

Manual Docker

```bash
docker build -t delhi-court-fetcher .  
docker run -p 5000:5000 delhi-court-fetcher
```

 ---

## 🎯 Usage

1. Select Case Type – Choose from dropdown (Civil Appeal, Writ Petition, etc.)
2. Enter Case Number – Input numerical case number
3. Select Filing Year – Choose filing year (1950-2025)
4. Handle CAPTCHA – Solve CAPTCHA through interface
5. View Results – Case details, PDFs, and timeline

Demo Mode:
- Set DEMO_MODE=True for instant results with realistic sample data.
- Perfect for testing without external dependencies.

---

📁 Project Structure
delhi-court-fetcher/
├── app.py                  # Main Flask application
├── scraper.py              # Court scraper logic with CAPTCHA handling
├── models.py               # Database models (SQLAlchemy)
├── config.py               # Application configuration
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose deployment
├── data/                   # Database and session files
├── static/                 # CSS, JS, CAPTCHA images
│   ├── style.css           # Enhanced dark theme CSS
│   ├── script.js           # Interactive JavaScript
│   └── captcha/            # CAPTCHA image storage
└── templates/              # HTML templates
    ├── index.html          # Main search interface
    ├── results.html        # Case details display
    ├── captcha_solver.html # CAPTCHA solving interface
    └── search_history.html # Search history page

---

## 🛠️ Tech Stack
Backend: Flask 3.0, SQLAlchemy, Selenium 4.15, BeautifulSoup4  
Frontend: Bootstrap 5, Font Awesome 6, Custom CSS/JS with dark theme  
Database: SQLite with comprehensive logging  
Deployment: Docker, Gunicorn  
Scraping: Chrome WebDriver with professional CAPTCHA handling  

---

## 📊 Environment Variables  
Create a `.env` file in the project root:

### Flask Configuration
FLASK_SECRET_KEY=your-secret-key-generate-strong-random-string  
FLASK_ENV=development  
DEBUG=True  

### Database Configuration
DATABASE_URL=sqlite:///court_data.db  

### Application Configuration
DEMO_MODE=True  
MAX_RETRIES=3  
TIMEOUT_SECONDS=30  

### Optional: For production deployment
PORT=5000  
HOST=0.0.0.0  

---

# Thank You 🙏





