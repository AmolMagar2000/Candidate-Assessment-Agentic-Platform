# 🎯 Candidate Assessment Platform

A comprehensive full-stack application for conducting technical assessments with MCQ and coding questions, powered by AI-generated content.

## 📋 Features

### For Candidates
- 🔐 Secure email-based authentication
- ⏱️ Timed assessments (60 minutes)
- 📝 Multiple choice questions (MCQs)
- 💻 Live code execution (Python & Java)
- 📊 Real-time progress tracking
- ✅ Instant submission and scoring

### For Administrators
- 👥 External candidate synchronization
- 🤖 AI-powered question generation using Mistral LLM
- 📚 Role-specific question banks (Apex, React, Java, OIC, Backend)
- 🔍 Question preview and verification
- 📈 Detailed results and analytics
- 📜 Generation logs for debugging
- 🔄 System reset capabilities

## 🏗️ Architecture

### Backend (FastAPI)
- **Framework**: FastAPI with SQLAlchemy ORM
- **Database**: SQLite (easily switchable to PostgreSQL/MySQL)
- **LLM Integration**: Mistral AI for question generation
- **Code Execution**: Sandboxed code executor for Python/Java
- **API Documentation**: Auto-generated at `/docs`

### Frontend (Streamlit)
- **Framework**: Streamlit for rapid UI development
- **Features**: Multi-page navigation, real-time updates, responsive design
- **Components**: Candidate portal + Admin dashboard

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Mistral AI server (or compatible LLM endpoint)
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/candidate-assessment.git
cd candidate-assessment
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

Create a `.env` file in the root directory:

```env
# LLM Configuration
MISTRAL_API_URL=http://localhost:11434
MISTRAL_MODEL=mistral:latest
LLM_TIMEOUT=360

# External API for candidate sync
EXTERNAL_API_URL=https://your-external-api.com/candidates

# Database (optional, defaults to SQLite)
# DATABASE_URL=postgresql://user:password@localhost/dbname
```

5. **Set up reference topics**

Create a `reference_topics/` directory with topic files:
- `apex_mcq_topics.txt`
- `apex_coding_topics.txt`
- `react_mcq_topics.txt`
- `react_coding_topics.txt`
- `java_mcq_topics.txt`
- `java_coding_topics.txt`
- `oic_mcq_topics.txt`
- `oic_coding_topics.txt`

Example content for `java_mcq_topics.txt`:
```
Java Collections Framework
Multithreading and Concurrency
Stream API and Functional Programming
Exception Handling
Spring Boot REST APIs
JPA and Hibernate
```

### Running the Application

1. **Start the backend server**
```bash
uvicorn app:app --reload --port 8000
```

2. **Start the frontend (in a new terminal)**
```bash
streamlit run streamlit_app.py
```

3. **Access the application**
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 📁 Project Structure

```
candidate-assessment/
├── app.py                      # FastAPI backend
├── streamlit_app.py           # Streamlit frontend
├── llm.py                     # LLM integration & question generation
├── code_executor.py           # Code execution engine
├── models.py                  # Database models
├── schemas.py                 # Pydantic schemas
├── db.py                      # Database configuration
├── .env                       # Environment variables (not in repo)
├── .gitignore                 # Git ignore rules
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── reference_topics/          # Topic files for question generation
│   ├── apex_mcq_topics.txt
│   ├── java_coding_topics.txt
│   └── ...
└── llm_generation.log        # LLM generation logs (auto-generated)
```

## 🔧 Configuration

### Supported Roles
- `apex` - Salesforce Apex
- `react` - React.js
- `java` - Java Development
- `oic` - Oracle Integration Cloud
- `backend` - General Backend (default)

### Question Limits
- MCQ per test: 10 questions
- Coding per test: 3 questions

Modify in `app.py`:
```python
MCQ_LIMIT = 10
CODING_LIMIT = 3
```

## 📊 Database Schema

### Tables
- **Candidate**: User information, authorization status
- **Question**: Question bank with role-based filtering
- **Test**: Test sessions with timestamps
- **Answer**: Candidate responses with correctness flags

## 🔒 Security Considerations

⚠️ **Important**: This is a development version. For production:

1. Enable HTTPS/TLS
2. Implement proper authentication (JWT, OAuth)
3. Add rate limiting
4. Sanitize all user inputs
5. Use proper database credentials
6. Enable CORS restrictions
7. Implement API key authentication
8. Add session management
9. Use environment-specific configs

## 🧪 Testing

### Test the backend
```bash
pytest tests/  # (if tests are implemented)
```

### Manual API testing
```bash
# Sync candidates
curl -X GET http://localhost:8000/admin/sync-external-candidates

# Generate MCQs
curl -X POST http://localhost:8000/admin/generate-mcq \
  -H "Content-Type: application/json" \
  -d '{"role": "java", "mcq_count": 15}'
```

## 📝 API Endpoints

### Admin Endpoints
- `GET /admin/sync-external-candidates` - Sync candidates
- `GET /admin/candidates` - List all candidates
- `POST /admin/authorize` - Authorize candidate
- `POST /admin/generate-mcq` - Generate MCQ questions
- `POST /admin/generate-coding` - Generate coding questions
- `GET /admin/results` - View test results
- `GET /admin/logs` - View generation logs
- `DELETE /admin/reset` - Reset all data

### Candidate Endpoints
- `POST /start-test` - Start assessment
- `POST /run-code` - Execute code snippet
- `POST /submit-answers` - Submit test answers

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🐛 Known Issues

- Code execution timeout handling needs improvement
- PDF export for results not yet implemented
- Email notifications pending
- Need to add pagination for large candidate lists

## 🗺️ Roadmap

- [ ] Add user authentication with JWT
- [ ] Implement email notifications
- [ ] Add PDF report generation
- [ ] Support for more programming languages
- [ ] Advanced analytics dashboard
- [ ] Question difficulty auto-adjustment
- [ ] Proctoring features (webcam, screen monitoring)
- [ ] Mobile responsive design improvements

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Contact: your-email@example.com

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- Streamlit for rapid UI development
- Mistral AI for LLM capabilities
- SQLAlchemy for ORM functionality

---

**Made with ❤️ for better technical assessments**