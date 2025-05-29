# Multi-Format Intake Agent with Intelligent Routing & Context Memory

## 🚀 Overview

This project implements an AI-powered multi-agent system designed to process various data formats—**PDF**, **JSON**, and **Email (text)**. The system intelligently classifies the input type and intent, routes it to the appropriate specialized agent for data extraction, and maintains context memory to support downstream processing and audits.

## 🧠 System Architecture

### 1. **Classifier Agent**
- **Function**: Determines the format (PDF, JSON, Email) and intent (Invoice, RFQ, Complaint, Regulation, etc.) of the input.
- **Routing**: Directs the input to the corresponding specialized agent based on classification.
- **Memory Update**: Logs format and intent into the shared memory.

### 2. **Specialized Agents**
- **Email Parser Agent**:
  - Processes email body text (plain or HTML).
  - Extracts sender name, request intent, urgency.
  - Returns a formatted CRM-style record.
  - Stores conversation ID and parsed metadata in memory.

- **JSON Agent**:
  - Accepts arbitrary JSON inputs (e.g., webhook payloads, APIs).
  - Extracts and reformats data to a defined schema.
  - Identifies anomalies or missing fields.

- **PDF Agent**:
  - Parses PDF documents to extract relevant information based on intent.
  - (Implementation details to be added.)

### 3. **Shared Memory Module**
- **Purpose**: Stores input metadata (source, type, timestamp), extracted fields per agent, and thread/conversation ID if available.
- **Implementation**: Utilizes a lightweight in-memory store (e.g., Redis, SQLite, or a JSON-based memory class).
- **Accessibility**: Readable and writable across all agents.

### 4. **Orchestrator**
- **Function**: Manages the end-to-end flow of data through the system.
- **Process**:
  1. Receives raw input.
  2. Invokes the Classifier Agent.
  3. Routes to the appropriate specialized agent.
  4. Updates shared memory.
  5. Returns or logs the structured output.

### Screenshots
- Home Page
   ![Alt text](https://github.com/Pixeler5diti/Multi-Format-Intake-Agent-with-Intelligent-Routing-Context-Memory/blob/94b0c9518ee1e52028a782d644c62293aa11a78e/assets/1.png)

- Input text : JSON
  ![Alt text](https://github.com/Pixeler5diti/Multi-Format-Intake-Agent-with-Intelligent-Routing-Context-Memory/blob/94b0c9518ee1e52028a782d644c62293aa11a78e/assets/2.png)
   
- Memory Store:
  ![Alt text](https://github.com/Pixeler5diti/Multi-Format-Intake-Agent-with-Intelligent-Routing-Context-Memory/blob/94b0c9518ee1e52028a782d644c62293aa11a78e/assets/3.png)

## 📁 Folder Structure
```
multi-format-intake-agent/

├── agents/
│ ├── classifier_agent.py
│ ├── email_agent.py
│ ├── json_agent.py
│ └── pdf_agent.py
├── memory/
│ └── memory_store.py
├── services/
│ └── orchestrator.py
├── models/
│ └── schemas.py
├── static/
│ ├── sample_email.txt
│ ├── sample_invoice.json
│ └── sample_complaint.pdf
├── main.py
├── pyproject.toml
├── uv.lock
└── README.md
```

## 🛠️ Tech Stack

- **Programming Language**: Python
- **Frameworks & Libraries**:
  - FastAPI (for API endpoints)
  - Langchain (for LLM integration)
  - Redis / SQLite (for shared memory)
  - PyMuPDF / pdfplumber (for PDF parsing)
- **Containerization**: Docker (optional)

## 📦 Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Pixeler5diti/Multi-Format-Intake-Agent-with-Intelligent-Routing-Context-Memory.git
   cd Multi-Format-Intake-Agent-with-Intelligent-Routing-Context-Memory
2. **Install requirements**:
   ```
   pip install -r requirements.txt
   ```
3. **Run the Application**:
   ```
   python main.py
   ```
4. **Upload a smaple input from the stactic folder or any custom input**

### 🔁 End-to-End Example Flow

- Input: Email file
- Classifier → detects Email + RFQ intent
- Routed to: Email Agent → extracts sender, request, urgency
- Memory stores: Email metadata + extracted fields
- If attachment is JSON → Routed to JSON Agent
- Combined structured output is logged

### Demo Video
Coming soon!<3

### 📄 License
MIT

### ✨ Author

Made with ❤️ by Diti Vasisht
