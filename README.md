# Dental Education AI (DisHekimligiAI)

A dental education simulation system that uses Google's Gemini AI to provide interactive learning scenarios for dental students.

## Features

- Interactive dental case scenarios
- AI-powered action interpretation and feedback
- Objective scoring system for student actions
- Tkinter-based GUI for easy interaction
- Hybrid AI workflow combining LLM interpretation with rule-based assessment

## Prerequisites

- Python 3.7 or higher
- Google Gemini API Key (get from [Google AI Studio](https://makersuite.google.com/app/apikey))

## Installation

1. **Clone or download the project** to your local machine

2. **Install Python dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API key:**
   - Copy `.env.example` to `.env`
   - Edit `.env` and replace `your_api_key_here` with your actual Gemini API key:
     ```
     GEMINI_API_KEY=your_actual_api_key_here
     ```

## Running the Project

### Option 1: Run the Main GUI Application

```bash
python main.py
```

This will start the Tkinter-based chat interface where you can interact with the Gemini AI.

### Option 2: Run the Agent Test

```bash
python app/agent.py
```

This will run a test of the dental education agent with a sample student action.

## Project Structure

```
DisHekimligiAI/
├── app/                    # Core application modules
│   ├── agent.py           # Main AI agent orchestrator
│   ├── assessment_engine.py # Rule-based scoring system
│   └── scenario_manager.py # Scenario state management
├── data/                  # Data files
│   ├── case_scenarios.json # Dental case scenarios
│   └── scoring_rules.json  # Assessment rules
├── main.py               # Main GUI application
├── requirements.txt      # Python dependencies
└── .env.example         # Environment variables template
```

## How It Works

1. **Student Action Input**: Students describe their actions in natural language
2. **AI Interpretation**: Gemini AI interprets the action into structured data
3. **Rule-Based Assessment**: The assessment engine scores the action against predefined rules
4. **Feedback Generation**: Combined feedback is provided to the student
5. **State Management**: Scenario state is updated based on the action

## Usage Examples

### GUI Application

- Run `python main.py`
- Type your dental actions in the input field
- Press Enter or click "Gönder" to send
- Receive AI feedback and guidance

### Agent Testing

- Run `python app/agent.py`
- See example of how the system processes a student action
- View the interpretation, scoring, and feedback pipeline

## Troubleshooting

### Common Issues

1. **"GEMINI_API_KEY not found" error:**

   - Make sure you have created a `.env` file with your API key
   - Verify the API key is valid and active

2. **Import errors:**

   - Run `pip install -r requirements.txt` to install all dependencies
   - Make sure you're using Python 3.7+

3. **GUI not opening:**
   - Ensure tkinter is installed (usually comes with Python)
   - On some Linux systems, you may need to install `python3-tk`

### Getting Help

If you encounter issues:

1. Check that all dependencies are installed
2. Verify your API key is correct
3. Check the console output for error messages
4. Ensure you're running the commands from the project directory

## Development

The project uses a hybrid AI approach:

- **Gemini AI**: For natural language understanding and interpretation
- **Rule Engine**: For objective, consistent scoring
- **State Management**: For tracking scenario progress

To extend the system:

- Add new case scenarios in `data/case_scenarios.json`
- Define new scoring rules in `data/scoring_rules.json`
- Modify the agent prompt in `app/agent.py` for different behavior
