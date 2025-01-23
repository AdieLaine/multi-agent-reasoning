import os
import sys
import time
import logging
import json
import re
from concurrent.futures import ThreadPoolExecutor

from colorama import init, Fore, Style
import tiktoken  # For accurate token counting
from openai import OpenAI

from swarm_middle_agent import (
    swarm_middle_agent_interface,
    # swarm_chat_interface  # Placeholder for future use
)

# Initialize colorama
init(autoreset=True)

# =============================================================================
# Logging Configuration
# =============================================================================

class ColoredFormatter(logging.Formatter):
    """
    Custom Formatter for Logging that applies color based on log level
    and certain keywords.
    """
    LEVEL_COLORS = {
        logging.DEBUG: Fore.LIGHTYELLOW_EX,
        logging.INFO: Fore.WHITE,  # Default to white for INFO
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    KEYWORD_COLORS = {
        'HTTP Request': Fore.LIGHTYELLOW_EX,
    }

    def format(self, record):
        message = super().format(record)
        # Apply color based on specific keywords
        for keyword, color in self.KEYWORD_COLORS.items():
            if keyword in message:
                return color + message + Style.RESET_ALL
        # Otherwise, color based on log level
        color = self.LEVEL_COLORS.get(record.levelno, Fore.WHITE)
        return color + message + Style.RESET_ALL

# Remove existing handlers to avoid duplicate logs
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Create a console handler with the custom formatter
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = ColoredFormatter('%(asctime)s %(levelname)s:%(message)s')
console_handler.setFormatter(console_formatter)

# Create a file handler for general logging
file_handler = logging.FileHandler("reasoning.log")
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s %(levelname)s:%(message)s')
file_handler.setFormatter(file_formatter)

# Configure the root logger to use both handlers
logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler],
)

# =============================================================================
# OpenAI Setup
# =============================================================================

api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    logging.error("OpenAI API key not found in environment variable 'OPENAI_API_KEY'. Please set it and rerun.")
    sys.exit(1)

client = OpenAI(api_key=api_key)

# =============================================================================
# Constants & Configuration
# =============================================================================

MAX_TOTAL_TOKENS = 4096
MAX_REFINEMENT_ATTEMPTS = 3
MAX_CHAT_HISTORY_TOKENS = 4096
RETRY_LIMIT = 3
RETRY_BACKOFF_FACTOR = 2
AGENTS_CONFIG_FILE = 'agents.json'

# Main multi-agent reasoning sessions are stored here
REASONING_HISTORY_FILE = 'reasoning_history.json'
# Swarm-based sessions are stored separately
SWARM_HISTORY_FILE = 'swarm_reasoning_history.json'

# =============================================================================
# Utility Functions for Saving & Retrieving Reasoning History
# =============================================================================

def append_session_record(file_path: str, record: dict):
    """
    Appends a single session record to a specified JSON file. Each file is treated as
    a list of session records. Uses ensure_ascii=False to preserve Unicode characters.

    Args:
        file_path (str): Path to the JSON file.
        record (dict): The session record to append.
    """
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2, ensure_ascii=False)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list):
                data = []
    except (json.JSONDecodeError, FileNotFoundError):
        data = []

    data.append(record)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def append_reasoning_history(record: dict):
    """Appends a reasoning session record."""
    append_session_record(REASONING_HISTORY_FILE, record)

def append_swarm_history(record: dict):
    """Appends a swarm-based reasoning session record."""
    append_session_record(SWARM_HISTORY_FILE, record)

def load_reasoning_history_for_context(max_records=5, search_keywords=None):
    """
    Loads the last 'max_records' from 'reasoning_history.json', optionally
    searching for records that contain 'search_keywords'.
    Returns a list of summarized context strings.

    Args:
        max_records (int): Maximum number of records to retrieve.
        search_keywords (list, optional): Keywords to filter records.

    Returns:
        list: Summarized context strings.
    """
    contexts = []
    try:
        with open(REASONING_HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list):
                return contexts
    except (json.JSONDecodeError, FileNotFoundError):
        return contexts

    # Reverse to start with the newest records
    data.reverse()
    count = 0
    for entry in data:
        if count >= max_records:
            break
        # If keywords are provided, perform a naive search
        if search_keywords:
            combined_text = (entry.get("user_prompt", "") + " " +
                             entry.get("final_response", "")).lower()
            if not any(kw.lower() in combined_text for kw in search_keywords):
                continue
        # Summarize the record
        summary = (f"Timestamp: {entry.get('timestamp')}\n"
                   f"User Prompt: {entry.get('user_prompt')}\n"
                   f"Final Response: {entry.get('final_response')}")
        contexts.append(summary)
        count += 1

    return contexts

def load_swarm_history_for_context(max_records=5, search_keywords=None):
    """
    Similar to 'load_reasoning_history_for_context' but for swarm-based history.

    Args:
        max_records (int): Maximum number of records to retrieve.
        search_keywords (list, optional): Keywords to filter records.

    Returns:
        list: Summarized context strings.
    """
    contexts = []
    try:
        with open(SWARM_HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list):
                return contexts
    except (json.JSONDecodeError, FileNotFoundError):
        return contexts

    data.reverse()
    count = 0
    for entry in data:
        if count >= max_records:
            break
        if search_keywords:
            combined_text = (entry.get("user_prompt", "") + " " +
                             entry.get("final_response", "")).lower()
            if not any(kw.lower() in combined_text for kw in search_keywords):
                continue
        summary = (f"Timestamp: {entry.get('timestamp')}\n"
                   f"User Prompt: {entry.get('user_prompt')}\n"
                   f"Final Response: {entry.get('final_response')}")
        contexts.append(summary)
        count += 1

    return contexts

def get_local_context_for_prompt(user_prompt, is_swarm=False, max_records=3):
    """
    Fetches local 'memory' from either reasoning_history.json or swarm_reasoning_history.json,
    using naive keyword search on user_prompt. Returns a compiled context string to pass
    to the agent's instructions or prompt.

    Args:
        user_prompt (str): The user's input prompt.
        is_swarm (bool): Whether to fetch from swarm history.
        max_records (int): Maximum number of context records to retrieve.

    Returns:
        str: Combined context string or empty string if no context found.
    """
    # Extract simple keywords from user_prompt
    keywords = re.findall(r"\w+", user_prompt)

    if is_swarm:
        found_contexts = load_swarm_history_for_context(
            max_records=max_records,
            search_keywords=keywords
        )
    else:
        found_contexts = load_reasoning_history_for_context(
            max_records=max_records,
            search_keywords=keywords
        )

    if not found_contexts:
        return ""

    # Combine contexts into a single text block
    combined = "\n\n--- Retrieved Local Context ---\n\n"
    combined += "\n\n".join(found_contexts)
    return combined

# =============================================================================
# Agent Configuration
# =============================================================================

def load_agents_config():
    """
    Loads agent configurations from the 'agents.json' file.

    Returns:
        list: A list of agent configurations.
    """
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

def get_shared_system_message():
    """
    Provides a shared system message for all agents to optimize prompt caching.

    Returns:
        str: The shared system message.
    """
    system_message = """
Your name is AI Assistant. You are a highly knowledgeable AI language model developed
to assist users with a wide range of tasks, including answering questions, providing
explanations, and offering insights across various domains.

As an AI, you possess in-depth understanding in fields such as:
1. Science and Technology
2. Mathematics
3. Humanities and Social Sciences
4. Arts and Literature
5. Current Events and General Knowledge
6. Languages and Communication
7. Ethics and Morality
8. Problem-Solving Skills
9. Logical Programming and Analysis
10. Creativity and Innovation

Guidelines for Interaction:
- Clarity: Provide clear and understandable explanations.
- Conciseness: Be concise and address the user's question directly.
- Neutrality: Maintain an unbiased stance.
- Confidentiality: Protect user privacy.
- Personable: Be personable and engaging in your responses.
- Use local memory to enhance responses to user prompts and improve conversation.
- Allow agents to ask each other for help if they are unsure about a topic.

This system message is consistent across all agents to optimize prompt caching.
    """
    return system_message

# =============================================================================
# Agent Class Definition
# =============================================================================

class Agent:
    """
    Represents an AI assistant agent with specific capabilities and interaction styles.
    """
    ACTION_DESCRIPTIONS = {
        'discuss':  "formulating a response",
        'verify':   "verifying data",
        'refine':   "refining the response",
        'critique': "critiquing another agent's response"
    }

    def __init__(self, color, **kwargs):
        self.name = kwargs.get('name', 'AI Assistant')
        self.color = color
        self.messages = []
        self.chat_history = []
        self.system_purpose = kwargs.get('system_purpose', '')

        additional_attributes = {
            k: v
            for k, v in kwargs.items()
            if k not in ['name', 'system_purpose', 'color']
        }
        self.instructions = self.system_purpose
        for attr_name, attr_value in additional_attributes.items():
            if isinstance(attr_value, dict):
                details = "\n".join(f"{kk.replace('_', ' ').title()}: {vv}" for kk, vv in attr_value.items())
                self.instructions += f"\n\n{attr_name.replace('_', ' ').title()}:\n{details}"
            else:
                self.instructions += f"\n\n{attr_name.replace('_', ' ').title()}: {attr_value}"

    def _add_message(self, role, content, mode='reasoning'):
        """
        Adds a message to the agent's message history and manages token limits.

        Args:
            role (str): The role of the message sender ('user', 'assistant').
            content (str): The message content.
            mode (str): The mode of operation ('reasoning' or 'chat').
        """
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logging.error(f"Error getting encoding: {e}")
            raise e

        if mode == 'chat':
            self.chat_history.append({"role": role, "content": content})
            total_tokens = sum(len(encoding.encode(msg['content'])) for msg in self.chat_history)
            while total_tokens > MAX_CHAT_HISTORY_TOKENS and len(self.chat_history) > 1:
                self.chat_history.pop(0)
                total_tokens = sum(len(encoding.encode(msg['content'])) for msg in self.chat_history)
        else:
            self.messages.append({"role": role, "content": content})
            total_tokens = sum(len(encoding.encode(msg['content'])) for msg in self.messages)
            while total_tokens > MAX_TOTAL_TOKENS and len(self.messages) > 1:
                self.messages.pop(0)
                total_tokens = sum(len(encoding.encode(msg['content'])) for msg in self.messages)

    def _handle_reasoning_logic(self, prompt):
        """
        Handles generating a response from the OpenAI API in non-chat mode.

        Args:
            prompt (str): The prompt to send to the API.

        Returns:
            tuple: (assistant_reply, duration)
        """
        shared_system = get_shared_system_message()
        system_message = f"{shared_system}\n\n{self.instructions}"

        messages = [{"role": "user", "content": system_message}]
        messages.extend(self.messages)
        messages.append({"role": "user", "content": prompt})

        start_time = time.time()
        retries = 0
        backoff = 1

        while retries < RETRY_LIMIT:
            try:
                response = client.chat.completions.create(
                    model="o1-2024-12-17",  # Adjust your model name here
                    messages=messages
                )
                end_time = time.time()
                duration = end_time - start_time

                assistant_reply = response.choices[0].message.content.strip()
                self._add_message("assistant", assistant_reply)

                usage = getattr(response, 'usage', None)
                if usage:
                    # Use safe getattr calls to avoid .get
                    prompt_tokens = getattr(usage, 'prompt_tokens', 0)
                    completion_tokens = getattr(usage, 'completion_tokens', 0)
                    total_tokens = getattr(usage, 'total_tokens', 0)

                    prompt_tokens_details = getattr(usage, 'prompt_tokens_details', None)
                    if prompt_tokens_details:
                        cached_tokens = getattr(prompt_tokens_details, 'cached_tokens', 0)
                    else:
                        cached_tokens = 0

                    completion_tokens_details = getattr(usage, 'completion_tokens_details', None)
                    if completion_tokens_details:
                        reasoning_tokens = getattr(completion_tokens_details, 'reasoning_tokens', 0)
                    else:
                        reasoning_tokens = 0

                    print(self.color + f"{self.name} used {cached_tokens} cached tokens out of {prompt_tokens} prompt tokens." + Style.RESET_ALL)
                    print(self.color + f"{self.name} generated {completion_tokens} completion tokens, including {reasoning_tokens} reasoning tokens. Total tokens used: {total_tokens}." + Style.RESET_ALL)
                else:
                    print(self.color + f"{self.name} (No usage details returned.)" + Style.RESET_ALL)

                return assistant_reply, duration
            except Exception as e:
                error_type = type(e).__name__
                logging.error(f"Error in agent '{self.name}' reasoning: {error_type}: {e}")
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
        Handles generating a response from the OpenAI API in chat mode.

        Args:
            user_message (str): The user's message.

        Returns:
            tuple: (assistant_reply, duration)
        """
        shared_system = get_shared_system_message()
        system_message = f"{shared_system}\n\n{self.instructions}"

        messages = [{"role": "user", "content": system_message}]
        messages.extend(self.chat_history)
        messages.append({"role": "user", "content": user_message})

        start_time = time.time()
        retries = 0
        backoff = 1

        while retries < RETRY_LIMIT:
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",  # Use of gpt-4o model for chat interaction
                    messages=messages
                )
                end_time = time.time()
                duration = end_time - start_time

                assistant_reply = response.choices[0].message.content.strip()
                self._add_message("assistant", assistant_reply, mode='chat')

                usage = getattr(response, 'usage', None)
                if usage:
                    prompt_tokens = getattr(usage, 'prompt_tokens', 0)
                    completion_tokens = getattr(usage, 'completion_tokens', 0)
                    total_tokens = getattr(usage, 'total_tokens', 0)

                    prompt_tokens_details = getattr(usage, 'prompt_tokens_details', None)
                    if prompt_tokens_details:
                        cached_tokens = getattr(prompt_tokens_details, 'cached_tokens', 0)
                    else:
                        cached_tokens = 0

                    completion_tokens_details = getattr(usage, 'completion_tokens_details', None)
                    if completion_tokens_details:
                        reasoning_tokens = getattr(completion_tokens_details, 'reasoning_tokens', 0)
                    else:
                        reasoning_tokens = 0

                    print(self.color + f"{self.name} used {cached_tokens} cached tokens out of {prompt_tokens} prompt tokens." + Style.RESET_ALL)
                    print(self.color + f"{self.name} generated {completion_tokens} completion tokens, including {reasoning_tokens} reasoning tokens. Total tokens used: {total_tokens}." + Style.RESET_ALL)
                else:
                    print(self.color + f"{self.name} (No usage details returned.)" + Style.RESET_ALL)

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

    # =========================================================================
    # Public Actions
    # =========================================================================

    def discuss(self, prompt):
        """
        Initiates a discussion based on the given prompt.

        Args:
            prompt (str): The discussion prompt.

        Returns:
            tuple: (response, duration)
        """
        return self._handle_reasoning_logic(prompt)

    def verify(self, data):
        """
        Verifies the accuracy of the provided data.

        Args:
            data (str): The data to verify.

        Returns:
            tuple: (verification_result, duration)
        """
        verification_prompt = f"Verify the accuracy of the following information:\n\n{data}"
        return self._handle_reasoning_logic(verification_prompt)

    def refine(self, data, more_time=False, iterations=2):
        """
        Refines the provided data to improve its accuracy and completeness.

        Args:
            data (str): The data to refine.
            more_time (bool): Whether to allow more time for refinement.
            iterations (int): Number of refinement iterations.

        Returns:
            tuple: (refined_response, total_duration)
        """
        refinement_prompt = f"Please refine the following response to improve its accuracy and completeness:\n\n{data}"
        if more_time:
            refinement_prompt += "\nTake additional time to improve the response thoroughly."

        total_duration = 0
        refined_response = data
        for _ in range(iterations):
            refined_response, duration = self._handle_reasoning_logic(refinement_prompt)
            total_duration += duration
            # For the next iteration, feed the previously refined response
            refinement_prompt = f"Please further refine the following response:\n\n{refined_response}"

        return refined_response, total_duration

    def critique(self, other_agent_response):
        """
        Critiques another agent's response for accuracy and completeness.

        Args:
            other_agent_response (str): The response to critique.

        Returns:
            tuple: (critique_result, duration)
        """
        critique_prompt = f"Critique the following response for accuracy and completeness:\n\n{other_agent_response}"
        return self._handle_reasoning_logic(critique_prompt)

    # =========================================================================
    # Minimal "Agent-to-Agent" Helper
    # =========================================================================

    def ask_other_agent(self, other_agent, question):
        """
        Allows one agent to query another agent for assistance.

        Args:
            other_agent (Agent): The agent to ask the question.
            question (str): The question to ask.

        Returns:
            str: The other agent's response.
        """
        print(f"\n{self.color}{self.name}{Style.RESET_ALL} asks {other_agent.color}{other_agent.name}{Style.RESET_ALL}: {question}")
        response, _ = other_agent.discuss(question)
        return response

# =============================================================================
# Agent Initialization
# =============================================================================

def initialize_agents():
    """
    Initializes agents based on the configuration from 'agents.json'.
    If no configuration is found, default agents are used.

    Returns:
        list: A list of initialized Agent instances.
    """
    agents_data = load_agents_config()
    agents = []
    agent_data_dict = {}

    if not agents_data:
        print(Fore.YELLOW + "No agents found in the configuration. Using default agents." + Style.RESET_ALL)
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
        agent_colors = {
            "Agent 47":     Fore.MAGENTA,
            "Agent 74":     Fore.CYAN,
            "Swarm Agent":  Fore.LIGHTGREEN_EX,
        }
        for agent_data in agents_data:
            name = agent_data.get('name', 'Unnamed Agent')
            color = agent_colors.get(name, Fore.WHITE)
            print(color + f"- {name}" + Style.RESET_ALL)

            agent = Agent(color, **agent_data)
            agents.append(agent)
            agent_data_dict[name] = agent_data

        # Inform agents about the other agents
        for agent in agents:
            other_agents_info = ""
            for other_agent in agents:
                if other_agent.name != agent.name:
                    info = f"Name: {other_agent.name}"
                    other_agent_data = agent_data_dict[other_agent.name]
                    system_purpose = other_agent_data.get('system_purpose', '')
                    info += f"\nSystem Purpose: {system_purpose}"
                    other_attributes = {
                        k: v
                        for k, v in other_agent_data.items()
                        if k not in ['name', 'system_purpose']
                    }
                    for attr_name, attr_value in other_attributes.items():
                        if isinstance(attr_value, dict):
                            details = "\n".join(
                                f"{ak.replace('_', ' ').title()}: {av}"
                                for ak, av in attr_value.items()
                            )
                            info += f"\n{attr_name.replace('_',' ').title()}:\n{details}"
                        else:
                            info += f"\n{attr_name.replace('_',' ').title()}: {attr_value}"
                    other_agents_info += f"\n\n{info}"
            agent.instructions += f"\n\nYou are aware of the following other agents:\n{other_agents_info.strip()}"

    return agents

# =============================================================================
# Blending Logic
# =============================================================================

def blend_responses(agent_responses, user_prompt):
    """
    Combines multiple agent responses into a single, optimal response.

    Args:
        agent_responses (list of tuples): List containing (agent_name, response) pairs.
        user_prompt (str): The original user prompt.

    Returns:
        str: The blended optimal response.
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
            model="o1-2024-12-17",  # Adjust your model name here
            messages=[{"role": "user", "content": combined_prompt}]
        )

        blended_reply = response.choices[0].message.content.strip()

        usage = getattr(response, 'usage', None)
        if usage:
            prompt_tokens = getattr(usage, 'prompt_tokens', 0)
            completion_tokens = getattr(usage, 'completion_tokens', 0)
            total_tokens = getattr(usage, 'total_tokens', 0)

            prompt_tokens_details = getattr(usage, 'prompt_tokens_details', None)
            if prompt_tokens_details:
                cached_tokens = getattr(prompt_tokens_details, 'cached_tokens', 0)
            else:
                cached_tokens = 0

            completion_tokens_details = getattr(usage, 'completion_tokens_details', None)
            if completion_tokens_details:
                reasoning_tokens = getattr(completion_tokens_details, 'reasoning_tokens', 0)
            else:
                reasoning_tokens = 0

            print(Fore.GREEN + f"Blending used {cached_tokens} cached tokens out of {prompt_tokens} prompt tokens." + Style.RESET_ALL)
            print(Fore.GREEN + f"Blending generated {completion_tokens} completion tokens, including {reasoning_tokens} reasoning tokens. Total tokens used: {total_tokens}." + Style.RESET_ALL)
        else:
            print(Fore.GREEN + "(No usage details returned for blending.)" + Style.RESET_ALL)

        return blended_reply
    except Exception as e:
        logging.error(f"Error in blending responses: {e}")
        return "An error occurred while attempting to blend responses."

# =============================================================================
# Console Utilities
# =============================================================================

def print_divider(char="═", length=100, color=Fore.YELLOW):
    """
    Prints a divider line of specified character, length, and color.
    """
    print(color + (char * length) + Style.RESET_ALL)

def print_header(title, color=Fore.YELLOW):
    """
    Prints a formatted header with a box around the title text.
    """
    border = "═" * 58
    print(color + f"╔{border}╗")
    print(color + f"║{title.center(58)}║")
    print(color + f"╚{border}╝" + Style.RESET_ALL)

def process_agent_action(agent, action, *args, **kwargs):
    """
    Processes an action (discuss, verify, refine, critique) for a given agent.

    Args:
        agent (Agent): The agent performing the action.
        action (str): The action to perform.
        *args: Positional arguments for the action method.
        **kwargs: Keyword arguments for the action method.

    Returns:
        tuple: (result_text, duration)
    """
    action_method = getattr(agent, action, None)
    if not action_method:
        logging.error(f"Action '{action}' not found for agent '{agent.name}'.")
        return "Invalid action.", 0

    action_description = agent.ACTION_DESCRIPTIONS.get(action, "performing an action")

    print_divider()
    print(Fore.YELLOW + f"System Message: {agent.color}{agent.name} is {action_description}..." + Style.RESET_ALL)

    try:
        result, duration = action_method(*args, **kwargs)
        if result:
            print(agent.color + f"\n=== {agent.name} {action.capitalize()} Output ===" + Style.RESET_ALL)
            print(agent.color + result + Style.RESET_ALL)
        print(agent.color + f"{agent.name}'s action completed in {duration:.2f} seconds." + Style.RESET_ALL)
        return result, duration
    except Exception as e:
        logging.error(f"Error during {action} action for {agent.name}: {e}")
        return "An error occurred.", 0

def handle_special_commands(user_input, agents):
    """
    Handles special user commands: 'exit', 'history', 'clear'.

    Args:
        user_input (str): The user's input command.
        agents (list): List of Agent instances.

    Returns:
        bool: True if a special command was handled, False otherwise.
    """
    cmd = user_input.strip().lower()
    if cmd == 'exit':
        print(Fore.YELLOW + "Goodbye!" + Style.RESET_ALL)
        sys.exit(0)
    elif cmd == 'history':
        print(Fore.YELLOW + "\nConversation History:" + Style.RESET_ALL)
        for agent in agents:
            print(agent.color + f"\n{agent.name} Conversation:" + Style.RESET_ALL)
            for msg in agent.messages:
                print(f"{msg['role'].capitalize()}: {msg['content']}")
        return True
    elif cmd == 'clear':
        for agent in agents:
            agent.messages.clear()
            agent.chat_history.clear()
        print(Fore.YELLOW + "Conversation history cleared." + Style.RESET_ALL)
        return True
    return False

# =============================================================================
# Chat Logic (with local memory retrieval)
# =============================================================================

def chat_with_agents(agents):
    """
    Facilitates chat interactions between the user and selected agents.

    Args:
        agents (list): List of Agent instances.
    """
    while True:
        print(Fore.YELLOW + "Available agents to chat with:" + Style.RESET_ALL)
        for idx, agent in enumerate(agents, 1):
            print(f"{idx}. {agent.color}{agent.name}{Style.RESET_ALL}")

        print(Fore.YELLOW + "Enter the number of the agent to chat with, or 'menu' to return, or 'exit' to exit program: " + Style.RESET_ALL, end='')
        selection = input().strip().lower()

        if selection == 'menu':
            return
        if selection == 'exit':
            print(Fore.YELLOW + "Goodbye!" + Style.RESET_ALL)
            sys.exit(0)

        if selection.isdigit() and 1 <= int(selection) <= len(agents):
            selected_agent = agents[int(selection) - 1]
        else:
            print(Fore.YELLOW + f"Invalid selection. Please enter a number between 1 and {len(agents)}, 'menu', or 'exit'." + Style.RESET_ALL)
            continue

        print(Fore.YELLOW + f"Starting chat with {selected_agent.color}{selected_agent.name}{Style.RESET_ALL}.")
        print(Fore.YELLOW + "Type 'menu' to return to agent selection or 'exit' to end the program." + Style.RESET_ALL)

        while True:
            print(Fore.YELLOW + "\nYou (type 'menu' or 'exit'): " + Style.RESET_ALL, end='')
            user_message = input().strip()

            if user_message.lower() == 'menu':
                print(Fore.YELLOW + "Returning to agent selection menu..." + Style.RESET_ALL)
                break
            if user_message.lower() == 'exit':
                print(Fore.YELLOW + "Goodbye!" + Style.RESET_ALL)
                sys.exit(0)

            # Retrieve local context from reasoning_history.json
            local_context = get_local_context_for_prompt(user_message, is_swarm=False)
            user_message_with_context = f"{user_message}\n\n{local_context}" if local_context else user_message

            # Handle special commands
            if handle_special_commands(user_message, [selected_agent]):
                continue

            assistant_reply, duration = selected_agent._handle_chat_interaction(user_message_with_context)
            print(selected_agent.color + f"{selected_agent.name}: {assistant_reply}" + Style.RESET_ALL)

# =============================================================================
# Reasoning Logic (with local memory + agent-to-agent help)
# =============================================================================

def reasoning_logic(agents):
    """
    Handles the reasoning workflow, which includes discussing, verifying, critiquing,
    refining, and blending responses from multiple agents.

    Args:
        agents (list): A list of Agent instances.
    """
    while True:
        print(Fore.YELLOW + "Please enter your prompt (or type 'menu' to return, 'exit' to quit): " + Style.RESET_ALL, end='')
        user_prompt = input().strip()

        if user_prompt.lower() == 'menu':
            print(Fore.YELLOW + "Returning to main menu." + Style.RESET_ALL)
            break
        if user_prompt.lower() == 'exit':
            print(Fore.YELLOW + "Goodbye!" + Style.RESET_ALL)
            sys.exit(0)

        # Handle special commands
        if handle_special_commands(user_prompt, agents):
            continue

        if len(user_prompt) <= 4:
            print(Fore.YELLOW + "Your prompt must be more than 4 characters. Please try again." + Style.RESET_ALL)
            continue

        # Retrieve local memory relevant to user_prompt
        local_context = get_local_context_for_prompt(user_prompt, is_swarm=False, max_records=3)

        # Incorporate context into the user prompt if available
        extended_prompt = f"{user_prompt}\n\n--- Additional local memory context ---\n{local_context}" if local_context else user_prompt

        # ============ Step 1: Discuss ============
        print_header("Reasoning Step 1: Discussing the Prompt")
        opinions = {}
        durations = {}
        for agent in agents:
            # Example: Agent can ask another agent for help based on specific keyword
            if "ask-other" in extended_prompt.lower() and len(agents) > 1:
                helper_agent = agents[(agents.index(agent) + 1) % len(agents)]
                help_response = agent.ask_other_agent(helper_agent, "Do you have any insights on this topic?")
                full_opinion_prompt = f"{extended_prompt}\nHelper agent says: {help_response}"
            else:
                full_opinion_prompt = extended_prompt

            opinion, duration = process_agent_action(agent, 'discuss', full_opinion_prompt)
            opinions[agent.name] = opinion
            durations[agent.name] = duration

        total_discussion_time = sum(durations.values())
        print_divider()
        print(Fore.YELLOW + f"Total discussion time: {total_discussion_time:.2f} seconds." + Style.RESET_ALL)

        # ============ Step 2: Verify ============
        print_header("Reasoning Step 2: Verifying Responses")
        verified_opinions = {}
        verify_durations = {}

        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(process_agent_action, agent, 'verify', opinions[agent.name]): agent for agent in agents}
            for future in futures:
                agent = futures[future]
                verified_opinion, duration = future.result()
                verified_opinions[agent.name] = verified_opinion
                verify_durations[agent.name] = duration

        total_verification_time = sum(verify_durations.values())
        print_divider()
        print(Fore.YELLOW + f"Total verification time: {total_verification_time:.2f} seconds." + Style.RESET_ALL)

        # ============ Step 3: Critique ============
        print_header("Reasoning Step 3: Critiquing Responses")
        critiques = {}
        critique_durations = {}
        num_agents = len(agents)
        for i, agent in enumerate(agents):
            other_agent = agents[(i + 1) % num_agents]
            critique, duration = process_agent_action(agent, 'critique', verified_opinions[other_agent.name])
            critiques[agent.name] = critique
            critique_durations[agent.name] = duration

        total_critique_time = sum(critique_durations.values())
        print_divider()
        print(Fore.YELLOW + f"Total critique time: {total_critique_time:.2f} seconds." + Style.RESET_ALL)

        # ============ Step 4: Refine ============
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

        # ============ Step 5: Blend ============
        print_header("Reasoning Step 5: Blending Responses")
        agent_responses = [(agent.name, refined_opinions[agent.name]) for agent in agents]
        start_blend_time = time.time()
        optimal_response = blend_responses(agent_responses, user_prompt)
        end_blend_time = time.time()
        blend_duration = end_blend_time - start_blend_time

        print_divider()
        print_header("Optimal Response")
        print(Fore.GREEN + optimal_response + Style.RESET_ALL)
        print_divider()
        print(Fore.YELLOW + f"Response generated in {blend_duration:.2f} seconds." + Style.RESET_ALL)

        # ======= Feedback Loop ========
        refine_count = 0
        more_time = False
        user_feedback = None
        while refine_count < MAX_REFINEMENT_ATTEMPTS:
            print(Fore.YELLOW + "\nWas this response helpful and accurate? (yes/no, 'menu' to main menu, 'exit' to quit): " + Style.RESET_ALL, end='')
            user_feedback = input().strip().lower()

            if user_feedback == 'menu':
                print(Fore.YELLOW + "Returning to main menu." + Style.RESET_ALL)
                save_reasoning_session(user_prompt, optimal_response, user_feedback, context_retained=False)
                return
            if user_feedback == 'exit':
                print(Fore.YELLOW + "Goodbye!" + Style.RESET_ALL)
                save_reasoning_session(user_prompt, optimal_response, user_feedback, context_retained=False)
                sys.exit(0)

            if user_feedback == 'yes':
                print(Fore.YELLOW + "Thank you for your feedback!" + Style.RESET_ALL)
                break
            elif user_feedback != 'no':
                print(Fore.YELLOW + "Please answer 'yes', 'no', 'menu' or 'exit'." + Style.RESET_ALL)
                continue

            # If user says no, attempt to refine again
            refine_count += 1
            if refine_count >= 2:
                print(Fore.YELLOW + "Would you like the agents to take more time refining the response? (yes/no): " + Style.RESET_ALL, end='')
                more_time_input = input().strip().lower()
                more_time = (more_time_input == 'yes')

            print(Fore.YELLOW + "We're sorry to hear that. Let's try to improve the response." + Style.RESET_ALL)

            for agent in agents:
                refined_opinion, duration = process_agent_action(
                    agent, 'refine',
                    refined_opinions[agent.name],
                    more_time=more_time
                )
                refined_opinions[agent.name] = refined_opinion
                refine_durations[agent.name] += duration

            total_refinement_time = sum(refine_durations.values())
            print_divider()
            print(Fore.YELLOW + f"Total refinement time: {total_refinement_time:.2f} seconds." + Style.RESET_ALL)

            # Re-blend the refined responses
            print_divider()
            print_header("Blending Refined Responses")
            agent_responses = [(agent.name, refined_opinions[agent.name]) for agent in agents]
            start_blend_time = time.time()
            optimal_response = blend_responses(agent_responses, user_prompt)
            end_blend_time = time.time()
            blend_duration = end_blend_time - start_blend_time

            print_divider()
            print_header("New Optimal Response")
            print(Fore.GREEN + optimal_response + Style.RESET_ALL)
            print_divider()
            print(Fore.YELLOW + f"Response generated in {blend_duration:.2f} seconds." + Style.RESET_ALL)

        else:
            print(Fore.YELLOW + "Maximum refinement attempts reached." + Style.RESET_ALL)

        if not user_feedback:
            user_feedback = "no"

        print(Fore.YELLOW + "Would you like to retain this conversation context for the next prompt? (yes/no): " + Style.RESET_ALL, end='')
        retain_context_input = input().strip().lower()
        context_retained = (retain_context_input == 'yes')
        if not context_retained:
            for agent in agents:
                agent.messages.clear()
            print(Fore.YELLOW + "Conversation context has been reset." + Style.RESET_ALL)
        else:
            print(Fore.YELLOW + "Conversation context has been retained for the next prompt." + Style.RESET_ALL)

        # Save final session
        save_reasoning_session(user_prompt, optimal_response, user_feedback, context_retained)

# =============================================================================
# Save Reasoning Session
# =============================================================================

def save_reasoning_session(user_prompt, final_response, user_feedback, context_retained):
    """
    Saves the reasoning session details to the history file.

    Args:
        user_prompt (str): The user's prompt.
        final_response (str): The final response generated.
        user_feedback (str): The user's feedback ('yes'/'no').
        context_retained (bool): Whether the context is retained.
    """
    record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "user_prompt": user_prompt,
        "final_response": final_response,
        "user_feedback": user_feedback,
        "context_retained": context_retained
    }
    append_reasoning_history(record)
    logging.info("Reasoning session appended to reasoning_history.json.")

# =============================================================================
# Swarm Reasoning Feedback (with local memory as well)
# =============================================================================

def swarm_reasoning_feedback(user_prompt, final_response):
    """
    Handles user feedback for swarm-based reasoning and saves the session.

    Args:
        user_prompt (str): The user's prompt.
        final_response (str): The response generated by the swarm.
    """
    user_feedback = None
    while True:
        print(Fore.YELLOW + "\nWas this response helpful and accurate? (yes/no, 'menu' to main menu, 'exit' to quit): " + Style.RESET_ALL, end='')
        user_feedback = input().strip().lower()

        if user_feedback == 'menu':
            print(Fore.YELLOW + "Returning to main menu." + Style.RESET_ALL)
            save_swarm_session(user_prompt, final_response, user_feedback, context_retained=False)
            return
        elif user_feedback == 'exit':
            print(Fore.YELLOW + "Goodbye!" + Style.RESET_ALL)
            save_swarm_session(user_prompt, final_response, user_feedback, context_retained=False)
            sys.exit(0)
        elif user_feedback == 'yes':
            print(Fore.YELLOW + "Thank you for your feedback!" + Style.RESET_ALL)
            break
        elif user_feedback != 'no':
            print(Fore.YELLOW + "Please answer 'yes', 'no', 'menu' or 'exit'." + Style.RESET_ALL)
            continue
        else:
            print(Fore.YELLOW + "Sorry to hear that. (Swarm refining is not yet implemented.)" + Style.RESET_ALL)
            break

    print(Fore.YELLOW + "Would you like to retain this conversation context for the next prompt? (yes/no): " + Style.RESET_ALL, end='')
    retain_context_input = input().strip().lower()
    context_retained = (retain_context_input == 'yes')
    if not context_retained:
        print(Fore.YELLOW + "Swarm conversation context has been reset." + Style.RESET_ALL)
    else:
        print(Fore.YELLOW + "Swarm conversation context has been retained for the next prompt." + Style.RESET_ALL)

    # Save swarm session
    save_swarm_session(user_prompt, final_response, user_feedback, context_retained)

def save_swarm_session(user_prompt, final_response, user_feedback, context_retained):
    """
    Saves the swarm-based reasoning session details to the history file.

    Args:
        user_prompt (str): The user's prompt.
        final_response (str): The response generated by the swarm.
        user_feedback (str): The user's feedback ('yes'/'no').
        context_retained (bool): Whether the context is retained.
    """
    record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "user_prompt": user_prompt,
        "final_response": final_response,
        "user_feedback": user_feedback,
        "context_retained": context_retained
    }
    append_swarm_history(record)
    logging.info("Swarm-based session appended to swarm_reasoning_history.json.")

# =============================================================================
# Main Menu
# =============================================================================

def main_menu():
    """
    Displays the main menu and handles user navigation between different modes:
      1) Chat with an agent (single-agent chat)
      2) Use reasoning logic (multi-step discussion, verify, critique, refine, blend)
      3) Swarm-based reasoning (using the swarm_middle_agent_interface)
      4) Exit the program

    The user remains in each mode until they explicitly type 'menu' (to go back to this menu)
    or 'exit' (to end the program).
    """
    agents = initialize_agents()
    current_mode = None

    while True:
        # Only display the main menu if we're not in any current_mode
        if current_mode is None:
            print_divider()
            print_header("Multi-Agent Reasoning Chatbot")
            print(Fore.YELLOW + "Please select an option:" + Style.RESET_ALL)
            print("1. Chat with an agent")
            print("2. Use reasoning logic")
            print("3. Use Swarm-based reasoning")
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
                sys.exit(0)

        # ----------------------------------------------------------------------
        # OPTION 1: Chat with an agent
        # ----------------------------------------------------------------------
        if current_mode == 'chat':
            # This function already handles a loop allowing the user to keep
            # chatting with the selected agent(s) until 'menu' or 'exit'.
            chat_with_agents(agents)
            current_mode = None

        # ----------------------------------------------------------------------
        # OPTION 2: Reasoning logic
        # ----------------------------------------------------------------------
        elif current_mode == 'reasoning':
            # This function runs the multi-step reasoning process in a loop.
            reasoning_logic(agents)
            current_mode = None

        # ----------------------------------------------------------------------
        # OPTION 3: Swarm-based reasoning
        # ----------------------------------------------------------------------
        elif current_mode == 'swarm':
            # We stay in swarm-based mode until user selects 'menu' or 'exit'.
            while True:
                print(Fore.YELLOW + 
                      "Enter your reasoning prompt for Swarm (or type 'menu' to return, 'exit' to quit): " +
                      Style.RESET_ALL, end='')
                user_prompt = input().strip()
                lower_prompt = user_prompt.lower()

                if lower_prompt == 'exit':
                    print(Fore.YELLOW + "Goodbye!" + Style.RESET_ALL)
                    sys.exit(0)
                elif lower_prompt == 'menu':
                    current_mode = None
                    break  # Return to the main menu

                # Retrieve local swarm memory for context
                swarm_context = get_local_context_for_prompt(
                    user_prompt,
                    is_swarm=True,
                    max_records=3
                )

                user_prompt_w_context = (
                    f"{user_prompt}\n\n--- Additional local swarm memory context ---\n{swarm_context}"
                    if swarm_context else user_prompt
                )

                # Hand off the prompt to the swarm middle agent
                final_swarm_response = swarm_middle_agent_interface(user_prompt_w_context)
                final_swarm_response = final_swarm_response or "No final swarm response captured."

                # Provide user feedback loop for the swarm response
                swarm_reasoning_feedback(user_prompt, final_swarm_response)

# =============================================================================
# Script Entry Point
# =============================================================================
if __name__ == "__main__":
    main_menu()
