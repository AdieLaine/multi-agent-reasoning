# Imports
import os
import time
import logging
import json
from colorama import Fore, Style, init
from swarm import Agent, Swarm  # Ensure you have the 'swarm' package installed or adjust as needed

# Initialize colorama
init(autoreset=True)

# Custom Formatter for Logging
class ColoredFormatter(logging.Formatter):
    # Colors for log levels
    LEVEL_COLORS = {
        logging.DEBUG: Fore.LIGHTYELLOW_EX,  # Changed to LIGHTYELLOW_EX for orange-like color
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
file_handler = logging.FileHandler("swarm_middle_agent.log")
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s %(levelname)s:%(message)s')
file_handler.setFormatter(file_formatter)

# Configure the root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler],
)

# Initialize the Swarm client
client = Swarm()

# Define colors for agents
AGENT_COLORS = {
    "Agent 47": Fore.MAGENTA,
    "Agent 74": Fore.CYAN,
    "Swarm Agent": Fore.LIGHTGREEN_EX,  # Changed to LIGHTGREEN_EX for better distinction
}

# Path to agents configuration file
AGENTS_CONFIG_FILE = 'agents.json'

# Function to load agents configuration
def load_agents_config():
    try:
        with open(AGENTS_CONFIG_FILE, 'r', encoding='utf-8') as f:
            agents_data = json.load(f)
        logging.info(f"Successfully loaded agents configuration from '{AGENTS_CONFIG_FILE}'.")
        return agents_data.get('agents', [])
    except FileNotFoundError:
        logging.error(f"Agents configuration file '{AGENTS_CONFIG_FILE}' not found.")
        return []
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing '{AGENTS_CONFIG_FILE}': {e}")
        return []

# Utility functions for formatting
def print_divider(char="═", length=100, color=Fore.YELLOW):
    print(color + char * length + Style.RESET_ALL)

def print_header(title, color=Fore.YELLOW):
    border = "═" * 58
    print(color + f"\n╔{border}╗")
    print(color + f"║{title.center(58)}║")
    print(color + f"╚{border}╝" + Style.RESET_ALL)

# Initialize Swarm Agents
def initialize_swarm_agents():
    """
    Initializes Swarm agents from the configuration file.
    """
    agents_data = load_agents_config()
    agents = []
    agent_data_dict = {}  # Map agent names to their data

    if not agents_data:
        logging.error("No agents found in the configuration. Please check your agents.json file.")
        exit(1)
    else:
        for agent_data in agents_data:
            name = agent_data.get('name', 'Unnamed Agent')
            system_purpose = agent_data.get('system_purpose', '')
            # Build the agent's instructions by incorporating traits
            additional_attributes = {k: v for k, v in agent_data.items() if k not in ['name', 'system_purpose']}
            # Build the full instructions
            full_instructions = system_purpose
            for attr_name, attr_value in additional_attributes.items():
                if isinstance(attr_value, dict):
                    details = "\n".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in attr_value.items())
                    full_instructions += f"\n\n{attr_name.replace('_', ' ').title()}:\n{details}"
                else:
                    full_instructions += f"\n\n{attr_name.replace('_', ' ').title()}: {attr_value}"
            # Initialize the agent with the combined instructions
            agent = Agent(
                name=name,
                instructions=full_instructions
            )
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

# Function to handle Swarm chat interactions
def swarm_chat_interface(conversation_history):
    """
    Handles chat interactions with the Swarm agent.
    :param conversation_history: List of messages in the conversation.
    :return: Swarm agent's response.
    """
    # Load Swarm agent's configuration
    agents = initialize_swarm_agents()
    swarm_agent = None
    for agent in agents:
        if agent.name == "Swarm Agent":
            swarm_agent = agent
            break
    if not swarm_agent:
        logging.error("Swarm Agent not found in the configuration.")
        return "Swarm Agent configuration is missing."

    # Prepare the conversation with the system message
    messages = [{"role": "system", "content": swarm_agent.instructions}]
    messages.extend(conversation_history)

    # Start timing
    start_time = time.time()

    try:
        # Swarm agent processes the conversation history
        response = client.run(
            agent=swarm_agent,
            messages=messages
        )

        # End timing
        end_time = time.time()
        duration = end_time - start_time

        # Extract and return reply
        swarm_reply = response.messages[-1]['content'].strip()

        # Display timing information
        print(Fore.YELLOW + f"Swarm response generated in {duration:.2f} seconds." + Style.RESET_ALL)

        return swarm_reply

    except Exception as e:
        logging.error(f"Error in Swarm chat interaction: {e}")
        return "An error occurred while generating a response."

# Function to run Swarm reasoning with multiple stages
def run_swarm_reasoning(user_prompt):
    """
    Uses Swarm agents to collaborate and respond to a user prompt following multiple reasoning stages.
    """
    # Initialize agents
    agents = initialize_swarm_agents()
    num_agents = len(agents)
    opinions = {}
    verified_opinions = {}
    critiques = {}
    refined_opinions = {}

    print(Fore.YELLOW + "\nRunning Swarm-based reasoning...\n" + Style.RESET_ALL)

    # ------------------ Reasoning Step 1: Agents Discuss the Prompt ------------------
    print_header("Reasoning Step 1: Discussing the Prompt")
    for agent in agents:
        response = client.run(
            agent=agent,
            messages=[{"role": "user", "content": user_prompt}]
        )
        opinion = response.messages[-1]['content']
        opinions[agent.name] = opinion
        print(AGENT_COLORS.get(agent.name, Fore.WHITE) + f"{agent.name} response: {opinion}" + Style.RESET_ALL)

    # ------------------ Reasoning Step 2: Agents Verify Their Responses ------------------
    print_header("Reasoning Step 2: Verifying Responses")
    for agent in agents:
        verify_prompt = f"Please verify the accuracy of your previous response:\n\n{opinions[agent.name]}"
        response = client.run(
            agent=agent,
            messages=[{"role": "user", "content": verify_prompt}]
        )
        verified_opinion = response.messages[-1]['content']
        verified_opinions[agent.name] = verified_opinion
        print(AGENT_COLORS.get(agent.name, Fore.WHITE) + f"{agent.name} verified response: {verified_opinion}" + Style.RESET_ALL)

    # ------------------ Reasoning Step 3: Agents Critique Each Other's Responses ------------------
    print_header("Reasoning Step 3: Critiquing Responses")
    for i, agent in enumerate(agents):
        other_agent = agents[(i + 1) % num_agents]  # Get the next agent
        critique_prompt = f"Please critique {other_agent.name}'s response for depth and accuracy:\n\n{verified_opinions[other_agent.name]}"
        response = client.run(
            agent=agent,
            messages=[{"role": "user", "content": critique_prompt}]
        )
        critique = response.messages[-1]['content']
        critiques[agent.name] = critique
        print(AGENT_COLORS.get(agent.name, Fore.WHITE) + f"{agent.name} critique on {other_agent.name}'s response: {critique}" + Style.RESET_ALL)

    # ------------------ Reasoning Step 4: Agents Refine Their Responses ------------------
    print_header("Reasoning Step 4: Refining Responses")
    for i, agent in enumerate(agents):
        other_agent = agents[(i + 1) % num_agents]  # Get the next agent
        refine_prompt = f"Please refine your response based on {other_agent.name}'s critique:\n\nYour Original Response:\n{opinions[agent.name]}\n\n{other_agent.name}'s Critique:\n{critiques[other_agent.name]}"
        response = client.run(
            agent=agent,
            messages=[{"role": "user", "content": refine_prompt}]
        )
        refined_opinion = response.messages[-1]['content']
        refined_opinions[agent.name] = refined_opinion
        print(AGENT_COLORS.get(agent.name, Fore.WHITE) + f"{agent.name} refined response: {refined_opinion}" + Style.RESET_ALL)

    # ------------------ Reasoning Step 5: Blending Refined Responses ------------------
    print_header("Reasoning Step 5: Blending Responses")
    agent_responses = [(agent.name, refined_opinions[agent.name]) for agent in agents]
    blended_response = blend_responses(agent_responses, user_prompt)
    print(Fore.GREEN + f"\nFinal Blended Response:\n{blended_response}" + Style.RESET_ALL)

    print(Fore.GREEN + "\nSwarm-based reasoning completed.\n" + Style.RESET_ALL)

# Function to blend responses
def blend_responses(agent_responses, user_prompt):
    """
    Combines multiple agent responses into a single, optimal response.
    """
    combined_prompt = (
        "Please combine the following responses into a single, optimal answer to the question.\n"
        f"Question: '{user_prompt}'\n"
        "Responses:\n"
        + "\n\n".join(f"Response from {agent_name}:\n{response}" for agent_name, response in agent_responses)
        + "\n\nProvide a concise and accurate combined response."
    )

    try:
        # Initialize the Blender agent with awareness of other agents
        blender_agent = Agent(
            name="Swarm Agent",
            instructions="You are a collaborative AI assistant composed of multiple expert agents."
        )
        # Include other agents' info in the system message
        other_agents_info = ""
        for agent_name, _ in agent_responses:
            if agent_name != "Swarm Agent":
                other_agents_info += f"{agent_name}, "
        if other_agents_info:
            other_agents_info = other_agents_info.strip().strip(",")
            blender_agent.instructions += f" You are aware of the following agents: {other_agents_info}."

        # Run the blending process
        response = client.run(
            agent=blender_agent,
            messages=[{"role": "user", "content": combined_prompt}]
        )
        blended_reply = response.messages[-1]['content']
        return blended_reply
    except Exception as e:
        logging.error(f"Error in blending responses: {e}")
        return "An error occurred while attempting to blend responses."

# Interface functions to be used by your original script
def swarm_middle_agent_interface(user_prompt):
    """
    Interface function to be used by your original script to trigger Swarm-based reasoning.
    """
    try:
        start_time = time.time()
        run_swarm_reasoning(user_prompt)
        end_time = time.time()
        print(Fore.YELLOW + f"Swarm reasoning completed in {end_time - start_time:.2f} seconds." + Style.RESET_ALL)
    except Exception as e:
        logging.error(f"Error in Swarm reasoning: {e}")

def swarm_chat_interface(conversation_history):
    """
    Handles chat interactions with the Swarm agent.
    :param conversation_history: List of messages in the conversation.
    :return: Swarm agent's response.
    """
    # Reuse the function defined earlier
    # Load Swarm agent's configuration
    agents = initialize_swarm_agents()
    swarm_agent = None
    for agent in agents:
        if agent.name == "Swarm Agent":
            swarm_agent = agent
            break
    if not swarm_agent:
        logging.error("Swarm Agent not found in the configuration.")
        return "Swarm Agent configuration is missing."

    # Prepare the conversation with the system message
    messages = [{"role": "system", "content": swarm_agent.instructions}]
    messages.extend(conversation_history)

    # Start timing
    start_time = time.time()

    try:
        # Swarm agent processes the conversation history
        response = client.run(
            agent=swarm_agent,
            messages=messages
        )

        # End timing
        end_time = time.time()
        duration = end_time - start_time

        # Extract and return reply
        swarm_reply = response.messages[-1]['content'].strip()

        # Display timing information
        print(Fore.YELLOW + f"Swarm response generated in {duration:.2f} seconds." + Style.RESET_ALL)

        return swarm_reply

    except Exception as e:
        logging.error(f"Error in Swarm chat interaction: {e}")
        return "An error occurred while generating a response."

if __name__ == "__main__":
    # Example test run (if you run this script directly)
    test_prompt = "What is love and how does it affect human behavior?"
    swarm_middle_agent_interface(test_prompt)