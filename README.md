# Auto Generate Test Cases

A Python-based AI testing system that leverages AutoGen framework and multiple AI agents to automatically analyze requirements and generate test cases.

## Features

- 📝 Automated requirement analysis using AI
- 🤖 Multi-agent system powered by AutoGen framework
- 📋 Configurable test case templates and formats
- 📊 Excel export with customizable formatting
- 🔄 Support for multiple document formats (PDF, Word, Markdown, Text)
- ⚙️ Extensible architecture for future enhancements

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ai-test-case-generator
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure the system:
- Copy the sample configuration file:
```bash
cp config.json.example config.json
```
- Update the configuration with your OpenAI API key and other settings in config.json

## Project Structure

src/
├── agents/                 # AutoGen-based AI agents
│   ├── requirement_analyst.py
│   ├── test_designer.py
│   ├── test_case_writer.py
│   ├── quality_assurance.py
│   └── assistant.py
├── services/               # Core services
│   ├── document_processor.py
│   ├── test_case_generator.py
│   └── export_service.py
├── models/                 # Data models
│   ├── test_case.py
│   └── template.py
├── utils/                  # Utilities
│   ├── logger.py
│   └── config.py
└── main.py                # Application entry point

## Usage

1. Start the system:

   python src/main.py

2. Input:
- Requirements document (PDF, Word, Markdown, or Text)
- Template configuration (optional)

3. Output:
- Excel file containing generated test cases
- Logs in the logs directory

## Configuration

The system can be configured through config.json. Key configuration options:

- openai_api_key: Your OpenAI API key
- log_level: Logging level (INFO, DEBUG, etc.)
- templates_dir: Directory for test case templates
- output_dir: Directory for generated files
- Agent-specific configurations (model, temperature, etc.)

## Example

from main import AITestingSystem
import asyncio

async def main():
    system = AITestingSystem()
    result = await system.process_requirements(
        doc_path="requirements.pdf",
        template_id="default_template",
        output_path="test_cases.xlsx"
    )
    print("Test cases generated successfully!")

if __name__ == "__main__":
    asyncio.run(main())

## Contributing

1. Fork the repository
2. Create your feature branch (git checkout -b feature/amazing-feature)
3. Commit your changes (git commit -m 'Add amazing feature')
4. Push to the branch (git push origin feature/amazing-feature)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
