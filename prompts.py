from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.validation import Validator


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


def service_prompt(prompt_msg):
    """
    Prompt user to enter a service
    :param prompt_msg: prompt message defined in main
    :return: None
    """
    # Define available services
    services = [
        "Ping",
        "Tracert",
        "HTTP",
        "HTTPS",
        "NTP",
        "DNS",
        "TCP",
        "UDP",
        "Echo",
        "",
    ]

    # Initialize auto-completer and validator for prompt session
    completer: WordCompleter = WordCompleter(services, ignore_case=True)
    validator = Validator.from_callable(
        lambda text: text in services,
        error_message=f"This is not a valid service!",
        move_cursor_to_end=True,
    )

    # Start prompt session
    prompt: PromptSession = PromptSession(completer=completer, validator=validator)

    # Prompt and return the input
    return prompt.prompt(f"{prompt_msg}")


def record_type_prompt(prompt_msg):
    """
    Prompt user for a dns record type
    :param prompt_msg: prompt message defined in main
    :return: user's input
    """
    # Define available record types
    record_types = [
        "A",
        "MX",
        "AAAA",
        "CNAME",
        "ANAME",
        "NS",
        "SOA",
        "TXT",
        "PTR",
        "SRV",
        "SPF",
        "",
    ]

    # Initialize auto-completer for prompt session
    completer: WordCompleter = WordCompleter(record_types, ignore_case=True)
    validator = Validator.from_callable(
        lambda text: text in record_types,
        error_message=f"This is not a valid record type!",
        move_cursor_to_end=True,
    )

    # Start prompt session
    prompt: PromptSession = PromptSession(completer=completer)

    # Prompt and return the input
    return prompt.prompt(f"{prompt_msg}")
