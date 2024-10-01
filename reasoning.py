# Imports
import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from colorama import init, Fore, Style
import tiktoken  # For accurate token counting
from openai import OpenAI

# Initialize colorama
init(autoreset=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s',
    handlers=[
        logging.FileHandler("assistant.log"),
        logging.StreamHandler()
    ]
)

# Initialize the OpenAI client
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    logging.error("OpenAI API key not found in environment variable 'OPENAI_API_KEY'. Please set it and rerun the script.")
    exit(1)

client = OpenAI(api_key=api_key)

# Constants
MAX_TOTAL_TOKENS = 2048   # Adjust based on OpenAI's token limit per request
RETRY_LIMIT = 3
RETRY_BACKOFF_FACTOR = 2  # Exponential backoff factor
MAX_REFINEMENT_ATTEMPTS = 3

class Agent:
    """
    Represents an agent that can perform various reasoning actions.
    """
    ACTION_DESCRIPTIONS = {
        'discuss': "formulating a response",
        'verify': "verifying data",
        'refine': "refining the response",
        'critique': "critiquing the other agent's response"
    }

    def __init__(self, name, color):
        """
        Initialize an agent with a name and color for display purposes.
        """
        self.name = name
        self.color = color
        self.messages = []  # Stores the conversation context
        self.lock = None  # Placeholder for potential thread safety mechanisms

    def _add_message(self, role, content):
        """
        Adds a message to the agent's message history and ensures token limit is not exceeded.

        Args:
            role (str): The role of the message sender ('user' or 'assistant').
            content (str): The content of the message.
        """
        self.messages.append({"role": role, "content": content})

        # Enforce a maximum message history length based on token count
        try:
            # Use a known encoding compatible with chat models
            encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logging.error(f"Error getting encoding: {e}")
            # Optionally, you can raise the exception if the encoding is critical
            raise e

        total_tokens = sum(len(encoding.encode(msg['content'])) for msg in self.messages)
        if total_tokens > MAX_TOTAL_TOKENS:
            # Trim messages from the beginning until under the limit
            while total_tokens > MAX_TOTAL_TOKENS and len(self.messages) > 1:
                self.messages.pop(0)
                total_tokens = sum(len(encoding.encode(msg['content'])) for msg in self.messages)

    def _handle_chat_response(self, prompt):
        """
        Handles the chat response by appending the user prompt and getting the response.

        Args:
            prompt (str): The prompt to send to the agent.

        Returns:
            tuple: The assistant's reply and the duration it took to get the response.
        """
        self._add_message("user", prompt)

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
                    messages=self.messages
                )

                # End timing
                end_time = time.time()
                duration = end_time - start_time

                # Extract and return reply
                assistant_reply = response.choices[0].message.content.strip()
                self._add_message("assistant", assistant_reply)

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

def blend_responses(agent_responses, user_prompt):
    """
    Combines multiple agent responses into a single, optimal response.

    Args:
        agent_responses (list): List of agent responses.
        user_prompt (str): The original user prompt.

    Returns:
        str: The blended response.
    """
    combined_prompt = (
        f"Combine the following responses into a single, optimal answer to the question: '{user_prompt}'.\n\n"
        + "\n\n".join(f"Response {idx+1}:\n{response}" for idx, response in enumerate(agent_responses))
        + "\n\nProvide a concise and accurate combined response."
    )

    try:
        response = client.chat.completions.create(
            model="o1-preview-2024-09-12",
            messages=[{"role": "user", "content": combined_prompt}]
        )
        blended_reply = response.choices[0].message.content.strip()
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

    This function handles the execution of a reasoning step (e.g., 'discuss', 'verify', 'critique', 'refine')
    for an agent. It ensures that the action is performed correctly and logs the duration.

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
    print(agent.color + f"{agent.name} is {action_description}..." + Style.RESET_ALL)

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

def handle_special_commands(user_input, agent_a, agent_b):
    """
    Handles special commands input by the user.

    Args:
        user_input (str): The user's input.
        agent_a (Agent): The first agent.
        agent_b (Agent): The second agent.

    Returns:
        bool: True if a special command was handled, False otherwise.
    """
    cmd = user_input.strip().lower()
    if cmd == 'exit':
        print(Fore.YELLOW + "Goodbye!" + Style.RESET_ALL)
        exit(0)
    elif cmd == 'history':
        print(Fore.YELLOW + "\nConversation History:" + Style.RESET_ALL)
        for msg in agent_a.messages:
            print(f"{msg['role'].capitalize()}: {msg['content']}")
        return True  # Indicate that a special command was handled
    elif cmd == 'clear':
        agent_a.messages = []
        agent_b.messages = []
        print(Fore.YELLOW + "Conversation history cleared." + Style.RESET_ALL)
        return True
    return False  # No special command handled

# Main script
if __name__ == "__main__":
    # Initialize agents with their respective colors
    agent_a = Agent("Agent A", Fore.MAGENTA)
    agent_b = Agent("Agent B", Fore.CYAN)  # Changed to CYAN for better distinction

    agents = [agent_a, agent_b]  # List of agents for easy management

    while True:
        # Get user input
        print(Fore.YELLOW + "Please enter your prompt (or type 'exit' to quit): " + Style.RESET_ALL, end='')
        user_prompt = input()

        # Handle special commands
        if handle_special_commands(user_prompt, agent_a, agent_b):
            continue

        # ------------------ Reasoning Step 1: Agents Discuss the Prompt ------------------
        print_header("Reasoning Step 1: Discussing the Prompt")
        opinions = {}
        durations = {}

        # Agents discuss the prompt (can be parallelized if desired)
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
        critiques[agent_a.name], critique_duration_a = process_agent_action(agent_a, 'critique', verified_opinions[agent_b.name])
        critiques[agent_b.name], critique_duration_b = process_agent_action(agent_b, 'critique', verified_opinions[agent_a.name])
        critique_durations[agent_a.name] = critique_duration_a
        critique_durations[agent_b.name] = critique_duration_b

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
        agent_responses = [refined_opinions[agent.name] for agent in agents]
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
            agent_responses = [refined_opinions[agent.name] for agent in agents]
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
        retain_context = ask_retain_context()

        if not retain_context:
            # Clear agents' message histories
            for agent in agents:
                agent.messages = []
            print(Fore.YELLOW + "Conversation context has been reset." + Style.RESET_ALL)
        else:
            print(Fore.YELLOW + "Conversation context has been retained for the next prompt." + Style.RESET_ALL)