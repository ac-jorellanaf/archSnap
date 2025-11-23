from pathlib import PurePath
from tkinter import BooleanVar, StringVar, IntVar
from typing import TypedDict


class ConfigValues(TypedDict):
    render_output_path: PurePath
    render_resolution: int
    use_eevee: bool
    separate_output_directories: bool
    default_object_colour: str


class MeshQueueItem(TypedDict):
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
    x: StringVar
    y: StringVar
    z: StringVar
    scalebar_tick: StringVar


class SizeVarsDict(TypedDict):
    initial: SizeVar
    current: SizeVar
    previous: SizeVar


class ColourVars(TypedDict):
    initial: StringVar
    current: StringVar
    previous: StringVar


class OutputVars(TypedDict):
    default: BooleanVar
    current: BooleanVar
    previous: BooleanVar


class RenderResolutionVars(TypedDict):
    default: IntVar
    current: IntVar
    previous: IntVar
