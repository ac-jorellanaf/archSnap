"""Custom types for type-hinting."""

from pathlib import PurePath
from tkinter import BooleanVar, IntVar, StringVar
from typing import TypedDict


class ConfigValues(TypedDict):
    """Class for the base app configuration values."""

    render_output_path: PurePath
    render_resolution: int
    use_eevee: bool
    separate_output_directories: bool
    default_object_colour: str


class MeshQueueItem(TypedDict):
    """Class for an individual multiprocessing queue dictionary."""

    mesh_path: str
    output_path: str
    separate_output_directories: bool
    use_eevee: bool
    render_resolution: int
    object_scale_factor: float
    scalebar_tick_size: str
    object_colour: str
    index: int


class SizeVar(TypedDict):
    """Class for the dict of mesh and scalebar tick size variables."""

    x: StringVar
    y: StringVar
    z: StringVar
    scalebar_tick: StringVar


class SizeVarsDict(TypedDict):
    """Class for an object containing the initial, current, and previous SizeVars."""

    initial: SizeVar
    current: SizeVar
    previous: SizeVar


class ColourVars(TypedDict):
    """Class for the initial, current, and previous StringVars of hex colour codes."""

    initial: StringVar
    current: StringVar
    previous: StringVar


class OutputVars(TypedDict):
    """Class for the default, current, and previous output config BooleanVars."""

    default: BooleanVar
    current: BooleanVar
    previous: BooleanVar


class RenderResolutionVars(TypedDict):
    """Class for the default, current, and previous render resolution IntVars."""

    default: IntVar
    current: IntVar
    previous: IntVar
