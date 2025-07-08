from archsnap.config import parse_config_file
from archsnap.gui import init_gui


def main():
    """Main function to initialise ArchSnap"""

    # Parse the configuration file and store the values
    config_values, default_values = parse_config_file()

    # Run the main GUI window and pass the configuration values
    init_gui(config_values, default_values)
