# Multi-Agent Reasoning

A Python-based solution that employs **Multi-Agent Reasoning**, where multiple AI agents collaborate to generate optimal responses to user prompts. By simulating interactions between agents, the system enhances reasoning capabilities to deliver accurate and refined answers. Custom agents can be added via JSON, allowing you to customize their personalities, interaction styles, and more. The system leverages **Prompt Caching** to optimize performance and reduce latency and costs for repeated prompts.

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
- [Prompt Caching](#prompt-caching)
  - [Overview](#overview-1)
  - [How It Works](#how-it-works)
  - [Monitoring Cache Usage](#monitoring-cache-usage)
  - [Best Practices](#best-practices)
  - [Frequently Asked Questions](#frequently-asked-questions)
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
- **Token Usage Transparency**: Displays token usage information after generating responses, including cached tokens, reasoning tokens, and total tokens used.
- **Prompt Caching**: Utilizes OpenAI's Prompt Caching to reduce latency and costs for repeated prompts.

## Prerequisites

- **Python 3.7** or higher
- **OpenAI Python Library** (compatible with the models used)
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
════════════════════════════════════════════════════════════════════════════════════════
║                        Multi-Agent Reasoning Chatbot                               ║
════════════════════════════════════════════════════════════════════════════════════════
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

The Multi-Agent Reasoning system uses specific OpenAI models:

- **Reasoning Logic**: Uses the `o1-preview-2024-09-12` model for reasoning tasks.
- **Chat Interactions**: Uses the `gpt-4o` model for chat interactions with agents.

These models support advanced features and token usage reporting, allowing the system to provide detailed token usage information after each response.

## Agents' Reasoning and Chat Process

### Chat Mode

**Objective**: Allows the user to chat directly with a selected agent.

- **Process**:
  - User selects an agent to chat with.
  - The selected agent interacts with the user, maintaining conversation context.
  - **Agents are aware of each other** and can discuss or answer questions about other agents.
  - Conversations can be in-depth, reflecting the agent's personality and quirks.
  - **Token Usage Transparency**: After each response, the agent displays token usage statistics, including cached tokens and reasoning tokens.
  - **Prompt Caching**: Utilizes cached prompts to reduce latency and costs.

*Example*:

- **User**: "Tell me about Agent 74."
- **Agent 47**: Provides information about Agent 74, including personality traits and quirks, along with token usage details.

![Agents](img/agents.png)

### Reasoning Logic Mode

The core of the chatbot's functionality lies in the reasoning process employed by the agents. This process is designed to simulate a collaborative environment where agents think critically, verify facts, challenge each other's perspectives, and refine their responses based on constructive feedback.

#### Step 1: Initial Discussion

**Objective**: Agents generate their initial responses to the user's prompt based on their individual reasoning and knowledge.

- **Process**:
  - Each agent independently formulates a response to the user's question, incorporating their unique system messages and personality traits.
  - Agents do not share their initial thoughts at this stage, ensuring diversity in perspectives.
  - **Token Usage Transparency**: Agents display token usage statistics after generating their responses.
  - **Prompt Caching**: Caches common prompt prefixes to optimize performance.

*Example*:

- **User Prompt**: "What are the benefits of renewable energy?"
- **Agent 47's Initial Response**: Provides a logical overview of renewable energy benefits.
- **Agent 74's Initial Response**: Focuses on creative perspectives, such as innovative technologies in renewable energy.

#### Step 2: Verification

**Objective**: Agents verify the accuracy and validity of their own responses to ensure factual correctness.

- **Process**:
  - Each agent reviews their initial response, checking for errors or inaccuracies.
  - **Parallel Processing**: Agents perform verification concurrently to improve efficiency.
  - **Token Usage Transparency**: Token usage is displayed after verification.
  - **Prompt Caching**: Utilizes cached content to reduce processing time.

*Example*:

- **Agent 47** confirms the statistics provided about energy efficiency.
- **Agent 74** verifies the information about emerging renewable technologies.

#### Step 3: Critiquing

**Objective**: Agents critique each other's verified responses to identify areas of improvement, omissions, or biases.

- **Process**:
  - Agents exchange their verified responses.
  - Each agent critiques another agent's response.
  - **Token Usage Transparency**: Token usage is displayed after critiquing.
  - **Prompt Caching**: Cached critiques enhance efficiency.

*Example*:

- **Agent 47** notes that **Agent 74** did not mention economic benefits.
- **Agent 74** points out that **Agent 47**'s response lacks discussion on environmental impacts.

#### Step 4: Refinement

**Objective**: Agents refine their own responses by incorporating feedback from critiques and improving upon their initial reasoning.

- **Process**:
  - Agents revise their responses, addressing the points raised during critiquing.
  - **Token Usage Transparency**: Token usage is displayed after refinement.
  - **Prompt Caching**: Refinement prompts benefit from caching.

*Example*:

- **Agent 47** adds information about environmental impacts in renewable energy.
- **Agent 74** includes economic benefits and cost-effectiveness analyses.

#### Step 5: Response Blending

**Objective**: Combine the refined responses from all agents into a single, cohesive, and comprehensive answer.

- **Process**:
  - Responses are blended using the `blend_responses` function.
  - **Token Usage Transparency**: Displays token usage during blending.
  - **Prompt Caching**: Cached blended responses reduce latency.

*Example*:

- The final response covers environmental impacts, economic benefits, technological advancements, and societal implications.

#### Step 6: User Feedback Loop

**Objective**: Incorporate the user's feedback to further refine the response, ensuring satisfaction and accuracy.

- **Process**:
  - The user is asked if the response was helpful and accurate.
  - If not, agents perform additional refinement iterations.
  - **Iterative Refinement Limits**: Up to `MAX_REFINEMENT_ATTEMPTS`.

*Example*:

- **User Feedback**: "Can you provide more details on cost savings?"
- **Agents** refine the response to include detailed cost analyses and examples.

#### Step 7: Context Retention

**Objective**: Allow the conversation to maintain context across multiple user prompts for a coherent dialogue.

- **Process**:
  - The user is prompted to decide whether to retain the conversation context.
  - If retained, agents can reference previous interactions.

*Example*:

- **User**: "What about the challenges?"
- **Agents**, with context retained, understand that the user refers to challenges related to renewable energy.

---

## Prompt Caching

### Overview

**Prompt Caching** enhances the efficiency of the Multi-Agent Reasoning system by reducing latency and cost when handling repeated or long prompts. It works by caching the longest common prefixes of prompts, allowing for faster processing of subsequent requests that reuse these prefixes.

![Prompt Caching](img/promptcache.png)

### How It Works

- **Automatic Caching**: Prompts longer than 1,024 tokens are automatically considered for caching.
- **Cache Lookup**: When a request is made, the system checks if the initial portion of the prompt is already cached.
- **Cache Hit**:
  - If a matching cached prefix is found, the system uses it.
  - This significantly reduces processing time and computational resources.
- **Cache Miss**:
  - If no matching prefix is found, the full prompt is processed.
  - After processing, the prompt's prefix is cached for future use.

**Cache Duration**:

- Cached prompts typically remain active for 5 to 10 minutes of inactivity.
- During off-peak times, caches may persist for up to one hour.

### Monitoring Cache Usage

- **Usage Metrics**:
  - The API response includes a `usage` field displaying token usage details.
  - Example:
    ```json
    "usage": {
      "prompt_tokens": 2006,
      "completion_tokens": 300,
      "total_tokens": 2306,
      "prompt_tokens_details": {
        "cached_tokens": 1920
      },
      "completion_tokens_details": {
        "reasoning_tokens": 0
      }
    }
    ```
  - `cached_tokens` indicates how many prompt tokens were retrieved from the cache.
- **Token Usage Transparency**:
  - The system displays token usage information after responses, helping users monitor cache effectiveness and costs.

### Best Practices

- **Structure Prompts Effectively**:
  - Place static or frequently reused content at the beginning of the prompt.
  - Dynamic content should be positioned at the end.
- **Maintain Consistency**:
  - Use consistent prompt prefixes to maximize cache hits.
  - Ensure that prompts are identical where caching is desired.
- **Monitor Performance**:
  - Keep an eye on cache hit rates and latency to optimize your caching strategy.
- **Usage Patterns**:
  - Frequent use of the same prompts can keep them in the cache longer.
  - During off-peak hours, cache entries may remain longer, increasing the chance of cache hits.

### Frequently Asked Questions

- **Does Prompt Caching Affect the API's Final Response?**
  - No. Caching only impacts the processing of the prompt, not the generation of the completion. The output will be consistent regardless of caching.
- **How Is Data Privacy Maintained?**
  - Caches are not shared between different organizations. Only members within the same organization can access cached prompts.
- **Is Manual Cache Management Available?**
  - Currently, there is no option to manually clear or manage the cache. Cached prompts are automatically evicted after periods of inactivity.
- **Are There Additional Costs for Using Prompt Caching?**
  - No. Prompt Caching is enabled automatically and does not incur extra charges.
- **Does Prompt Caching Impact Rate Limits?**
  - Yes, requests using cached prompts still count towards your rate limits.
- **Compatibility with Zero Data Retention Requests?**
  - Yes, Prompt Caching is compatible with Zero Data Retention policies.

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
        "system_purpose": "You are a logical and analytical assistant, focusing on facts and clear reasoning.",
        "interaction_style": { ... },
        "ethical_conduct": { ... },
        "capabilities_limitations": { ... },
        "context_awareness": { ... },
        "adaptability_engagement": { ... },
        "responsiveness": { ... },
        "additional_tools_modules": { ... },
        "personality": {
          "logical": "Yes",
          "analytical": "Yes",
          "humor_style": "...",
          "friendly_demeanor": "...",
          "personality_traits": ["Methodical", "Precise"],
          "empathy_level": "Moderate",
          "interaction_style_with_humor": "Dry wit",
          "quirks": ["Uses technical jargon"]
        }
      },
      {
        "name": "Agent 74",
        "system_purpose": "You are a creative and empathetic assistant, emphasizing imaginative solutions and understanding.",
        "interaction_style": { ... },
        "ethical_conduct": { ... },
        "capabilities_limitations": { ... },
        "context_awareness": { ... },
        "adaptability_engagement": { ... },
        "responsiveness": { ... },
        "additional_tools_modules": { ... },
        "personality": {
          "creative": "Yes",
          "empathetic": "Yes",
          "humor_style": "...",
          "friendly_demeanor": "...",
          "personality_traits": ["Imaginative", "Caring"],
          "empathy_level": "High",
          "interaction_style_with_humor": "Playful",
          "quirks": ["Uses metaphors"]
        }
      }
    ]
  }
  ```

- **Customization**:

  - You can add or modify agents by editing this file.
  - Define each agent's personality, interaction style, ethical conduct, capabilities, quirks, etc.
  - **Agent Awareness**: Agents will be aware of each other based on the information provided in this file.

*Example*:

- **User**: "Do you work with another agent?"
- **Agent 47**: "Yes, I collaborate with Agent 74, who is creative and empathetic. Together, we provide comprehensive insights."

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
  - Constants are defined for token limits (`MAX_TOTAL_TOKENS`, `MAX_CHAT_HISTORY_TOKENS`), retry attempts, and refinement attempts.

### Agent Class

**Modifications**:

- **Attributes**:

  - `other_agents_info`: Stores information about other agents, making each agent aware of others.
  - `system_message`: Each agent builds its own system message upon initialization, incorporating its unique `system_purpose` and personality traits.

- **Methods**:

  - `_build_system_message()`: Constructs the agent-specific system message, including personality traits and information about other agents.
  - `_add_message()`: Manages message history, ensuring token limits are not exceeded by trimming older messages while preserving essential context.
  - `_handle_chat_response()`: Handles the reasoning logic interactions using the `o1-preview-2024-09-12` model, including token usage extraction and display.
  - `_handle_chat_interaction()`: Handles the chat interaction logic using the `gpt-4o` model, including token usage extraction and display.
  - `discuss()`, `verify()`, `critique()`, `refine()`: Methods supporting the reasoning process.
  - **Prompt Caching Awareness**: Agents' methods leverage prompt caching to optimize performance and reduce costs.

### Main Workflow

- **Main Menu**: Presents options to chat with an agent or use reasoning logic.
- **Chat Mode**:

  - User selects an agent to chat with.
  - Agents can answer questions about themselves and other agents.
  - Conversation history is maintained, with the option to clear it.
  - Token usage is displayed after each agent response.
  - **Prompt Caching**: Frequently used prompts in chat may benefit from caching.

- **Reasoning Logic Mode**:

  - Agents proceed through the structured reasoning steps to generate an optimal response to the user's prompt.
  - Token usage is displayed after each step.
  - **Prompt Caching**: Common prompt prefixes in reasoning steps can be cached for efficiency.

### Error Handling and Logging

- **Retry Mechanism**:

  - Implements retries with exponential backoff in case of API failures.
  - Prevents the application from crashing due to transient errors.

- **Error Logging**:

  - Detailed error messages are logged to assist with debugging.

### Preventing Errors Related to Message Roles

- **Message Role Adjustment**:

  - The `system_message` is added with a `role` of `"user"` instead of `"system"` to prevent errors with models that do not support the `'system'` role.
  - Ensures compatibility with the models used (`o1-preview-2024-09-12` and `gpt-4o`).

---

## Visual Flow of the Reasoning Process

Below is an updated flowchart reflecting the new logic, including the chat mode, agents' awareness of each other, token usage transparency, and prompt caching:

![Reasoning Process Flowchart](img/reasoningflow.png)

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
    ├── reasoningflow.png
    ├── agents.png
    └── promptcache.png
```

---

Feel free to explore the code, customize the agents, and engage with the Multi-Agent Reasoning chatbot!

If you have any questions or need assistance, please open an issue on GitHub.