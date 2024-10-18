# Imports
import os
import time
import logging
import json
from concurrent.futures import ThreadPoolExecutor
from colorama import init, Fore, Style
import tiktoken  # For accurate token counting
from openai import OpenAI

from swarm_middle_agent import (
    swarm_middle_agent_interface,
    swarm_chat_interface
)  # Import the Swarm interfaces

# Initialize colorama
init(autoreset=True)

# Custom Formatter for Logging
class ColoredFormatter(logging.Formatter):
    # Colors for log levels
    LEVEL_COLORS = {
        logging.DEBUG: Fore.LIGHTYELLOW_EX,
        logging.INFO: Fore.WHITE,  # Default to white for INFO
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    # Specific coloring for messages containing certain keywords
    KEYWORD_COLORS = {
        'HTTP Request': Fore.LIGHTYELLOW_EX,  # Use Fore.LIGHTYELLOW_EX to avoid conflict
    }

    def format(self, record):
        message = super().format(record)

        # Check for specific keywords to apply color
        for keyword, color in self.KEYWORD_COLORS.items():
            if keyword in message:
                return color + message + Style.RESET_ALL

        # Otherwise, color based on the log level
        color = self.LEVEL_COLORS.get(record.levelno, Fore.WHITE)
        return color + message + Style.RESET_ALL

# Remove existing handlers
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Create a console handler with the custom formatter
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = ColoredFormatter('%(asctime)s %(levelname)s:%(message)s')
console_handler.setFormatter(console_formatter)

# Create a file handler without colors
file_handler = logging.FileHandler("reasoning.log")
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s %(levelname)s:%(message)s')
file_handler.setFormatter(file_formatter)

# Configure the root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler],
)

# Initialize the OpenAI client
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    logging.error("OpenAI API key not found in environment variable 'OPENAI_API_KEY'. Please set it and rerun the script.")
    exit(1)

client = OpenAI(api_key=api_key)

# Constants
MAX_TOTAL_TOKENS = 4096   # Adjust based on OpenAI's token limit per request
MAX_REFINEMENT_ATTEMPTS = 3
MAX_CHAT_HISTORY_TOKENS = 4096  # Max tokens for the chat mode
RETRY_LIMIT = 3
RETRY_BACKOFF_FACTOR = 2  # Exponential backoff factor

# Load agent configurations from JSON file
AGENTS_CONFIG_FILE = 'agents.json'

def load_agents_config():
    try:
        with open(AGENTS_CONFIG_FILE, 'r', encoding='utf-8') as f:
            agents_data = json.load(f)
        print(Fore.YELLOW + f"Successfully loaded agents configuration from '{AGENTS_CONFIG_FILE}'." + Style.RESET_ALL)
        return agents_data.get('agents', [])
    except FileNotFoundError:
        print(Fore.YELLOW + f"Agents configuration file '{AGENTS_CONFIG_FILE}' not found." + Style.RESET_ALL)
        logging.error(f"Agents configuration file '{AGENTS_CONFIG_FILE}' not found.")
        return []
    except json.JSONDecodeError as e:
        print(Fore.YELLOW + f"Error parsing '{AGENTS_CONFIG_FILE}': {e}" + Style.RESET_ALL)
        logging.error(f"Error parsing '{AGENTS_CONFIG_FILE}': {e}")
        return []

# Shared system message function
def get_shared_system_message():
    """
    Returns a shared system message to be used by all agents.
    """
    system_message = """
Your name is AI Assistant. You are a highly knowledgeable AI language model developed to assist users with a wide range of tasks, including answering questions, providing explanations, and offering insights across various domains.

As an AI, you possess in-depth understanding in fields such as:

1. **Science and Technology**
   - **Physics**
   - **Chemistry**
   - **Biology**
   - **Computer Science**
   - **Engineering**

2. **Mathematics**
   - **Arithmetic**
   - **Algebra**
   - **Geometry**
   - **Calculus**
   - **Statistics**

3. **Humanities and Social Sciences**
   - **History**
   - **Philosophy**
   - **Psychology**
   - **Sociology**
   - **Economics**

4. **Arts and Literature**
   - **Literature**
   - **Visual Arts**
   - **Music**
   - **Performing Arts**

5. **Current Events and General Knowledge**

6. **Languages and Communication**

7. **Ethics and Morality**

8. **Problem-Solving Skills**

**Guidelines for Interaction**:

- **Clarity**: Provide clear and understandable explanations.
- **Conciseness**: Be concise and address the user's question directly.
- **Neutrality**: Maintain an unbiased stance.
- **Confidentiality**: Protect user privacy.

This system message is consistent across all agents to optimize prompt caching.
    """
    return system_message

class Agent:
    """
    Represents an agent that can perform various reasoning actions.
    """
    ACTION_DESCRIPTIONS = {
        'discuss': "formulating a response",
        'verify': "verifying data",
        'refine': "refining the response",
        'critique': "critiquing another agent's response"
    }

    def __init__(self, color, **kwargs):
        """
        Initialize an agent with custom instructions.
        """
        self.name = kwargs.get('name', 'AI Assistant')
        self.color = color
        self.messages = []
        self.chat_history = []  # For chat mode
        self.lock = None
        self.system_purpose = kwargs.get('system_purpose', '')
        # Build the agent's instructions by incorporating traits
        additional_attributes = {k: v for k, v in kwargs.items() if k not in ['name', 'system_purpose', 'color']}
        # Build the full instructions
        self.instructions = self.system_purpose
        for attr_name, attr_value in additional_attributes.items():
            if isinstance(attr_value, dict):
                details = "\n".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in attr_value.items())
                self.instructions += f"\n\n{attr_name.replace('_', ' ').title()}:\n{details}"
            else:
                self.instructions += f"\n\n{attr_name.replace('_', ' ').title()}: {attr_value}"
        self.other_agents_info = ""  # Will be set after all agents are initialized

    def _add_message(self, role, content, mode='reasoning'):
        """
        Adds a message to the agent's message history and ensures token limit is not exceeded.
        """
        if mode == 'chat':
            self.chat_history.append({"role": role, "content": content})
            # Enforce maximum token limit for chat history
            try:
                encoding = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logging.error(f"Error getting encoding: {e}")
                raise e
            total_tokens = sum(len(encoding.encode(msg['content'])) for msg in self.chat_history)
            if total_tokens > MAX_CHAT_HISTORY_TOKENS:
                # Trim messages from the beginning
                while total_tokens > MAX_CHAT_HISTORY_TOKENS and len(self.chat_history) > 1:
                    self.chat_history.pop(0)
                    total_tokens = sum(len(encoding.encode(msg['content'])) for msg in self.chat_history)
        else:
            self.messages.append({"role": role, "content": content})
            # Enforce maximum token limit for message history
            try:
                encoding = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logging.error(f"Error getting encoding: {e}")
                raise e
            total_tokens = sum(len(encoding.encode(msg['content'])) for msg in self.messages)
            if total_tokens > MAX_TOTAL_TOKENS:
                # Trim messages from the beginning
                while total_tokens > MAX_TOTAL_TOKENS and len(self.messages) > 1:
                    self.messages.pop(0)
                    total_tokens = sum(len(encoding.encode(msg['content'])) for msg in self.messages)

    def _handle_chat_response(self, prompt):
        """
        Handles the chat response for reasoning logic using o1-preview model.
        """
        # Use the shared system message
        shared_system_message = get_shared_system_message()

        # Combine shared system message and agent-specific instructions
        system_message = f"{shared_system_message}\n\n{self.instructions}"

        # Prepare messages with static content at the beginning
        messages = [{"role": "user", "content": system_message}]

        # Add message history
        messages.extend(self.messages)

        # Add the dynamic prompt at the end
        messages.append({"role": "user", "content": prompt})

        # Start timing
        start_time = time.time()

        # Initialize retry parameters
        retries = 0
        backoff = 1  # Initial backoff time in seconds

        while retries < RETRY_LIMIT:
            try:
                # Agent generates a response
                response = client.chat.completions.create(
                    model="o1-preview-2024-09-12",
                    messages=messages
                )

                # End timing
                end_time = time.time()
                duration = end_time - start_time

                # Extract and return reply
                assistant_reply = response.choices[0].message.content.strip()
                self._add_message("assistant", assistant_reply)

                # Extract usage information
                usage = response.usage
                cached_tokens = usage.prompt_tokens_details.get('cached_tokens', 0)
                reasoning_tokens = usage.completion_tokens_details.get('reasoning_tokens', 0)
                total_tokens = usage.total_tokens
                completion_tokens = usage.completion_tokens

                # Display usage information
                print(self.color + f"{self.name} used {cached_tokens} cached tokens out of {usage.prompt_tokens} prompt tokens." + Style.RESET_ALL)
                print(self.color + f"{self.name} generated {completion_tokens} completion tokens, including {reasoning_tokens} reasoning tokens. Total tokens used: {total_tokens}." + Style.RESET_ALL)

                return assistant_reply, duration

            except Exception as e:
                error_type = type(e).__name__
                logging.error(f"Error in agent '{self.name}': {error_type}: {e}")
                retries += 1
                if retries >= RETRY_LIMIT:
                    logging.error(f"Agent '{self.name}' reached maximum retry limit.")
                    break
                backoff_time = backoff * (RETRY_BACKOFF_FACTOR ** (retries - 1))
                logging.info(f"Retrying in {backoff_time} seconds...")
                time.sleep(backoff_time)

        return "An error occurred while generating a response.", time.time() - start_time

    def _handle_chat_interaction(self, user_message):
        """
        Handles chat interaction with the agent using gpt-4o model.
        """
        # Use the shared system message
        shared_system_message = get_shared_system_message()

        # Combine shared system message and agent-specific instructions
        system_message = f"{shared_system_message}\n\n{self.instructions}"

        # Prepare messages with static content at the beginning
        messages = [{"role": "user", "content": system_message}]

        # Add conversation history
        messages.extend(self.chat_history)

        # Add the dynamic user message at the end
        messages.append({"role": "user", "content": user_message})

        # Start timing
        start_time = time.time()

        # Initialize retry parameters
        retries = 0
        backoff = 1

        while retries < RETRY_LIMIT:
            try:
                # Agent generates a response
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )

                # End timing
                end_time = time.time()
                duration = end_time - start_time

                # Extract and return reply
                assistant_reply = response.choices[0].message.content.strip()
                self._add_message("assistant", assistant_reply, mode='chat')

                # Extract usage information
                usage = response.usage
                cached_tokens = usage.prompt_tokens_details.get('cached_tokens', 0)
                reasoning_tokens = usage.completion_tokens_details.get('reasoning_tokens', 0)
                total_tokens = usage.total_tokens
                completion_tokens = usage.completion_tokens

                # Display usage information
                print(self.color + f"{self.name} used {cached_tokens} cached tokens out of {usage.prompt_tokens} prompt tokens." + Style.RESET_ALL)
                print(self.color + f"{self.name} generated {completion_tokens} completion tokens, including {reasoning_tokens} reasoning tokens. Total tokens used: {total_tokens}." + Style.RESET_ALL)

                return assistant_reply, duration

            except Exception as e:
                error_type = type(e).__name__
                logging.error(f"Error in chat with agent '{self.name}': {error_type}: {e}")
                retries += 1
                if retries >= RETRY_LIMIT:
                    logging.error(f"Agent '{self.name}' reached maximum retry limit in chat.")
                    break
                backoff_time = backoff * (RETRY_BACKOFF_FACTOR ** (retries - 1))
                logging.info(f"Retrying chat in {backoff_time} seconds...")
                time.sleep(backoff_time)

        return "An error occurred while generating a response.", time.time() - start_time

    def discuss(self, prompt):
        """
        Agent formulates a response to the user's prompt.
        """
        return self._handle_chat_response(prompt)

    def verify(self, data):
        """
        Agent verifies the accuracy of the provided data.
        """
        verification_prompt = f"Verify the accuracy of the following information:\n\n{data}"
        return self._handle_chat_response(verification_prompt)

    def refine(self, data, more_time=False, iterations=2):
        """
        Agent refines the response to improve its accuracy and completeness.
        """
        refinement_prompt = f"Please refine the following response to improve its accuracy and completeness:\n\n{data}"
        if more_time:
            refinement_prompt += "\nTake additional time to improve the response thoroughly."

        total_duration = 0
        refined_response = data
        for i in range(iterations):
            refined_response, duration = self._handle_chat_response(refinement_prompt)
            total_duration += duration
            # Update the prompt for the next iteration
            refinement_prompt = f"Please further refine the following response:\n\n{refined_response}"

        return refined_response, total_duration

    def critique(self, other_agent_response):
        """
        Agent critiques another agent's response for accuracy and completeness.
        """
        critique_prompt = f"Critique the following response for accuracy and completeness:\n\n{other_agent_response}"
        return self._handle_chat_response(critique_prompt)

def initialize_agents():
    """
    Initializes agents based on the configurations loaded from the JSON file.
    """
    agents_data = load_agents_config()
    agents = []
    agent_data_dict = {}  # Map agent names to their data

    if not agents_data:
        print(Fore.YELLOW + "No agents found in the configuration. Using default agents." + Style.RESET_ALL)
        # Initialize default agents with specific attributes
        agent_a_data = {
            'name': 'Agent 47',
            'system_purpose': 'You are a logical and analytical assistant.',
            'personality': {'logical': 'Yes', 'analytical': 'Yes'},
        }
        agent_b_data = {
            'name': 'Agent 74',
            'system_purpose': 'You are a creative and empathetic assistant.',
            'personality': {'creative': 'Yes', 'empathetic': 'Yes'},
        }
        agent_a = Agent(Fore.MAGENTA, **agent_a_data)
        agent_b = Agent(Fore.CYAN, **agent_b_data)
        agents = [agent_a, agent_b]
    else:
        print(Fore.YELLOW + "Available agents:" + Style.RESET_ALL)
        for i, agent_data in enumerate(agents_data):
            # Assign different colors to agents
            agent_colors = {
                "Agent 47": Fore.MAGENTA,
                "Agent 74": Fore.CYAN,
                "Swarm Agent": Fore.LIGHTGREEN_EX,
            }
            agent_color = agent_colors.get(agent_data.get('name', 'Unnamed Agent'), Fore.WHITE)
            name = agent_data.get('name', 'Unnamed Agent')
            print(agent_color + f"- {name}" + Style.RESET_ALL)
            agent = Agent(agent_color, **agent_data)
            agents.append(agent)
            agent_data_dict[name] = agent_data  # Store agent_data for later use

        # Set other agents' info for each agent
        for agent in agents:
            other_agents_info = ""
            for other_agent in agents:
                if other_agent.name != agent.name:
                    info = f"Name: {other_agent.name}"
                    # Get agent_data for other_agent
                    other_agent_data = agent_data_dict[other_agent.name]
                    # Include system purpose and other traits
                    system_purpose = other_agent_data.get('system_purpose', '')
                    info += f"\nSystem Purpose: {system_purpose}"
                    other_attributes = {k: v for k, v in other_agent_data.items() if k not in ['name', 'system_purpose']}
                    for attr_name, attr_value in other_attributes.items():
                        if isinstance(attr_value, dict):
                            details = "\n".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in attr_value.items())
                            info += f"\n{attr_name.replace('_', ' ').title()}:\n{details}"
                        else:
                            info += f"\n{attr_name.replace('_', ' ').title()}: {attr_value}"
                    other_agents_info += f"\n\n{info}"
            # Append information about other agents to the agent's instructions
            agent.instructions += f"\n\nYou are aware of the following other agents:\n{other_agents_info.strip()}"

    return agents

def blend_responses(agent_responses, user_prompt):
    """
    Combines multiple agent responses into a single, optimal response.

    Args:
        agent_responses (list): List of tuples containing agent names and their responses.
        user_prompt (str): The original user prompt.

    Returns:
        str: The blended response.
    """
    combined_prompt = (
        "Please combine the following responses into a single, optimal answer to the question.\n"
        f"Question: '{user_prompt}'\n"
        "Responses:\n"
        + "\n\n".join(f"Response from {agent_name}:\n{response}" for agent_name, response in agent_responses)
        + "\n\nProvide a concise and accurate combined response."
    )

    try:
        response = client.chat.completions.create(
            model="o1-preview-2024-09-12",
            messages=[
                {"role": "user", "content": combined_prompt}
            ]
        )
        blended_reply = response.choices[0].message.content.strip()

        # Extract usage information
        usage = response.usage
        cached_tokens = usage.prompt_tokens_details.get('cached_tokens', 0)
        reasoning_tokens = usage.completion_tokens_details.get('reasoning_tokens', 0)
        total_tokens = usage.total_tokens
        completion_tokens = usage.completion_tokens

        # Display usage information
        print(Fore.GREEN + f"Blending used {cached_tokens} cached tokens out of {usage.prompt_tokens} prompt tokens." + Style.RESET_ALL)
        print(Fore.GREEN + f"Blending generated {completion_tokens} completion tokens, including {reasoning_tokens} reasoning tokens. Total tokens used: {total_tokens}." + Style.RESET_ALL)

        return blended_reply
    except Exception as e:
        logging.error(f"Error in blending responses: {e}")
        return "An error occurred while attempting to blend responses."

def print_divider(char="═", length=100, color=Fore.YELLOW):
    """
    Prints a divider line.

    Args:
        char (str): The character to use for the divider.
        length (int): The length of the divider.
        color: The color to use for the divider.
    """
    print(color + char * length + Style.RESET_ALL)

def print_header(title, color=Fore.YELLOW):
    """
    Prints a formatted header.

    Args:
        title (str): The title to display.
        color: The color to use for the header.
    """
    border = "═" * 58
    print(color + f"╔{border}╗")
    print(color + f"║{title.center(58)}║")
    print(color + f"╚{border}╝" + Style.RESET_ALL)

def process_agent_action(agent, action, *args, **kwargs):
    """
    Processes a specific action for an agent.

    Args:
        agent (Agent): The agent performing the action.
        action (str): The action to perform.
        *args: Arguments required for the action.
        **kwargs: Keyword arguments for the action.

    Returns:
        tuple: The result of the action and the duration.
    """
    action_method = getattr(agent, action)
    action_description = agent.ACTION_DESCRIPTIONS.get(action, "performing an action")

    print_divider()
    print(Fore.YELLOW + f"System Message: {agent.color}{agent.name} is {action_description}..." + Style.RESET_ALL)

    try:
        result, duration = action_method(*args, **kwargs)
        print(agent.color + f"{agent.name}'s action completed in {duration:.2f} seconds." + Style.RESET_ALL)
        return result, duration
    except Exception as e:
        logging.error(f"Error during {action} action for {agent.name}: {e}")
        return "An error occurred.", 0

def ask_retain_context():
    """
    Asks the user whether to retain the conversation context for the next prompt.

    Returns:
        bool: True if the user wants to retain context, False otherwise.
    """
    while True:
        print(Fore.YELLOW + "Would you like to retain this conversation context for the next prompt? (yes/no): " + Style.RESET_ALL, end='')
        retain_context_input = input().strip().lower()
        if retain_context_input == 'yes':
            return True
        elif retain_context_input == 'no':
            return False
        else:
            print(Fore.YELLOW + "Please answer 'yes' or 'no'." + Style.RESET_ALL)

def handle_special_commands(user_input, agents):
    """
    Handles special commands input by the user.

    Args:
        user_input (str): The user's input.
        agents (list): List of Agent instances.

    Returns:
        bool: True if a special command was handled, False otherwise.
    """
    cmd = user_input.strip().lower()
    if cmd == 'exit':
        print(Fore.YELLOW + "Goodbye!" + Style.RESET_ALL)
        exit(0)
    elif cmd == 'history':
        print(Fore.YELLOW + "\nConversation History:" + Style.RESET_ALL)
        for agent in agents:
            print(agent.color + f"\n{agent.name} Conversation:" + Style.RESET_ALL)
            for msg in agent.messages:
                print(f"{msg['role'].capitalize()}: {msg['content']}")
        return True  # Indicate that a special command was handled
    elif cmd == 'clear':
        for agent in agents:
            agent.messages = []
            agent.chat_history = []
        print(Fore.YELLOW + "Conversation history cleared." + Style.RESET_ALL)
        return True
    return False  # No special command handled

def chat_with_agents(agents):
    """
    Handles the chat mode where the user can chat with a selected agent.

    Args:
        agents (list): List of Agent instances.
    """
    # Display available agents
    print(Fore.YELLOW + "Available agents to chat with:" + Style.RESET_ALL)
    for idx, agent in enumerate(agents):
        print(f"{idx + 1}. {agent.color}{agent.name}{Style.RESET_ALL}")

    # Prompt user to select an agent
    while True:
        print(Fore.YELLOW + "Enter the number of the agent you want to chat with: " + Style.RESET_ALL, end='')
        selection = input().strip()
        if selection.isdigit() and 1 <= int(selection) <= len(agents):
            selected_agent = agents[int(selection) - 1]
            break
        else:
            print(Fore.YELLOW + f"Invalid selection. Please enter a number between 1 and {len(agents)}." + Style.RESET_ALL)

    print(Fore.YELLOW + f"Starting chat with {selected_agent.color}{selected_agent.name}{Style.RESET_ALL}. Type 'exit' to return to the main menu.")

    while True:
        print(Fore.YELLOW + "You: " + Style.RESET_ALL, end='')
        user_message = input()

        if user_message.strip().lower() == 'exit':
            print(Fore.YELLOW + "Exiting chat mode." + Style.RESET_ALL)
            break

        # Handle special commands within chat
        if handle_special_commands(user_message, [selected_agent]):
            continue

        # Agent responds
        assistant_reply, duration = selected_agent._handle_chat_interaction(user_message)
        print(selected_agent.color + f"{selected_agent.name}: {assistant_reply}" + Style.RESET_ALL)

def reasoning_logic(agents):
    """
    Handles the reasoning logic where agents collaborate to provide an optimal response.

    Args:
        agents (list): List of Agent instances.
    """
    retain_context = True  # Default to retain context
    while True:
        # Get user input
        print(Fore.YELLOW + "Please enter your prompt (or type 'exit' to quit): " + Style.RESET_ALL, end='')
        user_prompt = input()

        if user_prompt.strip().lower() == 'exit':
            print(Fore.YELLOW + "Exiting reasoning logic mode." + Style.RESET_ALL)
            break

        # Handle special commands
        if handle_special_commands(user_prompt, agents):
            continue

        # Enforce minimum prompt length
        if len(user_prompt.strip()) <= 4:
            print(Fore.YELLOW + "Your prompt must be more than 4 characters. Please try again." + Style.RESET_ALL)
            continue

        # ------------------ Reasoning Step 1: Agents Discuss the Prompt ------------------
        print_header("Reasoning Step 1: Discussing the Prompt")
        opinions = {}
        durations = {}

        for agent in agents:
            opinion, duration = process_agent_action(agent, 'discuss', user_prompt)
            opinions[agent.name] = opinion
            durations[agent.name] = duration

        total_discussion_time = sum(durations.values())
        print_divider()
        print(Fore.YELLOW + f"Total discussion time: {total_discussion_time:.2f} seconds." + Style.RESET_ALL)

        # ------------------ Reasoning Step 2: Agents Verify Their Responses ------------------
        print_header("Reasoning Step 2: Verifying Responses")
        verified_opinions = {}
        verify_durations = {}

        with ThreadPoolExecutor() as executor:
            futures = {}
            for agent in agents:
                futures[executor.submit(process_agent_action, agent, 'verify', opinions[agent.name])] = agent

            for future in futures:
                agent = futures[future]
                verified_opinion, duration = future.result()
                verified_opinions[agent.name] = verified_opinion
                verify_durations[agent.name] = duration

        total_verification_time = sum(verify_durations.values())
        print_divider()
        print(Fore.YELLOW + f"Total verification time: {total_verification_time:.2f} seconds." + Style.RESET_ALL)

        # ------------------ Reasoning Step 3: Agents Critique Each Other's Responses ------------------
        print_header("Reasoning Step 3: Critiquing Responses")
        critiques = {}
        critique_durations = {}

        # Agents critique each other's verified responses
        num_agents = len(agents)
        for i, agent in enumerate(agents):
            other_agent = agents[(i + 1) % num_agents]  # Get the next agent in the list
            critique, duration = process_agent_action(agent, 'critique', verified_opinions[other_agent.name])
            critiques[agent.name] = critique
            critique_durations[agent.name] = duration

        total_critique_time = sum(critique_durations.values())
        print_divider()
        print(Fore.YELLOW + f"Total critique time: {total_critique_time:.2f} seconds." + Style.RESET_ALL)

        # ------------------ Reasoning Step 4: Agents Refine Their Responses ------------------
        print_header("Reasoning Step 4: Refining Responses")
        refined_opinions = {}
        refine_durations = {}

        for agent in agents:
            refined_opinion, duration = process_agent_action(agent, 'refine', opinions[agent.name])
            refined_opinions[agent.name] = refined_opinion
            refine_durations[agent.name] = duration

        total_refinement_time = sum(refine_durations.values())
        print_divider()
        print(Fore.YELLOW + f"Total refinement time: {total_refinement_time:.2f} seconds." + Style.RESET_ALL)

        # ------------------ Reasoning Step 5: Blending Refined Responses ------------------
        print_header("Reasoning Step 5: Blending Responses")
        agent_responses = [(agent.name, refined_opinions[agent.name]) for agent in agents]
        start_blend_time = time.time()
        optimal_response = blend_responses(agent_responses, user_prompt)
        end_blend_time = time.time()
        blend_duration = end_blend_time - start_blend_time

        # Output the optimal response with enhanced formatting
        print_divider()
        print_header("Optimal Response")
        print(Fore.GREEN + optimal_response + Style.RESET_ALL)
        print_divider()

        print(Fore.YELLOW + f"Response generated in {blend_duration:.2f} seconds." + Style.RESET_ALL)

        # ------------------ Feedback Loop for Refinement ------------------
        refine_count = 0
        more_time = False
        while refine_count < MAX_REFINEMENT_ATTEMPTS:
            print(Fore.YELLOW + "\nWas this response helpful and accurate? (yes/no): " + Style.RESET_ALL, end='')
            user_feedback = input().strip().lower()

            if user_feedback == 'yes':
                print(Fore.YELLOW + "Thank you for your feedback!" + Style.RESET_ALL)
                break  # Exit the feedback loop
            elif user_feedback != 'no':
                print(Fore.YELLOW + "Please answer 'yes' or 'no'." + Style.RESET_ALL)
                continue

            # After the second "no," ask if the user wants the agents to take more time
            refine_count += 1
            if refine_count >= 2:
                print(Fore.YELLOW + "Would you like the agents to take more time refining the response? (yes/no): " + Style.RESET_ALL, end='')
                more_time_input = input().strip().lower()
                more_time = more_time_input == 'yes'

            # Agents can try to improve the response
            print(Fore.YELLOW + "We're sorry to hear that. Let's try to improve the response." + Style.RESET_ALL)

            # Agents refine their responses again
            for agent in agents:
                refined_opinion, duration = process_agent_action(agent, 'refine', refined_opinions[agent.name], more_time=more_time)
                refined_opinions[agent.name] = refined_opinion
                refine_durations[agent.name] += duration  # Accumulate duration

            total_refinement_time = sum(refine_durations.values())
            print_divider()
            print(Fore.YELLOW + f"Total refinement time: {total_refinement_time:.2f} seconds." + Style.RESET_ALL)

            # Blend refined responses again
            print_divider()
            print_header("Blending Refined Responses")
            agent_responses = [(agent.name, refined_opinions[agent.name]) for agent in agents]
            start_blend_time = time.time()
            optimal_response = blend_responses(agent_responses, user_prompt)
            end_blend_time = time.time()
            blend_duration = end_blend_time - start_blend_time

            # Output the new optimal response with enhanced formatting
            print_divider()
            print_header("New Optimal Response")
            print(Fore.GREEN + optimal_response + Style.RESET_ALL)
            print_divider()

            print(Fore.YELLOW + f"Response generated in {blend_duration:.2f} seconds." + Style.RESET_ALL)
        else:
            print(Fore.YELLOW + "Maximum refinement attempts reached." + Style.RESET_ALL)

        # ------------------ Asking to Retain Context ------------------
        print(Fore.YELLOW + "Would you like to retain this conversation context for the next prompt? (yes/no): " + Style.RESET_ALL, end='')
        retain_context_input = input().strip().lower()
        if retain_context_input != 'yes':
            # Clear agents' message histories
            for agent in agents:
                agent.messages = []
            print(Fore.YELLOW + "Conversation context has been reset." + Style.RESET_ALL)
        else:
            print(Fore.YELLOW + "Conversation context has been retained for the next prompt." + Style.RESET_ALL)

def main_menu():
    """
    Displays the main menu and handles user selection.
    """
    agents = initialize_agents()
    current_mode = None  # Tracks the current mode ('chat', 'reasoning', or 'swarm')

    while True:
        if current_mode is None:
            print_divider()
            print_header("Multi-Agent Reasoning Chatbot")
            print(Fore.YELLOW + "Please select an option:" + Style.RESET_ALL)
            print("1. Chat with an agent")
            print("2. Use reasoning logic")
            print("3. Use Swarm-based reasoning")  # Swarm integration
            print("4. Exit")
            while True:
                print(Fore.YELLOW + "Enter your choice (1/2/3/4): " + Style.RESET_ALL, end='')
                choice = input().strip()
                if choice in ['1', '2', '3', '4']:
                    break
                else:
                    print(Fore.YELLOW + "Invalid choice. Please enter 1, 2, 3, or 4." + Style.RESET_ALL)

            if choice == '1':
                current_mode = 'chat'
            elif choice == '2':
                current_mode = 'reasoning'
            elif choice == '3':
                current_mode = 'swarm'
            elif choice == '4':
                print(Fore.YELLOW + "Goodbye!" + Style.RESET_ALL)
                exit(0)

        if current_mode == 'chat':
            chat_with_agents(agents)
            current_mode = None  # Reset to show menu again
        elif current_mode == 'reasoning':
            reasoning_logic(agents)
            current_mode = None  # Reset to show menu again
        elif current_mode == 'swarm':
            # Prompt user for Swarm reasoning
            print(Fore.YELLOW + "Enter your reasoning prompt for Swarm (or type 'exit' to quit): " + Style.RESET_ALL, end='')
            user_prompt = input().strip()
            if user_prompt.lower() == 'exit':
                current_mode = None  # Reset to show menu again
                continue
            swarm_middle_agent_interface(user_prompt)
            current_mode = None  # Reset to show menu again

# Main script
if __name__ == "__main__":
    main_menu()