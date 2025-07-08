import configparser
from importlib.resources import files
from pathlib import Path as p

# Hardcoded path to the configuration file
CONFIG_PATH = files('archsnap').joinpath('config/config.ini')

def parse_config_file():
    """Parse the configuration file."""

    ## Default values
    # Default output path for the renders should be in the 'output' directory
    # in the project root two levels up from the current file location (src/archSnap)
    RENDER_OUTPUT_PATH = p(
        p.cwd().absolute() / 'output')
    # Default render resolution of 1920x1920
    RENDER_RESOLUTION = 1920
    # Use the faster EEVEE rendering engine by default
    USE_EEVEE = True
    # By default save each object's renders in a separate directory
    SEPARATE_OUTPUT_DIRECTORIES = True
    # Default object colour for the render
    DEFAULT_OBJECT_COLOUR = '#808080'

    # Create a dictionary for the 'factory settings'
    default_values = {
        'render_output_path': RENDER_OUTPUT_PATH,
        'render_resolution': RENDER_RESOLUTION,
        'use_eevee': USE_EEVEE,
        'separate_output_directories': SEPARATE_OUTPUT_DIRECTORIES,
        'default_object_colour': DEFAULT_OBJECT_COLOUR,
    }

    # Pre-populate the configuration values with the default values
    # in case the config file does not exist or cannot be read
    config_values = default_values.copy()

    # Check if the configuration file exists
    if (CONFIG_PATH).exists():
        # If it exists, try to read its values
        try:
            # Read the configuration file contents
            config = configparser.ConfigParser()
            config.read(CONFIG_PATH)

            # Get the output path as an absolute Path object
            RENDER_OUTPUT_PATH = p(config.get(
                'render', 'output_path', fallback=RENDER_OUTPUT_PATH)).absolute()
            # Get the render resolution as an integer
            RENDER_RESOLUTION = config.getint(
                'render', 'resolution', fallback=RENDER_RESOLUTION)
            # Get whether to use the EEVEE rendering engine as a boolean
            USE_EEVEE = config.getboolean(
                'render', 'use_eevee', fallback=USE_EEVEE)
            # Get whether to save each object's renders in a separate directory as a boolean
            SEPARATE_OUTPUT_DIRECTORIES = config.getboolean(
                'render', 'separate_output_directories', fallback=SEPARATE_OUTPUT_DIRECTORIES)
            # Get the default object colour as a string
            DEFAULT_OBJECT_COLOUR = config.get(
                'object', 'default_object_colour', fallback=DEFAULT_OBJECT_COLOUR)

        # Except any errors when reading the file
        except configparser.Error as e:
            print(f'Error reading config file: {e}')
            return None

        # Create a dictionary for the saved configuration values
        config_values = {
            'render_output_path': RENDER_OUTPUT_PATH,
            'render_resolution': RENDER_RESOLUTION,
            'use_eevee': USE_EEVEE,
            'separate_output_directories': SEPARATE_OUTPUT_DIRECTORIES,
            'default_object_colour': DEFAULT_OBJECT_COLOUR,
        }

    # Return the saved and default configuration values
    return config_values, default_values
