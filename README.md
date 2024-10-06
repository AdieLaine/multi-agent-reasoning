# Multi-Agent Reasoning

A Python-based solution that employs **Multi-Agent Reasoning**, where multiple AI agents collaborate to generate optimal responses to user prompts. By simulating interactions between agents, the system enhances reasoning capabilities to deliver accurate and refined answers. Custom Agents can be added via JSON and customize their personalities, interaction styles, and more.

---

![Multi-Agent Reasoning Banner](img/reasoningbanner.png)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Models](#models)
- [Agents' Reasoning and Chat Process](#agents-reasoning-and-chat-process)
  - [Chat Mode](#chat-mode)
  - [Reasoning Logic Mode](#reasoning-logic-mode)
    - [Step 1: Initial Discussion](#step-1-initial-discussion)
    - [Step 2: Verification](#step-2-verification)
    - [Step 3: Critiquing](#step-3-critiquing)
    - [Step 4: Refinement](#step-4-refinement)
    - [Step 5: Response Blending](#step-5-response-blending)
    - [Step 6: User Feedback Loop](#step-6-user-feedback-loop)
    - [Step 7: Context Retention](#step-7-context-retention)
- [Use of JSON Configuration File](#use-of-json-configuration-file)
- [Code Logic Explanation](#code-logic-explanation)
- [Visual Flow of the Reasoning Process](#visual-flow-of-the-reasoning-process)
- [Contributing](#contributing)
- [License](#license)
- [Setting Up the GitHub Repository](#setting-up-the-github-repository)
- [Directory Structure](#directory-structure)

---

## Overview

The **Multi-Agent Reasoning** script creates an interactive chatbot experience where multiple AI agents collaborate through a structured reasoning process to provide optimal answers. Each agent brings unique perspectives and expertise, and through iterative steps of discussion, verification, critique, and refinement, they converge on a high-quality, accurate response.

Additionally, the system allows users to **chat with individual agents**. Agents are aware of each other, including their personalities and quirks, and can answer questions about one another, providing a rich and interactive experience.

## Features

- **Multi-Agent Collaboration**: Simulates collaborative reasoning between multiple agents.
- **Agent Awareness**: Agents are aware of each other, including their personalities, quirks, and capabilities.
- **Chat with Individual Agents**: Users can choose to chat directly with individual agents, engaging in personalized conversations.
- **Structured Reasoning Process**: Agents engage in a multi-step process including discussion, verification, critique, and refinement.
- **Iterative Refinement**: Agents improve responses through multiple iterations, enhancing accuracy and completeness.
- **Response Blending**: Combines refined responses into a single, optimal answer.
- **User Feedback Loop**: Incorporates user feedback for further refinement.
- **Context Retention Option**: Users can choose to retain conversation context for follow-up prompts, allowing for more coherent and context-aware interactions.
- **Customizable Agents**: Agents are configured via a JSON file, allowing easy customization of their personalities, interaction styles, and other attributes.
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

Upon running the script, you will be presented with a menu:

```
══════════════════════════════════════════════════════════════════════════
║                  Multi-Agent Reasoning Chatbot                         ║
══════════════════════════════════════════════════════════════════════════
Please select an option:
1. Chat with an agent
2. Use reasoning logic
3. Exit
Enter your choice (1/2/3):
```

- **Option 1: Chat with an agent**

  - Allows you to chat directly with one of the agents.
  - Agents are aware of each other and can answer questions about themselves and other agents.
  - Agents' personalities, quirks, and behaviors are defined in the JSON configuration file.

- **Option 2: Use reasoning logic**

  - Engages the agents in a collaborative reasoning process to answer your prompt.
  - Follows the structured multi-step process to generate an optimal response.

- **Option 3: Exit**

  - Exits the application.

## Models

The Multi-Agent Reasoning system uses various OpenAI models, including `gpt-4o` for chat interactions with the choie of `gpt-4`, `gpt-turbo`, `gpt-4o`, `gpt-4o-mini`,`o1-mini`, `o1-preview` for reasoning logic.

## Agents' Reasoning and Chat Process

## Chat Mode

**Objective**: Allows the user to chat directly with a selected agent.

- **Process**:
  - User selects an agent to chat with.
  - The selected agent interacts with the user, maintaining conversation context.
  - `Agents are aware of each other` and can discuss or answer questions about other agents.
  - Conversations can be in-depth, reflecting the agent's personality and quirks.

*Example*:

- **User**: "Tell me about Agent 74."
- **Agent 47**: Provides information about Agent 74, including personality traits and quirks.

![alt text](img/agents.png)

## Reasoning Logic Mode

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

## Use of JSON Configuration File

Agents are configured via an `agents.json` file, allowing easy customization of their attributes.

- **Location**: Must be placed in the same directory as the `reasoning.py` script.
- **Structure**:

  ```json
  {
    "agents": [
      {
        "name": "Agent 47",
        "system_purpose": "Your primary role is...",
        "interaction_style": { ... },
        "ethical_conduct": { ... },
        "capabilities_limitations": { ... },
        "context_awareness": { ... },
        "adaptability_engagement": { ... },
        "responsiveness": { ... },
        "additional_tools_modules": { ... },
        "personality": {
          "humor_style": "...",
          "friendly_demeanor": "...",
          "personality_traits": ["...", "..."],
          "empathy_level": "...",
          "interaction_style_with_humor": "...",
          "quirks": ["..."]
        }
      },
      {
        "name": "Agent 74",
        "system_purpose": "Your primary role is...",
        "interaction_style": { ... },
        "ethical_conduct": { ... },
        "capabilities_limitations": { ... },
        "context_awareness": { ... },
        "adaptability_engagement": { ... },
        "responsiveness": { ... },
        "additional_tools_modules": { ... },
        "personality": {
          "humor_style": "...",
          "friendly_demeanor": "...",
          "personality_traits": ["...", "..."],
          "empathy_level": "...",
          "interaction_style_with_humor": "...",
          "quirks": ["..."]
        }
      }
    ]
  }
  ```

- **Customization**:

  - You can add or modify agents by editing this file.
  - Define each agent's personality, interaction style, ethical conduct, capabilities, quirks, etc.
  - Agents will be aware of each other based on the information provided in this file.

*Example*:

- **User**: "Do you work with another agent?"
- **Agent**: "Yes, I collaborate with Agent 74, who is analytical and supportive..."

## Code Logic Explanation

The code is structured to facilitate both the reasoning process and chat interactions with agents.

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

**Modifications**:

- **Attributes**:

  - `other_agents_info`: Stores information about other agents, making each agent aware of others.

- **Methods**:

  - `_build_system_message()`: Now includes information about other agents, so the agent can refer to them during interactions.
  - `_handle_chat_interaction()`: Handles the chat interaction logic using the `gpt-4o` model.
  - `discuss()`, `verify()`, `critique()`, `refine()`: Methods supporting the reasoning process.

### Main Workflow

- **Main Menu**: Presents options to chat with an agent or use reasoning logic.
- **Chat Mode**:

  - User selects an agent to chat with.
  - Agents can answer questions about themselves and other agents.
  - Conversation history is maintained, with the option to clear it.

- **Reasoning Logic Mode**:

  - Agents proceed through the structured reasoning steps to generate an optimal response to the user's prompt.

### Agent Initialization

- Agents are initialized based on configurations loaded from the `agents.json` file.
- After all agents are initialized, each agent's `other_agents_info` attribute is populated with information about the other agents.

### Use of JSON File

- Agents' attributes, including personality and quirks, are defined in the `agents.json` file.
- Agents use this information to inform their responses and interactions.

---

## Visual Flow of the Reasoning Process

Below is an updated flowchart reflecting the new logic, including the chat mode and agents' awareness of each other:

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
4. **Include the `agents.json`** file in the root directory.
5. **Create a `.gitignore`** file to exclude unnecessary files:

   ```gitignore
   # Exclude log files
   assistant.log

   # Exclude environment files
   .env

   # Python cache
   __pycache__/
   *.py[cod]
   ```

6. **Commit and push** the files to GitHub.

## Directory Structure

```
multi-agent-reasoning/
├── README.md
├── reasoning.py
├── agents.json
├── LICENSE
├── .gitignore
└── img/
    ├── reasoningbanner.png
    └── reasoningflow.png
    └── agents.png