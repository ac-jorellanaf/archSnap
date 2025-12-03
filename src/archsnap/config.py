"""Module to parse the configuration of the program."""

import configparser
import logging
from importlib.resources import files
from pathlib import Path

from .custom_types import ConfigValues

# Hardcoded path to the configuration file
CONFIG_PATH = files("archsnap").joinpath(".config/config.ini")


def parse_config_file() -> tuple[ConfigValues, ConfigValues]:
    """Parse the configuration file."""
    # Default values
    #
    # Default output path for the renders should be in the 'output' directory
    # in the project root. If the user is running this module locally, then
    # the CWD would be in ROOT/src, so we check if this is the case and adjust
    # the output path accordingly.
    render_output_path = Path(
        Path.cwd().absolute() / "output"
        if Path.cwd().parts[-1] != "src"
        else Path.cwd().absolute().parent / "output",
    )
    # Default render resolution of 1920x1920
    render_resolution = 1920
    # Use the faster EEVEE rendering engine by default
    use_eevee = True
    # By default save each object's renders in a separate directory
    separate_output_directories = True
    # Default object colour for the render
    default_object_colour = "#808080"

    # Create a dictionary for the 'factory settings'
    default_values: ConfigValues = {
        "render_output_path": render_output_path,
        "render_resolution": render_resolution,
        "use_eevee": use_eevee,
        "separate_output_directories": separate_output_directories,
        "default_object_colour": default_object_colour,
    }

    # Pre-populate the configuration values with the default values
    # in case the config file does not exist or cannot be read
    config_values: ConfigValues = default_values.copy()

    # Check if the configuration file exists
    if CONFIG_PATH.is_file():
        # If it exists, try to read its values
        try:
            # Read the configuration file contents
            config = configparser.ConfigParser()
            config.read(str(CONFIG_PATH))

            # Get the output path as an absolute Path object
            render_output_path = Path(
                config.get(
                    "render",
                    "output_path",
                    fallback=render_output_path,
                ),
            ).absolute()
            # Get the render resolution as an integer
            render_resolution = config.getint(
                "render",
                "resolution",
                fallback=render_resolution,
            )
            # Get whether to use the EEVEE rendering engine as a boolean
            use_eevee = config.getboolean(
                "render",
                "use_eevee",
                fallback=use_eevee,
            )
            # Get whether to save each object's renders in a separate directory
            # as a boolean
            separate_output_directories = config.getboolean(
                "render",
                "separate_output_directories",
                fallback=separate_output_directories,
            )
            # Get the default object colour as a string
            default_object_colour = config.get(
                "object",
                "default_object_colour",
                fallback=default_object_colour,
            )

        # Except any errors when reading the file
        except configparser.Error as e:
            logger = logging.getLogger(__name__)
            logger.exception(
                "Error reading config file.",
                extra=f"{e}\nContinuing with default configuration.",
            )
            return default_values, default_values

        # Create a dictionary for the saved configuration values
        config_values = {
            "render_output_path": render_output_path,
            "render_resolution": render_resolution,
            "use_eevee": use_eevee,
            "separate_output_directories": separate_output_directories,
            "default_object_colour": default_object_colour,
        }

    # Return the saved and default configuration values
    return config_values, default_values
