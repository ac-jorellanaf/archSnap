"""Module for the mesh handling methods."""

import math
import sys
from importlib.resources import files
from pathlib import Path
from typing import Literal, cast

from archsnap.custom_types import MeshQueueItem

# Avoiding the issue of importing bpy while multiprocessing
# as mentioned in https://github.com/TylerGubala/blenderpy/issues/23#issuecomment-514826760
ORIG_SYS_PATH = list(sys.path)
import bpy  # noqa: E402

sys.path = ORIG_SYS_PATH

# TODO: For performance, change the bpy.ops to matrix transformations where applicable  # noqa: E501, FIX002, TD002, TD003


def import_mesh(mesh_path: Path) -> {str} | Literal[406]:
    """Safely import a compatibe mesh into blender.

    Returns either the imported mesh object or a 406.
    """
    # From the mesh_path Path object, get the suffix
    extension = mesh_path.suffix
    # Based on the file extension, run the relevant bpy import function or quit
    # if invalid
    match extension:
        case ".ply":
            return bpy.ops.wm.ply_import(filepath=str(mesh_path))
        case ".obj":
            return bpy.ops.wm.obj_import(filepath=str(mesh_path))
        case ".stl":
            return bpy.ops.wm.stl_import(filepath=str(mesh_path))
        case ".dae":
            return bpy.ops.wm.dae_import(filepath=str(mesh_path))
        case _:
            return 406


def get_mesh_args(
    mesh_path: Path,
) -> tuple[tuple[float, float, float], float] | tuple[None, None]:
    """Get the initial size of a mesh from a pathlib Path object."""
    # Set the cursor to the cartesian centre
    bpy.context.scene.cursor.location = (0, 0, 0)

    # Run the import mesh function and store its return in import_results
    import_result = import_mesh(mesh_path)

    # If the importing was completed
    if "FINISHED" in import_result:
        # The imported mesh will be the only seleted object,
        # so grab it from selected_objects[0], and store that in a variable
        obj = bpy.context.selected_objects[0]
        # A more readable alternative would be bpy.data.objects[f'{mesh_path.name}'],
        # but this might break a bit too easily with non-standard filenames

        # Select the object in the viewport
        obj.select_set(state=True)
        # Set it as the active object in the view layer
        bpy.context.view_layer.objects.active = obj

        # Set the origin of the object to the centre of volume of the object
        # based on its bounding box
        bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_VOLUME", center="BOUNDS")
        # Then move the object's origin to the cartesian centre
        obj.location = (0, 0, 0)
        # Apply that location to the object
        bpy.ops.object.transform_apply(location=True, scale=False, rotation=False)

        # Get the initial scalebar tick size by getting the largest object dimension
        # and dividing by the 10 ticks in the scalebar
        initial_scalebar_tick_size = (
            max([cast("float", x) for x in obj.dimensions[0:3]]) / 10
        )

        # Round the scalebar tick size to the nearest round number (375>400, 325>300)
        # calculated through -floor(log10(initial_tick_size)).
        # The log10(initial_tick_size) caculates the significant digits
        # (log10(0.01)=-2, log10(100)=2), while the floor function makes sure that the
        # right number of significant digits (log10(50)=1.70 > floor(1.70)=1).
        # Since the round function uses the number of digits as number of decimals
        # (round(215,2)=215.00), we need to change the sign to get the right
        # significant digit (round(215,-2)=200)
        scalebar_tick_size = round(
            initial_scalebar_tick_size,
            -math.floor(math.log10(initial_scalebar_tick_size)),
        )

        # We return the object dimensions as a single object and then also the
        # scalebar tick size
        return (
            cast("tuple[float, float, float]", obj.dimensions[0:3]),
            scalebar_tick_size,
        )

    # Close this blender instance
    bpy.ops.wm.quit_blender()

    return None, None


def render_mesh(mesh_queue: MeshQueueItem) -> None:  # noqa: C901, PLR0912, PLR0915
    """Render the mesh from a multiprocessing mesh queue object."""
    # Get the variables from the mesh queue
    mesh_path = Path(mesh_queue["mesh_path"])
    output_path = Path(mesh_queue["output_path"])
    separate_output_directories = mesh_queue["separate_output_directories"]
    use_eevee = mesh_queue["use_eevee"]
    render_resolution = mesh_queue["render_resolution"]
    object_scale_factor = mesh_queue["object_scale_factor"]
    scalebar_tick_size = float(mesh_queue["scalebar_tick_size"])
    object_colour = mesh_queue["object_colour"]
    index = mesh_queue["index"]

    # If the user chose to save the renders in separate output directories
    if separate_output_directories:
        # Set the correct output path for this mesh
        output_path = Path(output_path / f"{index}_{mesh_path.name.replace('.', '_')}")
    # Recursively create all the necessary directories to the output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Get the template Blender scene file path
    scene_path = files("archsnap").joinpath("data/artefact_scene.blend")

    # Open the template Blender scene file in our Blender instance
    bpy.ops.wm.open_mainfile(filepath=str(scene_path))
    # Setup the render resolution settings
    bpy.context.scene.render.resolution_x = render_resolution
    bpy.context.scene.render.resolution_y = render_resolution
    bpy.context.scene.render.resolution_percentage = 100
    # Set cursor to origin of scene, just in case it has moved
    bpy.context.scene.cursor.location = (0, 0, 0)

    # If the user set the setting to use the EEVEE rendered
    if use_eevee:
        # Set it as the selected render engine
        bpy.context.scene.render.engine = "BLENDER_EEVEE"
    else:
        # Else set Cycles as the render engine
        bpy.context.scene.render.engine = "CYCLES"
        # Loop through the available compute types
        for compute_type in ["CUDA", "OPTIX", "HIP", "ONEAPI"]:
            # Set the preferences to the current compute type
            bpy.context.preferences.addons[
                "cycles"
            ].preferences.compute_device_type = compute_type
            # Get the available devices
            devices = bpy.context.preferences.addons["cycles"].preferences.devices
            # Loop through them
            for device in devices:
                # Set them to be used for rendering
                device["use"] = True
            # If the currently set compute type has an active device
            if bpy.context.preferences.addons["cycles"].preferences.has_active_device():
                # Set the Cycles engine device to GPU Compute and quit the loop
                bpy.context.scene.cycles.device = "GPU"
                break
            # If it does not have an active device and we already arrived at the last
            # compute type
            if compute_type == "ONEAPI":
                # Set the compute type to none
                # (since we did not find a compatible device)
                bpy.context.preferences.addons[
                    "cycles"
                ].preferences.compute_device_type = "NONE"
                # And set the rendering device to CPU only
                bpy.context.scene.cycles.device = "CPU"
            # If we are not yet at the last compute type, we can continue looping
            else:
                continue

    # Import the mesh to render and grab the result of the importing
    import_result = import_mesh(mesh_path)

    # If the importing is complete
    if "FINISHED" in import_result:
        # The imported mesh will be the only seleted object,
        # so grab it from selected_objects[0], and store that in a variable
        obj = bpy.context.selected_objects[0]
        # A more readable alternative would be bpy.data.objects[f'{mesh_path.name}'],
        # but this might break a bit too easily with non-standard filenames

        # Select the object in the viewport
        obj.select_set(state=True)
        # Set it as the active object in the view layer
        bpy.context.view_layer.objects.active = obj

        # Set the origin of the object to the centre of volume of the object based
        # on its bounding box
        bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_VOLUME", center="BOUNDS")
        # Then move the object's origin to the cartesian centre
        obj.location = (0, 0, 0)
        # Apply that location to the object
        bpy.ops.object.transform_apply(location=True, scale=False, rotation=False)

        # Set the scale of the object to the passed object_scale_factor arg
        obj.scale[0:3] = (object_scale_factor, object_scale_factor, object_scale_factor)
        # Apply that transformation to the object
        bpy.ops.object.transform_apply(location=False, scale=True, rotation=False)

        # Get the default scalebar tick size for this rescaled object as the largest
        # object dimension and divide it by the 10 ticks in the scalebar
        default_scalebar_tick_size = max([float(x) for x in obj.dimensions[0:3]]) / 10
        # Calculate the rescale factor so that the object itself is by default actually
        # only 10 units in size in its largest dimension (the matching of the dimensions
        # and scalebar to the desired sizes will be done via mathematical trickery)
        rescale_factor: float = 1 / max([float(x) for x in obj.dimensions[0:3]]) * 10
        # Apply the rescale factor (the object is now 10 units in its largest dimension)
        obj.scale[0:3] = (rescale_factor, rescale_factor, rescale_factor)
        bpy.ops.object.transform_apply(location=False, scale=True, rotation=False)

        # if the desired scalebar tick size is larger than the calculated default size
        if scalebar_tick_size > default_scalebar_tick_size:
            # The rescale factor is now the default size divided by the desired size,
            # meaning the object must be made smaller
            # (since with larger tick size than default,
            # it would be smaller than 10 scalebar ticks)
            rescale_factor = default_scalebar_tick_size / scalebar_tick_size
            # Apply this new rescale factor to the object
            obj.scale[0:3] = (rescale_factor, rescale_factor, rescale_factor)
            bpy.ops.object.transform_apply(location=False, scale=True, rotation=False)
            scalebar_rescale_factor = 1.0
        # If the desired scalebar tick size is smaller than the calculated default size
        else:
            # The rescale factor is now the desired tick size divided by the
            # default scalebar tick size
            scalebar_rescale_factor = scalebar_tick_size / default_scalebar_tick_size
            # Now instead of rescaling the object, we rescale the scalebar instead,
            # since the scalebar is now necessarily smaller than the
            # maximum object length
            bpy.data.objects["Scale Bar"].scale = (
                scalebar_rescale_factor,
                scalebar_rescale_factor,
                scalebar_rescale_factor,
            )
            # Apply the transformation
            bpy.ops.object.transform_apply(location=False, scale=True, rotation=False)

        # We set up the offset for the Array modifier that creates the scalebar at
        # the bottom of the image
        bpy.data.objects["Scale Bar"].modifiers[
            "Bottom Scale Bar"
        ].constant_offset_displace[0] = -5.58 / scalebar_rescale_factor

        # We prepare the label text (the size of each scalebar tick) that
        # accompanies the scalebar
        label_tick_size = (
            round(scalebar_tick_size)
            if scalebar_tick_size.is_integer()
            else round(scalebar_tick_size, 4)
        )

        # We store all the label and stroke objects of the scene into
        # the labels variable
        labels = [
            bpy.data.objects["Scale Label Left"],
            bpy.data.objects["Scale Label Bottom"],
            bpy.data.objects["Scale Stroke Left"],
            bpy.data.objects["Scale Stroke Bottom"],
        ]
        # Then iterate through it
        for x in labels:
            # We make the label object text bodies be the same
            x.data.body = f"{label_tick_size} cm"
            # And if they are the labels from the bottom sscale
            if " Bottom" in x.name:
                # We position them correctly
                x.location[0] = -5.15 / scalebar_rescale_factor - (
                    0.4 / scalebar_rescale_factor - 0.4
                )
                x.location[1] = -5.58 / scalebar_rescale_factor

        # We set up the colour of the object based on the passed arg,
        # removing the initial # and appending to it 'ff' at the end,
        # since we need it as an RGBA hex
        object_colour = object_colour.lstrip("#") + "ff"
        # We also need to convert the hex to decimal values (0 to 1),
        # so we iterate through the entire colour code (from pos 0 to 8, in steps of 2)
        # convert the hex to a decimal number (int(object_colour[i:i+2], 16)),
        # and divide by 255 to obtain the decimal RGBA
        colour_tuple = cast(
            "tuple[float, float, float, float]",
            tuple(int(object_colour[i : i + 2], 16) / 255 for i in range(0, 8, 2)),
        )
        # We have already prepared a material in the scene, so we simply
        # assign the colour tuple to the Principled BSDF diffuse colour value
        bpy.data.materials["ArtefactMaterial"].node_tree.nodes[
            "Principled BSDF"
        ].inputs[0].default_value = colour_tuple
        # We then add the material to the mesh we wish to render (since it is
        # freshly imported, it has no material)
        mat = bpy.data.materials.get("ArtefactMaterial")
        obj.data.materials.append(mat)

        # Loop through all six animation frames (i.e. all six orthogonal views:
        # top, bottom, left, right, front, back)
        for i in range(1, 7):
            # Set the frame in the scene
            bpy.context.scene.frame_set(frame=i)
            # Set the render path of the png file for this frame
            render_path = Path(
                output_path
                / f"{mesh_path.name.replace('.', '_')}_render_{i}_tick_length_"
                f"{str(label_tick_size).replace('.', '-')}cm.png",
            )
            # Render the scene, and save to the stored path
            bpy.ops.render.render()
            bpy.data.images["Render Result"].save_render(filepath=str(render_path))

    # When we are done with rendering, quit this blender instance
    bpy.ops.wm.quit_blender()
