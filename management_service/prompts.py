from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.validation import Validator


def monitor_command_prompt(prompt_msg):
    """
    Prompt user for a command to send to monitor_service service
    :param prompt_msg: message to display for prompt
    :return: user input from prompt
    """
    # Define available main commands
    monitor_commands = [
        "run-ping",
        "pause-ping",
        "stop-ping",
        "run-tracert",
        "pause-tracert",
        "stop-tracert",
        "run-http",
        "pause-http",
        "stop-http",
        "run-https",
        "pause-https",
        "stop-https",
        "run-dns",
        "pause-dns",
        "stop-dns",
        "run-ntp",
        "pause-ntp",
        "stop-ntp",
        "run-tcp",
        "pause-tcp",
        "stop-tcp",
        "run-udp",
        "pause-udp",
        "stop-udp",
        "run-echo",
        "pause-echo",
        "stop-echo",
        "run-all",
        "pause-all",
        "stop-all",
    ]

    # Initialize auto-completer and validator for prompt session
    completer: WordCompleter = WordCompleter(monitor_commands, ignore_case=True)
    validator = Validator.from_callable(
        lambda text: text in monitor_commands,
        error_message=f"This is not a valid command!",
        move_cursor_to_end=True,
    )

    # Start prompt session
    prompt: PromptSession = PromptSession(completer=completer, validator=validator)

    # Prompt and return the input
    return prompt.prompt(f"{prompt_msg}")


def results_prompt(prompt_msg: str):
    """
    Prompt user for command during result gathering
    :param prompt_msg: message to display for prompt
    :return: user input from prompt
    """
    # Define available commands
    results_commands = ["send-server-command", "quit"]

    # Initialize auto-completer and validator for prompt session
    completer: WordCompleter = WordCompleter(results_commands, ignore_case=True)
    validator = Validator.from_callable(
        lambda text: text in results_commands,
        error_message=f"This is not a valid command!",
        move_cursor_to_end=True,
    )

    # Start prompt session
    prompt: PromptSession = PromptSession(completer=completer, validator=validator)

    # Prompt and return the input
    return prompt.prompt(f"{prompt_msg}")


def monitor_choice_prompt(prompt_msg: str, configs: dict):
    """
    Prompt user for choice of available monitors
    :param prompt_msg: message to display for prompt
    :param configs: dictionary with monitor_service configs
    :return: user input from prompt
    """
    # Load configs
    monitor_choices = []
    for config in configs.values():
        monitor_choices.append(f"IP: {config['IP']}, Port: {config['Port']}")

    # Initialize auto-completer and validator for prompt session
    completer: WordCompleter = WordCompleter(monitor_choices, ignore_case=True)
    validator = Validator.from_callable(
        lambda text: text in monitor_choices,
        error_message=f"This is not a valid command!",
        move_cursor_to_end=True,
    )

    # Start prompt session
    prompt: PromptSession = PromptSession(completer=completer, validator=validator)

    # Prompt and return the input
    choice = prompt.prompt(f"{prompt_msg}")
    for monitor, config in configs.items():
        if choice == f"IP: {config['IP']}, Port: {config['Port']}":
            monitor_id = monitor
            host = config["IP"]
            port = config["Port"]
            services = config["Services"]
    return monitor_id, host, port, services
