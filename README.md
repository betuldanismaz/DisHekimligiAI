# 🦷 DentAI - Dental Education AI Simulator

> An intelligent, AI-powered dental education platform that simulates realistic clinical patient encounters for dental students using Google's Gemini AI.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178C6.svg)](https://www.typescriptlang.org/)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#️-system-architecture)
- [Technology Stack](#-technology-stack)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Running the Application](#-running-the-application)
- [Project Structure](#-project-structure)
- [Available Cases](#-available-cases)
- [API Documentation](#-api-documentation)
- [Development](#-development)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

**DentAI** is a comprehensive dental education simulator that leverages Google's Gemini AI to create realistic patient interaction scenarios. The platform enables dental students to practice clinical decision-making in a safe, simulated environment with real-time AI-powered feedback.

### What Makes DentAI Unique?

- **Hybrid AI Architecture**: Combines Large Language Models (Google Gemini) with deterministic rule-based assessment for accurate, safe, and objective feedback
- **Realistic Patient Simulation**: AI-powered conversational patient that responds naturally to student interactions
- **Objective Grading**: Rule-based scoring system aligned with clinical protocols
- **Performance Analytics**: Identifies weaknesses and provides personalized recommendations
- **Bilingual Support**: Turkish patient responses with English internal logic

---

## ✨ Key Features

### 🎭 Interactive Clinical Scenarios

- Multiple realistic patient simulations covering various pathology categories
- Cases include: Oral Lichen Planus, Chronic Periodontitis, Primary Herpetic Gingivostomatitis, Behçet's Disease, Secondary Syphilis, and more
- Difficulty levels: Easy, Medium, Hard

### 🤖 Hybrid Assessment Engine

- **LLM Layer**: Interprets student intent and natural language inputs using Google Gemini
- **Rule Layer**: Scores actions against strict clinical protocols defined in JSON rules
- **Silent Evaluator**: Background validation without interrupting conversation flow

### 📊 Performance Tracking

- Real-time score tracking during case sessions
- Category-based performance analysis
- Weakness identification with actionable recommendations
- Downloadable performance reports

### 🔐 User Management

- Secure authentication with JWT tokens
- Individual student profiles
- Session persistence across multiple cases
- Chat history tracking

### 💻 Modern Web Interface

- Responsive Next.js frontend with TypeScript
- Real-time chat interface
- Interactive dashboard showing all available cases
- Clean, intuitive user experience

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Login/     │  │  Dashboard   │  │  Chat Page   │      │
│  │   Register   │  │              │  │   (Case)     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                           │                                  │
│                    ┌──────▼──────┐                          │
│                    │  API Client  │                          │
│                    │   (Axios)    │                          │
└────────────────────┴──────────────┴──────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   FastAPI       │
                    │   REST API      │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼─────┐      ┌──────▼──────┐      ┌─────▼─────┐
   │  Agent   │      │ Assessment  │      │ Scenario  │
   │          │◄─────┤   Engine    │◄─────┤  Manager  │
   └────┬─────┘      └─────────────┘      └─────┬─────┘
        │                                        │
   ┌────▼─────┐                          ┌──────▼──────┐
   │  Gemini  │                          │   SQLite    │
   │   API    │                          │  Database   │
   └──────────┘                          └─────────────┘
```

### Core Components

1. **DentalEducationAgent** (`app/agent.py`): Orchestrates the hybrid AI workflow
2. **AssessmentEngine** (`app/assessment_engine.py`): Rule-based scoring and evaluation
3. **ScenarioManager** (`app/scenario_manager.py`): Case and session state management
4. **AnalyticsEngine** (`app/analytics_engine.py`): Performance analysis and reporting

---

## 🛠 Technology Stack

### Backend

- **Python 3.10+**: Core programming language
- **FastAPI**: Modern, high-performance REST API framework
- **SQLAlchemy**: ORM for database management
- **SQLite**: Lightweight database for data persistence
- **Pydantic v2**: Data validation and serialization
- **Google Generative AI**: Gemini API integration
- **python-jose**: JWT token authentication
- **Passlib**: Password hashing with bcrypt

### Frontend

- **Next.js 14+**: React framework with App Router
- **TypeScript 5+**: Type-safe JavaScript
- **React 18+**: UI library
- **Axios**: HTTP client for API communication
- **CSS Modules**: Component-scoped styling

### AI/ML

- **Google Gemini 2.5 Flash Lite**: Cost-effective LLM for patient simulation
- **Custom Rules Engine**: Clinical protocol validation

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10 or higher**
- **Node.js 18+ and npm** (for frontend)
- **Google Gemini API Key** ([Get one here](https://ai.google.dev/))
- **Git** (for cloning the repository)

---

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/betuldanismaz/dentai.git
cd dentai/dentai
```

### 2. Backend Setup

#### Create a Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### Install Backend Dependencies

```bash
# Install Streamlit dependencies (legacy)
pip install -r requirements.txt

# Install FastAPI dependencies (API server)
pip install -r requirements-api.txt
```

#### Configure Environment Variables

Create a `.env` file in the root directory:

```ini
# .env file
GEMINI_API_KEY=your_google_gemini_api_key_here
SECRET_KEY=your_secret_key_for_jwt_here
DATABASE_URL=sqlite:///./db/dental_tutor.db
```

> **Note**: Generate a secure `SECRET_KEY` using:
>
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(32))"
> ```

### 3. Frontend Setup

Navigate to the frontend directory and install dependencies:

```bash
cd frontend
npm install
```

#### Configure Frontend Environment

Create a `.env.local` file in the `frontend` directory:

```ini
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 🚀 Running the Application

### Start the Backend Server

From the root directory (with virtual environment activated):

```bash
# Navigate to the project root
cd dentai

# Start the FastAPI server
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:

- **API**: http://localhost:8000
- **API Documentation (Swagger)**: http://localhost:8000/docs
- **Alternative Documentation (ReDoc)**: http://localhost:8000/redoc

### Start the Frontend Development Server

In a new terminal, navigate to the frontend directory:

```bash
cd dentai/frontend
npm run dev
```

The frontend will be available at:

- **Frontend**: http://localhost:3000

### Access the Application

1. Open your browser and go to http://localhost:3000
2. Register a new student account
3. Log in with your credentials
4. Select a case from the dashboard
5. Start practicing!

---

## 📁 Project Structure

```
dentai/
├── 📂 app/                          # Backend application core
│   ├── 📂 api/                      # FastAPI REST API
│   │   ├── 📂 routers/              # API endpoint routers
│   │   │   ├── auth.py              # Authentication endpoints
│   │   │   ├── chat.py              # Chat/conversation endpoints
│   │   │   └── cases.py             # Case management endpoints
│   │   ├── main.py                  # FastAPI app initialization
│   │   └── deps.py                  # Dependency injection
│   │
│   ├── 📂 services/                 # External service integrations
│   │   ├── med_gemma_service.py     # MedGemma AI service
│   │   └── rule_service.py          # Rule processing service
│   │
│   ├── agent.py                     # 🧠 Main AI orchestrator
│   ├── assessment_engine.py         # 📊 Scoring engine
│   ├── scenario_manager.py          # 🎭 State management
│   ├── analytics_engine.py          # 📈 Performance analytics
│   └── student_profile.py           # 👤 Student data management
│
├── 📂 frontend/                     # Next.js frontend application
│   ├── 📂 app/                      # Next.js App Router pages
│   │   ├── 📂 chat/[caseId]/        # Dynamic chat page
│   │   ├── 📂 dashboard/            # Student dashboard
│   │   ├── 📂 login/                # Login page
│   │   ├── 📂 register/             # Registration page
│   │   └── layout.tsx               # Root layout
│   │
│   ├── 📂 components/               # Reusable React components
│   ├── 📂 context/                  # React context providers
│   ├── 📂 lib/                      # Utility libraries
│   │   └── api.ts                   # Axios API client
│   └── 📂 public/                   # Static assets
│
├── 📂 data/                         # Application data files
│   ├── case_scenarios.json          # Clinical case definitions
│   ├── scoring_rules.json           # Scoring rule configurations
│   └── mcq_questions.json           # Multiple choice questions
│
├── 📂 db/                           # Database layer
│   └── database.py                  # SQLAlchemy models & session
│
├── 📂 assets/                       # Media assets (images, etc.)
├── 📂 tests/                        # Test suite
│
├── main.py                          # Streamlit entry point (legacy)
├── requirements.txt                 # Streamlit dependencies
├── requirements-api.txt             # FastAPI dependencies
├── README.md                        # This file
└── PROJECT_ARCHITECTURE.md          # Detailed architecture documentation
```

---

## 🏥 Available Cases

| Case ID               | Name                                           | Difficulty | Category    |
| --------------------- | ---------------------------------------------- | ---------- | ----------- |
| `olp_001`             | Oral Lichen Planus                             | Medium     | Immunologic |
| `perio_001`           | Chronic Periodontitis                          | Hard       | Infectious  |
| `herpes_primary_01`   | Primary Herpetic Gingivostomatitis             | Medium     | Infectious  |
| `infectious_child_01` | Primary Herpetic Gingivostomatitis (Pediatric) | Hard       | Infectious  |
| `behcet_01`           | Behçet's Disease                               | Hard       | Immunologic |
| `syphilis_02`         | Secondary Syphilis                             | Hard       | Infectious  |
| `desquamative_01`     | Chronic Desquamative Gingivitis                | Hard       | Immunologic |

---

## 📚 API Documentation

### Authentication Endpoints

| Endpoint             | Method | Description                  | Auth Required |
| -------------------- | ------ | ---------------------------- | ------------- |
| `/api/auth/register` | POST   | Register new student account | No            |
| `/api/auth/login`    | POST   | Authenticate and receive JWT | No            |
| `/api/auth/me`       | GET    | Get current user info        | Yes           |

### Chat Endpoints

| Endpoint                                   | Method | Description                       | Auth Required |
| ------------------------------------------ | ------ | --------------------------------- | ------------- |
| `/api/chat/send`                           | POST   | Send message, receive AI response | Yes           |
| `/api/chat/history/{student_id}/{case_id}` | GET    | Retrieve chat history             | Yes           |

### Cases Endpoints

| Endpoint                      | Method | Description                           | Auth Required |
| ----------------------------- | ------ | ------------------------------------- | ------------- |
| `/api/cases`                  | GET    | List all available cases              | Yes           |
| `/api/cases/{caseId}`         | GET    | Get specific case (student-safe view) | Yes           |
| `/api/cases/{caseId}/start`   | POST   | Start or resume session               | Yes           |
| `/api/cases/{caseId}/session` | GET    | Get current session info              | Yes           |

### Interactive API Documentation

Visit http://localhost:8000/docs for the interactive Swagger UI where you can test all endpoints.

---

## 🔧 Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auth.py -v

# Run with coverage
pytest --cov=app tests/
```

### Adding New Cases

1. Add case definition to `data/case_scenarios.json`
2. Add corresponding scoring rules to `data/scoring_rules.json`
3. Add clinical images to `assets/images/` (if applicable)
4. Test with API endpoint `GET /api/cases`

### Code Standards

- **Python**: Follow PEP 8, use type hints
- **TypeScript**: Strict mode enabled, explicit types preferred
- **API Design**: RESTful conventions, consistent error responses

### Useful Development Commands

```bash
# Backend - Format code
black app/

# Backend - Lint code
flake8 app/

# Frontend - Lint code
cd frontend
npm run lint

# Frontend - Build for production
npm run build
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 📞 Support

For questions, issues, or suggestions:

- **GitHub Issues**: [Create an issue](https://github.com/betuldanismaz/dentai/issues)
- **Documentation**: See [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) for detailed technical documentation

---

## 🙏 Acknowledgments

- **Google Gemini AI**: For providing the powerful LLM capabilities
- **FastAPI**: For the excellent API framework
- **Next.js**: For the modern React framework
- **All Contributors**: Thank you for your contributions!

---

<div align="center">

**Built with ❤️ for dental education**

[⬆ Back to Top](#-dentai---dental-education-ai-simulator)

</div>
