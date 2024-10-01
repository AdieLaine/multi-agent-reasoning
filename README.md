# Multi-Agent Reasoning

A Python-based solution that employs **Multi-Agent Reasoning** where multiple AI agents collaborate to generate optimal responses to user prompts. By simulating interactions between agents, the system enhances reasoning capabilities to deliver accurate and refined answers.

---
![alt text](img/reasoningbanner.png)

---
## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Models](#models)
- [Agents' Reasoning Process](#agents-reasoning-process)
  - [Step 1: Initial Discussion](#step-1-initial-discussion)
  - [Step 2: Verification](#step-2-verification)
  - [Step 3: Critiquing](#step-3-critiquing)
  - [Step 4: Refinement](#step-4-refinement)
  - [Step 5: Response Blending](#step-5-response-blending)
  - [Step 6: User Feedback Loop](#step-6-user-feedback-loop)
  - [Step 7: Context Retention](#step-7-context-retention)
- [Code Logic Explanation](#code-logic-explanation)
- [Visual Flow of the Reasoning Process](#visual-flow-of-the-reasoning-process)
- [Contributing](#contributing)
- [License](#license)
- [Setting Up the GitHub Repository](#setting-up-the-github-repository)
- [Directory Structure](#directory-structure)

---

## Overview

The **Multi-Agent Reasoning** script creates an interactive chatbot experience where multiple AI agents collaborate through a structured reasoning process to provide optimal answers. Each agent brings unique perspectives and expertise, and through iterative steps of discussion, verification, critique, and refinement, they converge on a high-quality, accurate response. This collaborative approach simulates a team of experts working together to solve a problem, enhancing the chatbot's ability to deliver comprehensive and reliable information.

## Features

- **Multi-Agent Collaboration**: Simulates collaborative reasoning between multiple agents.
- **Structured Reasoning Process**: Agents engage in a multi-step process including discussion, verification, critique, and refinement.
- **Iterative Refinement**: Agents improve responses through multiple iterations, enhancing accuracy and completeness.
- **Response Blending**: Combines refined responses into a single, optimal answer.
- **User Feedback Loop**: Incorporates user feedback for further refinement.
- **Context Retention Option**: Users can choose to retain conversation context for follow-up prompts, allowing for more coherent and context-aware interactions.
- **Parallel Processing**: Agents perform independent tasks concurrently where appropriate, improving efficiency.
- **Robust Error Handling**: Implements retry mechanisms and extensive logging.

## Prerequisites

- **Python 3.7** or higher
- **OpenAI Python Library**
- **colorama** library for colored console output
- **tiktoken** library for accurate token counting

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/AdieLaine/multi-agent-reasoning.git
   ```

2. **Navigate to the project directory**:

   ```bash
   cd multi-agent-reasoning
   ```

3. **Install the required packages**:

   ```bash
   pip install openai colorama tiktoken
   ```

4. **Set your OpenAI API key**:

   Set your API key as an environment variable:

   ```bash
   export OPENAI_API_KEY='your-api-key-here'
   ```

   Alternatively, you can set it directly in your script or use a `.env` file.

## Usage

Run the script using Python:

```bash
python reasoning.py
```

Follow the on-screen prompts to interact with the chatbot. Type your question when prompted, and the agents will collaborate through a multi-stage reasoning process to provide an optimal response.

---

## Models

The Multi-Agent Reasoning system uses GPT-4, GPT-turbo, GPT-4o, GPT-4o-mini, o1-mini, o1-preview.

## Agents' Reasoning Process

The core of the chatbot's functionality lies in the reasoning process employed by the agents. This process is designed to simulate a collaborative environment where agents think critically, verify facts, challenge each other's perspectives, and refine their responses based on constructive feedback.

### Step 1: Initial Discussion

**Objective**: Agents generate their initial responses to the user's prompt based on their individual reasoning and knowledge.

- **Process**:
  - Each agent independently formulates a response to the user's question.
  - Agents do not share their initial thoughts at this stage, ensuring diversity in perspectives.

*Example*:

- **User Prompt**: "What are the benefits of renewable energy?"
- **Agent A's Initial Response**: Provides a general overview of renewable energy benefits.
- **Agent B's Initial Response**: Focuses on environmental impacts and long-term sustainability.

### Step 2: Verification

**Objective**: Agents verify the accuracy and validity of their own responses to ensure factual correctness.

- **Process**:
  - Each agent reviews their initial response, checking for errors or inaccuracies.
  - External sources or internal knowledge bases may be utilized for verification.

*Example*:

- **Agent A** confirms the statistics provided about energy efficiency.
- **Agent B** verifies the environmental data mentioned in the response.

### Step 3: Critiquing

**Objective**: Agents critique each other's verified responses to identify areas of improvement, omissions, or biases.

- **Process**:
  - Agent A critiques Agent B's response, and vice versa.
  - Critiques focus on accuracy, completeness, clarity, and relevance.

*Example*:

- **Agent A** notes that Agent B did not mention economic benefits.
- **Agent B** points out that Agent A's response lacks discussion on technological advancements.

### Step 4: Refinement

**Objective**: Agents refine their own responses by incorporating feedback from critiques and improving upon their initial reasoning.

- **Process**:
  - Agents revise their responses, addressing the points raised during critiquing.
  - They aim to enhance accuracy, depth, and clarity.

*Example*:

- **Agent A** adds information about technological advancements in renewable energy.
- **Agent B** includes economic benefits and cost-effectiveness analyses.

### Step 5: Response Blending

**Objective**: Combine the refined responses from all agents into a single, cohesive, and comprehensive answer.

- **Process**:
  - Responses are blended using an algorithm or model that synthesizes the information.
  - The combined response aims to include the strengths of each agent's contribution.

*Example*:

- The final response covers environmental impacts, economic benefits, technological advancements, and societal implications.

### Step 6: User Feedback Loop

**Objective**: Incorporate the user's feedback to further refine the response, ensuring satisfaction and accuracy.

- **Process**:
  - The user is asked if the response was helpful and accurate.
  - If not, agents perform additional refinement iterations, potentially taking more time or focusing on specific areas indicated by the user.

*Example*:

- **User Feedback**: "Can you provide more details on cost savings?"
- **Agents** refine the response to include detailed cost analyses and examples.

### Step 7: Context Retention

**Objective**: Allow the conversation to maintain context across multiple user prompts for a coherent dialogue.

- **Process**:
  - The user is prompted to decide whether to retain the conversation context for the next prompt.
  - If retained, agents can reference previous interactions to provide more contextualized responses.

*Example*:

- **User**: "What about the challenges?"
- **Agents**, with context retained, understand that the user refers to challenges related to renewable energy.

---

## Code Logic Explanation

The code is structured to facilitate the reasoning process of the agents through carefully designed classes and functions.

### Imports and Initialization

- **Libraries**:
  - `os`, `time`, `logging`: For system operations, timing, and logging.
  - `concurrent.futures.ThreadPoolExecutor`: For parallel processing.
  - `colorama`: For colored console output.
  - `tiktoken`: For accurate token counting.
  - `openai.OpenAI`: To interact with OpenAI's API.

- **Initialization**:
  - Colorama is initialized.
  - Logging is configured to output to both console and file.
  - OpenAI client is initialized with the API key.
  - Constants are defined for token limits, retry attempts, and refinement attempts.

### Agent Class

**Purpose**: Represents an AI agent capable of performing various reasoning actions.

- **Attributes**:
  - `name`: The agent's name.
  - `color`: The display color for console output.
  - `messages`: A list to store the conversation history.

- **Methods**:
  - `_add_message()`: Adds messages to the conversation history while enforcing token limits.
  - `_handle_chat_response()`: Handles communication with the OpenAI API, including retries and timing.
  - `discuss()`: Formulates an initial response to the user's prompt.
  - `verify()`: Verifies the accuracy of a given response.
  - `critique()`: Critiques another agent's response.
  - `refine()`: Refines a response based on feedback and optional parameters for depth.

### Main Workflow

The script follows the reasoning steps outlined in the **Agents' Reasoning Process** section:

1. **User Prompt**: Captures the user's question.
2. **Initial Discussion**: Agents independently generate initial responses.
3. **Verification**: Agents verify their own responses.
4. **Critiquing**: Agents critique each other's verified responses.
5. **Refinement**: Agents refine their responses based on critiques.
6. **Response Blending**: Blends the agents' refined responses into a single answer.
7. **User Feedback Loop**: Incorporates user feedback for further refinement.
8. **Context Retention**: Prompts the user to retain or reset the conversation context.

### Parallel Processing

- **Implementation**: Uses `ThreadPoolExecutor` to parallelize certain steps, such as verification, where agents' tasks are independent.
- **Benefit**: Improves efficiency by performing independent operations concurrently.

### Error Handling and Logging

- **Retry Logic**: Implements retries with exponential backoff in case of API failures.
- **Logging**: All significant events and errors are logged for troubleshooting and analysis.
- **Exception Handling**: Ensures that exceptions are caught and do not crash the program.

---

## Visual Flow of the Reasoning Process

Below is a detailed and logically structured flowchart of the reasoning process employed by the **Multi-Agent Reasoning**:

![alt text](img/reasoningflow.png)

---

## Contributing

Contributions are welcome! To contribute:

1. **Fork the repository**.
2. **Create a new branch** for your feature or bug fix.
3. **Commit** your changes with clear, descriptive messages.
4. **Push** your branch to your fork.
5. **Submit a pull request** explaining your changes.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Setting Up the GitHub Repository

To prepare the GitHub repository:

1. **Create a new repository** on GitHub named `multi-agent-reasoning`.
2. **Add the `README.md`** file with this content.
3. **Include the `reasoning.py`** script in the root directory.
4. **Create a `.gitignore`** file to exclude unnecessary files:

   ```gitignore
   # Exclude log files
   assistant.log

   # Exclude environment files
   .env

   # Python cache
   __pycache__/
   *.py[cod]
   ```

5. **Commit and push** the files to GitHub.

## Directory Structure

```
multi-agent-reasoning/
├── README.md
├── reasoning.py
├── LICENSE
├── .gitignore
└── img/
    └── reasoningbanner.png
    └── reasoningflow.png  
```