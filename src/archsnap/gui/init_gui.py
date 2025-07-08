import colorsys
import tkinter as tk
import webbrowser
from functools import partial
from importlib.resources import files
from multiprocessing import Pool
from pathlib import Path as p
from tkinter import colorchooser, ttk
from tkinter.filedialog import askdirectory, askopenfilename

from archsnap.mesh import get_mesh_args, render_mesh


def button_state_validation():
    """Enable or disable the add file and the render buttons"""
    # Disable the add file button if any of the file paths are empty
    add_file_button['state'] = tk.DISABLED if any(
        [x.entry_text.get() == '' for x in inputs_frame.winfo_children()]) else tk.NORMAL
    # Enable the render button if there are not no mesh entries,
    # and no mesh entries have errors, and no entries are empty, and the add file button is enabled
    render_button['state'] = tk.NORMAL if all([x.error_text.get() == '' and x.entry_text.get(
    ) != '' for x in inputs_frame.winfo_children()]) and add_file_button['state'] and len(inputs_frame.winfo_children()) > 0 else tk.DISABLED


def _handle_render(inputs_frame, output_frame):
    """Wrapper for the multiprocessed rendering functionality"""

    # Set up the work queue for multiprocessing the rendering across various instances of blender
    # and populate it from all the entries in the inputs frame as a list of parameters of shape:
    # mesh file path, output directory, use separate directories boolean, use eevee renderer boolean,
    # render resolution, calculated mesh scale factor, current scalebar tick size, mesh colour and index
    mesh_queue = [
        (x.entry_text.get(),
         output_frame.output_path.get(),
         output_frame.separate_output_directories_vars['current'].get(),
         output_frame.use_eevee_vars['current'].get(),
         output_frame.render_resolution_vars['current'].get(),
         x.mesh_scale_factor.get(),
         x.current_sizes['scalebar_tick'].get(),
         x.mesh_colour_vars['current'].get(),
         idx)
        for idx, x in enumerate(inputs_frame.winfo_children())]

    # Create a pool of len(mesh_queue) processes to run blender instances for each mesh
    with Pool(len(mesh_queue)) as pool:
        # Map each item in the list to its own instance of the render_mesh function
        pool.map(render_mesh, mesh_queue)
        # Close the queue, letting the worker processes to complete their tasks, required to call join()
        pool.close()
        # Wait until all workers have completed their tasks
        pool.join()
        # When the workers completed their tasks, show the user a messagebox
        # to ask if they want to open the output directory or not
        open_output = tk.messagebox.askyesno(
            'Image generation complete', 'Image generation was successfully completed!\n\nOpen the output directory?')
        # If they said yes to opening the output directory, do so
        if open_output:
            webbrowser.open(str(p(output_frame.output_path.get()).absolute()))


class _ConfigMeshModal(tk.Toplevel):
    """Modal for the configuration of mesh render settings"""

    def __init__(self, entry_text, size_vars, mesh_colour_vars, mesh_scale_factor, scalebar_scale_factor):
        """Initialise the modal for the individual mesh rendering configuration"""
        # Initiate the TopLevel as a child of the top tk.Tk()
        super().__init__(main_window)

        # Set the modal title
        self.title(
            f'Render settings for {p(entry_text.get()).absolute().name}')
        # Capture focus and prevent switching to the main window to make it a modal
        self.grab_set()
        self.attributes('-topmost')
        # Make it un-resizable in both directions.
        self.resizable(False, False)

        # Create the instance size variables from the provided parameters, sent as an array of
        # initial, current, and previous size dictionaries of StringVars
        [self.initial_sizes, self.current_sizes, self.previous_sizes] = size_vars
        # Get the remaining parameters as instance variables
        self.mesh_colour_vars, self.mesh_scale_factor, self.scalebar_scale_factor = \
            mesh_colour_vars, mesh_scale_factor, scalebar_scale_factor

        # Create the tk.StringVar to store the colour selection error text as an isntance variable
        self.colour_error_text = tk.StringVar()
        # Create a tk.StringVar for the value of the scalebar length to display in the respective label
        self.total_scalebar_size = tk.StringVar(value=f'Total scalebar length (10 ticks): '
                                                f'{float(self.current_sizes["scalebar_tick"].get())*10:.3f} cm')

        # Process the entry text to get the absolute file path
        file_path = p(entry_text.get()).absolute()

        # If the file path was somehow made invalid before opening the modal, exit
        if not file_path.is_file():
            tk.messagebox.showerror('Error', 'File does not exist!')
            self.destroy()
            return 404
        if not file_path.suffix in ['.ply', '.obj', '.stl', '.dae']:
            tk.messagebox.showerror(
                'Error', 'File type not supported!')
            self.destroy()
            return 406

        # Create the main frame of the modal and add it to the grid
        config_mesh_modal_main_frame = self._ConfigMeshModalMainFrame(
            self)
        config_mesh_modal_main_frame.grid(pady=10, padx=10)

    class _ConfigMeshModalMainFrame(ttk.Frame):
        def __init__(self, container):
            # Create the main frame of the modal
            super().__init__(container)

            # Create the frame for the labels
            labels_frame = ttk.Frame(self)
            labels_frame.grid(column=0, row=0, sticky='nw', padx=(0, 10))

            # Create the frame for the parameter editing widgets and add it to the grid
            options_frame = ttk.Frame(self)
            options_frame.grid(column=1, row=0, sticky='nw')

            # Create the label for the mesh dimensions editing section and add it to the grid
            dimensions_label = ttk.Label(
                labels_frame, text='Mesh dimensions in cm:')
            dimensions_label.grid(column=0, row=0, sticky='w')

            # Create the label for the x-dimension editing and add it to the grid
            mesh_x_size_label = ttk.Label(
                options_frame, text='x:')
            mesh_x_size_label.grid(
                column=0, row=0, sticky='w', padx=(0, 5))
            # Create the entry widget for the x-dimension editing and add it to the grid
            mesh_x_size_entry = ttk.Entry(
                options_frame, textvariable=container.current_sizes['x'], justify='center')
            mesh_x_size_entry.configure(width=12)
            mesh_x_size_entry.grid(
                column=1, row=0, sticky='', padx=(0, 5))
            # Bind the KeyRelease event of the x-dimension entry widget to
            # a lambda function that passes the event object and the dimension code (x = 0) to
            # the method to handle the mesh size changes
            mesh_x_size_entry.bind(
                '<KeyRelease>', lambda event: container._handle_mesh_size_change(event, 0))

            # Create the label for the y-dimension editing and add it to the grid
            mesh_y_size_label = ttk.Label(
                options_frame, text='y:')
            mesh_y_size_label.grid(
                column=2, row=0, sticky='w', padx=(0, 5))
            # Create the entry widget for the y-dimension editing and add it to the grid
            mesh_y_size_entry = ttk.Entry(
                options_frame, textvariable=container.current_sizes['y'], justify='center')
            mesh_y_size_entry.configure(width=12)
            mesh_y_size_entry.grid(
                column=3, row=0, sticky='', padx=(0, 5))
            # Bind the KeyRelease event of the y-dimension entry widget to
            # a lambda function that passes the event object and the dimension code (y = 1) to
            # the method to handle the mesh size changes
            mesh_y_size_entry.bind(
                '<KeyRelease>', lambda event: container._handle_mesh_size_change(event, 1))

            # Create the label for the z-dimension editing and add it to the grid
            mesh_z_size_label = ttk.Label(
                options_frame, text='z:')
            mesh_z_size_label.grid(
                column=4, row=0, sticky='w', padx=(0, 5))
            # Create the entry widget for the z-dimension editing and add it to the grid
            mesh_z_size_entry = ttk.Entry(
                options_frame, textvariable=container.current_sizes['z'], justify='center')
            mesh_z_size_entry.configure(width=12)
            mesh_z_size_entry.grid(
                column=5, row=0, sticky='', padx=(0, 50))
            # Bind the KeyRelease event of the z-dimension entry widget to
            # a lambda function that passes the event object and the dimension code (z = 2) to
            # the method to handle the mesh size changes
            mesh_z_size_entry.bind(
                '<KeyRelease>', lambda event: container._handle_mesh_size_change(event, 2))

            # Create the label for the editing of the scalebar and add it to the grid
            scalebar_tick_scale_label = ttk.Label(
                labels_frame, text='Scalebar tick length in cm:')
            scalebar_tick_scale_label.grid(
                column=0, row=1, sticky='w', pady=(10, 0))
            # Create the entry widget for the editing of the scalebar and add it to the grid
            scalebar_tick_size_entry = ttk.Entry(
                options_frame, textvariable=container.current_sizes['scalebar_tick'], justify='center')
            scalebar_tick_size_entry.configure(width=12)
            scalebar_tick_size_entry.grid(
                column=1, row=1, sticky='w', columnspan=5, pady=(5, 0))
            # Bind the KeyRelease event of the scalebar editing entry widget to
            # the method to handle the scalebar tick size changes
            scalebar_tick_size_entry.bind(
                '<KeyRelease>', container._handle_scalebar_tick_size_change)

            # Create the label widget to display the total scalebar length and add it to the grid
            scalebar_total_size_label = ttk.Label(
                options_frame, textvariable=container.total_scalebar_size, font=('TkDefaultFont', 8))
            scalebar_total_size_label.grid(
                column=2, row=1, columnspan=4, pady=(10, 0), sticky='w')

            # Create the frame for the colour picker for the mesh and add it to the grid
            colour_picker_frame = ttk.Frame(self)
            colour_picker_frame.grid(
                column=0, row=2, columnspan=2, sticky='nsew', pady=10)
            colour_picker_frame.columnconfigure(2, weight=999)

            # Create the label for the colour picker and add it to the grid
            colour_picker_label = ttk.Label(
                colour_picker_frame, text='Mesh colour:'
            )
            colour_picker_label.grid(column=0, row=0)
            # Create the entry widget for the manual editing of the mesh colour as an instance variable and add it to the grid
            self.colour_picker_entry = tk.Entry(
                colour_picker_frame, textvariable=container.mesh_colour_vars[
                    'current'], justify='center'
            )
            self.colour_picker_entry.configure(width=10)
            self.colour_picker_entry.grid(column=1, row=0)
            # Bind the KeyRelease event of the colour editing entry widget to
            # the method to handle manual colour code changes
            self.colour_picker_entry.bind(
                '<KeyRelease>', container._handle_colour_change)

            # Create the button for opening the colour picker dialog and add it to the grid
            colour_picker_button = ttk.Button(
                colour_picker_frame, text='Select colour', command=container._choose_colour
            )
            colour_picker_button.grid(column=2, row=0, padx=(5, 0), sticky='w')

            # Create the label widget to display any colour picker errors as an instance variable
            # and add it to the grid to actually create it, then hide it by default until there is an error
            self.colour_error_label = ttk.Label(
                colour_picker_frame, textvariable=container.colour_error_text, foreground='red')
            self.colour_error_label.grid(
                column=0, row=1, columnspan=3, sticky='w')
            self.colour_error_label.grid_forget()

            # Run an handling of colour change of the default colour obtained from the config
            container._handle_colour_change(None)

            # Create the frame for the modal buttons and add it to the grid
            buttons_frame = ttk.Frame(self)
            buttons_frame.grid(column=0, row=3, columnspan=2,
                               sticky='nsew', padx=10, pady=10)

            # First column and last column aligned at their respective edges, so the
            # middle column should have high weight to fill the space between them
            buttons_frame.columnconfigure(0, weight=1)
            buttons_frame.columnconfigure(1, weight=99)
            buttons_frame.columnconfigure(2, weight=1)

            # Create the button to restore initial values and add it to the grid
            initials_button = ttk.Button(
                buttons_frame, text='Initial values', command=container._handle_reset_to_initial_values)
            initials_button.grid(column=0, row=0, sticky='w')

            # Create the button to cancel the changes and add it to the grid
            cancel_button = ttk.Button(
                buttons_frame, text='Cancel', command=container._handle_cancel)
            cancel_button.grid(column=1, row=0, sticky='e')

            # Create the button to save the changes and add it to the grid
            save_button = ttk.Button(
                buttons_frame, text='Save', command=container._handle_save)
            save_button.grid(column=2, row=0)

    def _handle_mesh_size_change(self, _, dimension):
        """Handle the change of the mesh size through the entry widgets"""
        # TODO: Block non-numeric input

        # Local variables to simplify code
        current_sizes = self.current_sizes
        initial_sizes = self.initial_sizes

        # Do a match to get which dimension the user modified (x, y, z = 0, 1, 2)
        match dimension:
            # User modified the size along the x axis
            case 0:
                try:
                    # If we change x, see if we can convert the respective StringVar to a float
                    float(current_sizes['x'].get())
                except ValueError:
                    # If not then exit without doing anything
                    return 422
                if float(current_sizes['x'].get()) != 0:
                    # If we are not dividing by 0, set the mesh scale factor based on
                    # the user's input with respect to the initial size of the mesh
                    self.mesh_scale_factor.set(float(current_sizes['x'].get()) / float(
                        initial_sizes['x'].get()))
                else:
                    # If the value is 0, exit without doing anything
                    return 416
            # User modified the size along the y axis
            case 1:
                try:
                    # If we change y, see if we can convert the respective StringVar to a float
                    float(current_sizes['y'].get())
                except ValueError:
                    # If not then exit without doing anything
                    return 422
                if float(current_sizes['y'].get()) != 0:
                    # If we are not dividing by 0, set the mesh scale factor based on
                    # the user's input with respect to the initial size of the mesh
                    self.mesh_scale_factor.set(float(current_sizes['y'].get()) / float(
                        initial_sizes['y'].get()))
                else:
                    # If the value is 0, exit without doing anything
                    return 416
            # User modified the size along the z axis
            case 2:
                try:
                    # If we change z, see if we can convert the respective StringVar to a float
                    float(current_sizes['z'].get())
                except ValueError:
                    # If not then exit without doing anything
                    return 422
                if float(current_sizes['z'].get()) != 0:
                    # If we are not dividing by 0, set the mesh scale factor based on
                    # the user's input with respect to the initial size of the mesh
                    self.mesh_scale_factor.set(float(current_sizes['z'].get()) / float(
                        initial_sizes['z'].get()))
                else:
                    # If the value is 0, exit without doing anything
                    return 416

        # Loop through all three dimensions in both the current and initial sizes with an index
        for idx, (size, initial) in enumerate(
            zip([current_sizes['x'], current_sizes['y'], current_sizes['z']],
                [initial_sizes['x'], initial_sizes['y'], initial_sizes['z']])):
            # If the index is not the dimension
            # (since there is no need to change the values along the dimension the user just changed)
            if idx != dimension:
                # Calculate and set the new size along the other dimensions based on the mesh scale factor
                size.set(
                    str(f'{float(initial.get()) * float(self.mesh_scale_factor.get()):.4f}'))

    def _handle_scalebar_tick_size_change(self, _):
        """Handle the change of the scalebar tick size"""
        # TODO: Block non-numeric input
        # TODO: Validate against mesh dimensions to prevent too large scale factors

        # Local variable to improve code readability
        scalebar_tick_size = self.current_sizes['scalebar_tick'].get()

        try:
            # See if we can convert the respective StringVar to a float
            float(scalebar_tick_size)
        except ValueError:
            # If not then exit without doing anything
            return 422
        # If the tick size is not 0
        if (float(scalebar_tick_size) > 0):
            # Calculate and set the scalebar scale factor based on the current and initial tick sizes
            self.scalebar_scale_factor.set(
                float(scalebar_tick_size) / float(self.initial_sizes['scalebar_tick'].get()))
            # Call the method to set the value of the StringVar to display the total scalebar size
            self._set_total_scalebar_size()
        else:
            # If it is 0, return without doing anything
            return 416

    def _handle_colour_change(self, _):
        """Validate a colour input or selection and change
        the look of the entry widget to reflect the colour chosen"""

        # Local variables to improve readability
        colour = self.mesh_colour_vars['current'].get()
        config_mesh_modal_main_frame = self.winfo_children()[0]
        colour_picker_entry = config_mesh_modal_main_frame.colour_picker_entry
        colour_error_label = config_mesh_modal_main_frame.colour_error_label

        # If the colour is not an empty string and begins with a hash symbol
        # like a well-formed hex colour code should
        if colour and colour[0] == '#':
            # Try to parse the code
            try:
                # If the code is in the shape of #RGB instead of #RRGGBB,
                # parse it into a full length colour code by duplicating each
                # hex digit from each primary colour
                if len(colour) == 4:
                    colour = (
                        '#'
                        f'{colour[1]}{colour[1]}'
                        f'{colour[2]}{colour[2]}'
                        f'{colour[3]}{colour[3]}'
                    )
                # Get the integer values of the hex colour code (without the #)
                r, g, b = bytes.fromhex(colour[1:])
                # Convert those values (in decimal) to HLS to check the validity of the colour code
                hls = colorsys.rgb_to_hls(r/255, g/255, b/255)

                # If we have not excepted here, that means that there is no error,
                # so delete any error message and remove the label from the grid
                self.colour_error_text.set('')
                colour_error_label.grid_forget()

                # Depending on the luminosity, we change the text colour to white or black
                if hls[1] < 0.5:
                    colour_picker_entry.configure(foreground='white')
                else:
                    colour_picker_entry.configure(foreground='black')
                # Set the background of the entry widget to the chosen colour
                colour_picker_entry.configure(background=colour)

            except ValueError:
                # If there was an error, set the error text and display the error label
                self.colour_error_text.set('Invalid colour code!')
                colour_error_label.grid(columnspan=3, sticky='w')
        else:
            # If there was an error, set the error text and display the error label
            self.colour_error_text.set('Invalid colour code!')
            colour_error_label.grid(columnspan=3, sticky='w')

    def _choose_colour(self):
        """Colour picker dialog wrapper"""
        # Call the colour picker dialog
        colour_code = colorchooser.askcolor(title='Choose colour')

        # If the hex code in the dialog's return value (in the shape of [(r,g,b), hex])
        # is not empty
        if colour_code[1]:
            # Set the tk.StringVar for the currently chosen colour
            # and call the method to handle a colour change
            self.mesh_colour_vars['current'].set(colour_code[1])
            self._handle_colour_change(None)

    def _set_scale_factors(self):
        """Set the tk.DoubleVars of the mesh and scalebar tick scale factors"""
        self.mesh_scale_factor.set(
            float(self.current_sizes['x'].get())/float(self.initial_sizes['x'].get()))
        self.scalebar_scale_factor.set(
            float(self.current_sizes['scalebar_tick'].get())/float(self.initial_sizes['scalebar_tick'].get()))

    def _set_total_scalebar_size(self):
        """Set the display text of the total scalebar length"""
        total_scalebar_size = f'Total scalebar length (10 ticks): {float(self.current_sizes["scalebar_tick"].get())*10:.3f} cm'
        self.total_scalebar_size.set(total_scalebar_size)

    def _handle_reset_to_initial_values(self):
        """Set all values to initial values"""

        # Check if there were any changes made in the parameters compared to the initial values
        changed = any([current.get() != initial.get() or previous.get() != initial.get()
                       for [(_, current), (_, previous), (_, initial)] in
                       zip(self.current_sizes.items(), self.previous_sizes.items(), self.initial_sizes.items())])

        # If there were any changes
        if changed:
            # Ask the user for confirmation for resetting to initial values
            confirm = tk.messagebox.askyesno('Reset to initial values?',
                                             'Are you sure you want to reset all parameters to their initial values?')

            # If the user did not confirm, exit without changing
            if not confirm:
                return 304

            # If the user did confirm, set all parameters to their initial values
            self.current_sizes['x'].set(self.initial_sizes['x'].get())
            self.current_sizes['y'].set(self.initial_sizes['y'].get())
            self.current_sizes['z'].set(self.initial_sizes['z'].get())
            self.current_sizes['scalebar_tick'].set(
                self.initial_sizes['scalebar_tick'].get())
            self.mesh_colour_vars['current'].set(
                self.mesh_colour_vars['initial'].get())

            self.previous_sizes['x'].set(self.initial_sizes['x'].get())
            self.previous_sizes['y'].set(self.initial_sizes['y'].get())
            self.previous_sizes['z'].set(self.initial_sizes['z'].get())
            self.previous_sizes['scalebar_tick'].set(
                self.initial_sizes['scalebar_tick'].get())
            self.mesh_colour_vars['previous'].set(
                self.mesh_colour_vars['initial'].get())

            # Re-calculate the total scalebar size and the scale factors
            self._set_total_scalebar_size()
            self._set_scale_factors()

        # Show a confirmation that the initial values were restored
        tk.messagebox.showinfo(
            'Initial values', 'Parameters set to their initial values.')

    def _handle_cancel(self):
        """Exit the modal without making any changes after confirmation"""

        # Check if there were any changes made in the parameters since opening
        changed = any([current.get() != previous.get() for [(_, current), (_, previous)] in zip(
            self.current_sizes.items(), self.previous_sizes.items())])

        if changed:
            # If there were changes, ask the user to confirm they want to discard them
            confirm = tk.messagebox.askyesno('Discard changes?',
                                             'Are you sure you want to discard your changes?')
            # If the user did not confirm, exit the method without discarding
            if not confirm:
                return 304

            # If the user did confirm and there are changes,
            # set all current parameters to the values they had before changing
            self.current_sizes['x'].set(self.previous_sizes['x'].get())
            self.current_sizes['y'].set(self.previous_sizes['y'].get())
            self.current_sizes['z'].set(self.previous_sizes['z'].get())
            self.current_sizes['scalebar_tick'].set(
                self.previous_sizes['scalebar_tick'].get())
            self.mesh_colour_vars['current'].set(
                self.mesh_colour_vars['previous'].get())

        # Close the modal
        self.destroy()

    def _handle_save(self):
        """Save the changed parameters"""

        # Since the current values are stored in tk.StringVars, there's no need to do anything,
        # just set the 'previous' set of parameters to the current values so the cancel button
        # behaves as it should
        self.previous_sizes['x'].set(self.current_sizes['x'].get())
        self.previous_sizes['y'].set(self.current_sizes['x'].get())
        self.previous_sizes['z'].set(self.current_sizes['x'].get())
        self.previous_sizes['scalebar_tick'].set(
            self.current_sizes['scalebar_tick'].get())
        self.mesh_colour_vars['previous'].set(
            self.mesh_colour_vars['current'].get())

        # Re-calculate the total scalebar size and the scale factors
        self._set_total_scalebar_size()
        self._set_scale_factors()

        # Close the modal
        self.destroy()


class _NewInputMesh(ttk.Frame):
    """Frame for a new input mesh to render"""

    def __init__(self, container, first=False, file_path=None):
        """Initialise the new input mesh frame"""
        super().__init__(container)

        # Set the initial size instance variables as empty tk.StringVars
        self.initial_sizes = {
            'x': tk.StringVar(),
            'y': tk.StringVar(),
            'z': tk.StringVar(),
            'scalebar_tick': tk.StringVar()
        }
        # Set the currently set size instance variables as empty tk.StringVars
        self.current_sizes = {
            'x': tk.StringVar(),
            'y': tk.StringVar(),
            'z': tk.StringVar(),
            'scalebar_tick': tk.StringVar()
        }
        # Set the previously set (i.e. before any current edits) size instance variables as empty tk.StringVars
        self.previous_sizes = {
            'x': tk.StringVar(),
            'y': tk.StringVar(),
            'z': tk.StringVar(),
            'scalebar_tick': tk.StringVar()
        }

        self.mesh_colour_vars = {
            'initial': tk.StringVar(),
            'current': tk.StringVar(),
            'previous': tk.StringVar()
        }

        # Set the tk.StringVars for the filepath (entry widget) text and error text
        self.entry_text = tk.StringVar()
        self.error_text = tk.StringVar()

        # Set the tk.DoubleVars for the scaling factors of the mesh and scale bar as instance variables
        # and set them to 1
        self.mesh_scale_factor = tk.DoubleVar(value=1)
        self.scalebar_scale_factor = tk.DoubleVar(value=1)

        # Add self (new input frame) to the parent grid
        self.grid(column=0, sticky='w')

        # Create the input widget for the file path as an instance variable and add it to the grid
        self.entry_widget = ttk.Entry(self, textvariable=self.entry_text)
        self.entry_widget.configure(width=60)
        self.entry_widget.grid(column=1, row=0, padx=(7, 0))

        # Create the button to open the configuration modal as an instance variable
        self.configure_button = ttk.Button(
            self, text='⚙️',
            command=partial(_ConfigMeshModal, self.entry_text, [self.initial_sizes, self.current_sizes, self.previous_sizes],
                            self.mesh_colour_vars, self.mesh_scale_factor, self.scalebar_scale_factor)
        )
        self.configure_button.configure(width=3)
        # Set it to disabled by default until a valid file is selected
        self.configure_button['state'] = tk.DISABLED
        # Add the button to the grid (at column 3, after the browse button)
        self.configure_button.grid(column=3, row=0)

        # Add a remove entry button and add it to the grid at the start
        remove_entry_button = ttk.Button(self, text='❌',
                                         command=self._handle_remove_entry)
        remove_entry_button.configure(width=3)
        remove_entry_button.grid(column=0, row=0, ipadx=0, ipady=0)

        # Add the label widget to show any errors as an instance variable
        # add it to the grid to actually create it, then hide it by default until there is an error
        self.error_label = ttk.Label(
            self, textvariable=self.error_text, foreground='red')
        self.error_label.grid(columnspan=3, sticky='w')
        self.error_label.grid_forget()

        # Create the button to browse for a file and add it to the grid (at column 2, before the configure button)
        browse_button = ttk.Button(self, text='Browse…',
                                   command=self._select_mesh)
        browse_button.grid(column=2, row=0)

        # Bind the KeyRelease event of the file path entry widget
        # to handle the manual editing of the file path
        self.entry_widget.bind('<KeyRelease>', self._handle_manual_change)

        # If the file path is provided (as part of the directory selection)
        if (file_path is not None):
            # Set the entry widget text to the absolute path of the selected file
            self.entry_text.set(str(p(file_path).absolute()))
            # Set the view of the entry widget to see the end of the path (the most important part)
            self.entry_widget.xview('end')

            # Load the initial parameters for the selected mesh
            self._load_initial_parameter()

            # Enable the configure button (since the file path is validated by the directory selection)
            self.configure_button['state'] = tk.NORMAL

        # Perform validation for the render button state at start
        button_state_validation()

    def _handle_remove_entry(self):
        """Handle the removal of an file entry"""
        self.grid_forget()
        self.destroy()

        # Perform validation for the render button during deletion
        button_state_validation()

    def _clear_mesh_parameters(self):
        """Clear the initial instance parameters for the input mesh"""

        # Set all parameters to empty strings
        self.initial_sizes['x'].set('')
        self.initial_sizes['y'].set('')
        self.initial_sizes['z'].set('')
        self.initial_sizes['scalebar_tick'].set('')

        self.current_sizes['x'].set('')
        self.current_sizes['y'].set('')
        self.current_sizes['z'].set('')
        self.current_sizes['scalebar_tick'].set('')

        self.previous_sizes['x'].set('')
        self.previous_sizes['y'].set('')
        self.previous_sizes['z'].set('')
        self.previous_sizes['scalebar_tick'].set('')

        self.mesh_colour_vars['initial'].set(
            CONFIG_VALUES['default_object_colour'])
        self.mesh_colour_vars['current'].set(
            CONFIG_VALUES['default_object_colour'])
        self.mesh_colour_vars['previous'].set(
            CONFIG_VALUES['default_object_colour'])

    def _load_initial_parameter(self):
        """Load the initial parameters for the input mesh and save them to the instance variables"""

        # Check if the initial size is not yet changed
        # and if the file path is valid
        # and if the file type is supported
        if (self.initial_sizes['x'].get() == '' and
            p(self.entry_text.get()).absolute().is_file() and
                p(self.entry_text.get()).suffix in ['.ply', '.obj', '.stl', '.dae']):

            # Call the get_mesh_args function to calculate the mesh and scale dimensions as saved in the file
            dim_returns, scalebar_tick_returns = get_mesh_args(
                mesh_path=p(self.entry_text.get()).absolute())

            # Set the initial sizes to the calculated dimensions
            self.initial_sizes['x'].set(f'{dim_returns[0]:.4f}')
            self.initial_sizes['y'].set(f'{dim_returns[1]:.4f}')
            self.initial_sizes['z'].set(f'{dim_returns[2]:.4f}')
            self.initial_sizes['scalebar_tick'].set(
                f'{scalebar_tick_returns:.4f}')

            # Set the current and previous sizes to the initial sizes,
            # since no change in the parameters has been made yet
            self.current_sizes['x'].set(self.initial_sizes['x'].get())
            self.current_sizes['y'].set(self.initial_sizes['y'].get())
            self.current_sizes['z'].set(self.initial_sizes['z'].get())
            self.current_sizes['scalebar_tick'].set(
                self.initial_sizes['scalebar_tick'].get())

            self.previous_sizes['x'].set(self.initial_sizes['x'].get())
            self.previous_sizes['y'].set(self.initial_sizes['y'].get())
            self.previous_sizes['z'].set(self.initial_sizes['z'].get())
            self.previous_sizes['scalebar_tick'].set(
                self.initial_sizes['scalebar_tick'].get())

    def _handle_manual_change(self, event):
        """Handle the manual change of the file path entry widget"""

        # First, clear the initial parameters, since we changed the file path and thus file used
        self._clear_mesh_parameters()

        if not event.widget.get():
            # Add an error message, add the label to the grid, and disable the configure button
            self.error_text.set('Empty file path!')
            self.error_label.grid(columnspan=3, sticky='w')
            self.configure_button['state'] = tk.DISABLED
        # If the file path is not valid or the file does not exist
        elif not p(event.widget.get()).absolute().is_file():
            # Add an error message, add the label to the grid, and disable the configure button
            self.error_text.set('File does not exist!')
            self.error_label.grid(columnspan=3, sticky='w')
            self.configure_button['state'] = tk.DISABLED
        # Else if the file type is not supported
        elif not p(event.widget.get()).suffix in ['.ply', '.obj', '.stl', '.dae']:
            # Add an error message, add the label to the grid, and disable the configure button
            self.error_text.set('File type not supported!')
            self.error_label.grid(columnspan=3, sticky='w')
            self.configure_button['state'] = tk.DISABLED
        # Else (the file exists and is supported)
        else:
            # Load the initial parameters for the selected mesh
            self._load_initial_parameter()

            # Set the error text to empty, hide the error label, and enable the configure button
            self.error_text.set('')
            self.error_label.grid_forget()
            self.configure_button['state'] = tk.NORMAL

        # Perform validation for the render button state now with the changed file path
        button_state_validation()

    def _select_mesh(self):
        """Open a file selection dialog to select a mesh file"""

        # Use the askopenfilename function to open a file selection dialog,
        # specifying the file types to filter the selection, and store it as a Path object
        file_path = p(askopenfilename(filetypes=[('All compatible files', '.ply .obj .stl .dae'), (
            'Stanford PLY', '.ply'), ('Wavefront OBJ', '.obj'), ('STL', '.stl'), ('Collada DAE', '.dae')]))
        extension = file_path.suffix

        # Check file extension, and if the extension is not supported,
        # or no selection was made (i.e. extension == ''), exit the method
        if (extension not in ['.ply', '.obj', '.stl', '.dae']):
            return 406

        # If the file path is valid, clear the initial parameters,
        self._clear_mesh_parameters()

        # Set the entry widget text to the absolute path of the selected file
        self.entry_text.set(str(file_path.absolute()))
        # Set the view of the entry widget to see the end of the path (the most important part)
        self.entry_widget.xview('end')

        # Load the initial parameters for the selected mesh
        self._load_initial_parameter()

        # Set the error text to empty, since the file selected is valid
        self.error_text.set('')
        # Hide the error label widget and endable the configure button
        self.error_label.grid_forget()
        self.configure_button['state'] = tk.NORMAL

        # Perform validation for the render button state now with the newly selected file
        button_state_validation()


def _select_dir(inputs_frame):
    """Load all meshes from a single directory"""

    # Use the askdirectory function to open a directory selection dialog
    dir_path = askdirectory(mustexist=True)

    # Whether the last entry from the input frame is empty or not (to avoid overwriting it)
    last_entry_empty = True

    # If a directory was selected
    if dir_path != '':
        # Non-recursively iterate through files in the slected directory
        for file_path in p(dir_path).glob('*'):
            # If the file extension of is supported
            if file_path.suffix in ['.ply', '.obj', '.stl', '.dae']:

                # Get the last input frame (empty by default before any file has been selected)
                new_input_mesh_frame = inputs_frame.winfo_children()[-1]
                # If the last entry from the input frame is empty
                if not last_entry_empty:
                    # If the entry text is not empty (i.e. the file path is not empty)
                    if new_input_mesh_frame.entry_text.get() != '':
                        # Then we should not overwrite it
                        last_entry_empty: False

                # If the last entry from the input frame is emtpy
                if last_entry_empty:
                    # Set the file path but do not add a new frame
                    new_input_mesh_frame.entry_text.set(
                        str(file_path.absolute()))
                # If it is not empty (e.g. we already added files from this directory)
                else:
                    # Do not overwrite it, and start a new instance of the new input mesh frame
                    new_input_mesh_frame = _NewInputMesh(
                        inputs_frame, file_path=str(file_path.absolute()))

                # Set the configure button state to enabled, since the file path is ipso facto valid
                new_input_mesh_frame.configure_button['state'] = tk.NORMAL

                # Since by now we now have added a file path,
                # the last entry would never be empty, so set it to false
                last_entry_empty = False

                # Perform validation for the render button state now with the newly added file
                button_state_validation()


class _InputsFrame(ttk.Frame):
    """Frame for the list of input meshes to render"""

    def __init__(self, container):
        """Initialise the inputs frame"""
        super().__init__(container)

        # Configure the column weights
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=3)
        self.columnconfigure(2, weight=1)
        self.columnconfigure(3, weight=1)


class _AddMeshButtonsFrame(ttk.Frame):
    """Frame for the buttons to add meshes to render"""

    def __init__(self, container, inputs_frame):
        """Initialise the add mesh buttons frame"""
        super().__init__(container)

        global add_file_button
        # Create the button to add a single mesh and add it to the grid
        add_file_button = ttk.Button(self, text='➕ File',
                                     command=partial(_NewInputMesh, inputs_frame))
        add_file_button.configure(width=8)
        add_file_button.grid(column=0, row=0)

        # Create the button to add a directory of meshes and add it to the grid
        add_dir_button = ttk.Button(
            self, text='➕ Folder', command=partial(_select_dir, inputs_frame))
        add_dir_button.grid(column=1, row=0)


def _select_output(self, entry):
    """Select the output directory for the renders"""

    # Use the askdirectory function to open a directory selection dialog
    output_path = askdirectory(
        initialdir=f'{str(p(self.output_path.get()).parent)}')

    # If a directory was selected
    if output_path != '':
        # Set the tk.StringVar of the output directory to the selected directory
        self.output_path.set(str(p(output_path).absolute()))

        # Move the view of the entry widget to the end to see the end of the path, the most important part
        entry.xview('end')


class _ConfigOutputModal(tk.Toplevel):
    """Modal for the configuration of render output settings"""

    def __init__(self, output_frame):
        """Initialise the modal for the render output configuration"""
        # Initiate the TopLevel as a child of the top tk.Tk()
        super().__init__(main_window)

        # Set the modal title
        self.title('Configure output settings')
        # Capture focus and prevent switching to the main window to make it a modal
        self.grab_set()
        self.attributes('-topmost')
        # Make it un-resizable in both directions.
        self.resizable(False, False)

        # Create the config output modal main frame and add it to the grid
        config_output_frame = ttk.Frame(self)
        config_output_frame.grid(pady=10, padx=10)
        # Two column, multiple row layout, so only configure the columns
        config_output_frame.columnconfigure(0, weight=1)
        config_output_frame.columnconfigure(1, weight=0)

        # Frame for the option labels
        labels_frame = ttk.Frame(config_output_frame)
        labels_frame.grid(column=0, row=0, sticky='w', padx=(0, 10))

        # Frame for the option widgets
        options_frame = ttk.Frame(config_output_frame)
        options_frame.grid(column=1, row=0, sticky='w')

        # Option to select if each mesh's output should be saved in a separate directory or not
        # Create the label for the option and add it to the grid
        separate_dirs_label = ttk.Label(
            labels_frame, text='Save each mesh\'s output in a separate directory based on filename?')
        separate_dirs_label.grid(column=0, row=0, sticky='w')
        # Create the checkbox for the option and add it to the grid
        separate_dirs_checkbox = ttk.Checkbutton(
            options_frame, variable=output_frame.separate_output_directories_vars['current'], onvalue=1, offvalue=0)
        separate_dirs_checkbox.grid(column=0, row=0, sticky='')

        # Option to select if EEVEE should be used as the renderer or not
        # Create the label for the option and add it to the grid
        use_eevee_label = ttk.Label(
            labels_frame, text='Use faster EEVEE renderer?')
        use_eevee_label.grid(column=0, row=1, sticky='w')
        # Create the checkbox for the option and add it to the grid
        use_eevee_checkbox = ttk.Checkbutton(
            options_frame, variable=output_frame.use_eevee_vars['current'], onvalue=1, offvalue=0)
        use_eevee_checkbox.grid(column=0, row=1, sticky='')

        # Option to specify the render resolution
        # Create the label for the option and add it to the grid
        render_resolution_label = ttk.Label(
            labels_frame, text='Render resolution in px (height and width):')
        render_resolution_label.grid(column=0, row=2, sticky='w')
        # Create the entry widget for the option and add it to the grid
        render_resolution_entry = ttk.Entry(
            options_frame, textvariable=output_frame.render_resolution_vars['current'], justify='center')
        render_resolution_entry.grid(column=0, row=2, sticky='')
        render_resolution_entry.configure(width=7)

        # Create the frame for the modal buttons and add it to the grid
        buttons_frame = ttk.Frame(self)
        buttons_frame.grid(column=0, row=1, pady=(
            0, 10), padx=10, sticky='nsew')

        # First column and last column aligned at their respective edges, so the
        # middle column should have high weight to fill the space between them
        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.columnconfigure(1, weight=99)
        buttons_frame.columnconfigure(2, weight=1)

        # Create the button to restore factory default values and add it to the grid
        defaults_button = ttk.Button(
            buttons_frame, text='Factory defaults', command=partial(self._handle_factory_defaults, output_frame))
        defaults_button.grid(column=0, row=0, sticky='w')

        # Create the button to cancel the changes and add it to the grid
        cancel_button = ttk.Button(
            buttons_frame, text='Cancel', command=partial(self._handle_cancel, output_frame))
        cancel_button.grid(column=1, row=0, sticky='e')

        # Create the button to save the changes and add it to the grid
        save_button = ttk.Button(
            buttons_frame, text='Save', command=partial(self._handle_save, output_frame))
        save_button.grid(column=2, row=0)

    def _handle_factory_defaults(self, output_frame):
        """Handle a reset to factory defaults"""
        # Local variables to improve readability
        separate_output_directories_vars = output_frame.separate_output_directories_vars
        use_eevee_vars = output_frame.use_eevee_vars
        render_resolution_vars = output_frame.render_resolution_vars

        # Check if there were any changes made in the parameters compared to their factory defaults
        changed = any([var['current'].get() != var['default'].get() or var['previous'].get() != var['default'].get() for var
                       in (separate_output_directories_vars, use_eevee_vars, render_resolution_vars)])

        # If there were any changes
        if changed:
            # Ask the user for confirmation for resetting to factory defaults
            confirm = tk.messagebox.askyesno('Reset to factory defaults?',
                                             'Are you sure you want to reset all parameters to their factory defaults?')

            # If the user did not confirm, exit without changing
            if not confirm:
                return 304

            # If the user did confirm, set all parameters to their factory defaults
            separate_output_directories_vars['current'].set(
                DEFAULT_VALUES['separate_output_directories'])
            use_eevee_vars['current'].set(DEFAULT_VALUES['use_eevee'])
            render_resolution_vars['current'].set(
                DEFAULT_VALUES['render_resolution'])

        # Show a confirmation that the initial values were restored
        tk.messagebox.showinfo(
            'Defaults', 'Default settings have been restored.')

    def _handle_cancel(self, output_frame):
        """Exit the modal without making any changes after confirmation"""
        # Local variables to improve readability
        separate_output_directories_vars = output_frame.separate_output_directories_vars
        use_eevee_vars = output_frame.use_eevee_vars
        render_resolution_vars = output_frame.render_resolution_vars

        # Check if there were any changes made in the parameters compared to the previous values
        changed = any([var['current'].get() != var['default'].get() or var['previous'].get() != var['default'].get() for var
                       in (separate_output_directories_vars, use_eevee_vars, render_resolution_vars)])

        if changed:
            # If there were changes, ask the user to confirm they want to discard them
            confirm = tk.messagebox.askyesno('Discard changes?',
                                             'Are you sure you want to discard your changes?')
            # If the user did not confirm, exit the method without discarding
            if not confirm:
                return 304

            # If the user did confirm and there are changes,
            # set all current parameters to the values they had before changing
            separate_output_directories_vars['current'].set(
                separate_output_directories_vars['previous'].get())
            use_eevee_vars['current'].set(use_eevee_vars['previous'].get())
            render_resolution_vars['current'].set(
                render_resolution_vars['previous'].get())

        # Close the modal
        self.destroy()

    def _handle_save(self, output_frame):
        """Save the changed parameters"""
        # Local variables to improve readability
        separate_output_directories_vars = output_frame.separate_output_directories_vars
        use_eevee_vars = output_frame.use_eevee_vars
        render_resolution_vars = output_frame.render_resolution_vars

        # Since the current values are stored in tk.StringVars, there's no need to do anything,
        # just set the 'previous' set of parameters to the current values so the cancel button
        # behaves as it should
        separate_output_directories_vars['previous'].set(
            separate_output_directories_vars['current'].get())
        use_eevee_vars['previous'].set(use_eevee_vars['current'].get())
        render_resolution_vars['previous'].set(
            render_resolution_vars['current'].get())

        # Close the modal
        self.destroy()


class _OutputsFrame(ttk.Frame):
    """Frame for the output options frame"""

    def __init__(self, container):
        """Initialise the outputs frame"""
        super().__init__(container)

        # Configure the column weights
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.columnconfigure(2, weight=0)

        # Set up the tkinter variables for the output settings as instance variables
        self.separate_output_directories_vars = {
            'default': tk.BooleanVar(value=DEFAULT_VALUES['separate_output_directories']),
            'current': tk.BooleanVar(value=CONFIG_VALUES['separate_output_directories']),
            'previous': tk.BooleanVar(value=CONFIG_VALUES['separate_output_directories']),
        }
        self.use_eevee_vars = {
            'default': tk.BooleanVar(value=DEFAULT_VALUES['use_eevee']),
            'current': tk.BooleanVar(value=CONFIG_VALUES['use_eevee']),
            'previous': tk.BooleanVar(value=CONFIG_VALUES['use_eevee']),
        }
        self.render_resolution_vars = {
            'default': tk.IntVar(value=DEFAULT_VALUES['render_resolution']),
            'current': tk.IntVar(value=CONFIG_VALUES['render_resolution']),
            'previous': tk.IntVar(value=CONFIG_VALUES['render_resolution']),
        }
        # Set up the tk.StringVar for the output path as instance variables
        self.output_path = tk.StringVar(
            value=str(CONFIG_VALUES['render_output_path']))

        # Create the label for the output path label and add it to the grid
        output_path_label = ttk.Label(self, text='Render output path:')
        output_path_label.grid(column=0, row=0, sticky='w')

        # Create the output path entry widget and add it to the grid
        output_entry = ttk.Entry(self, textvariable=self.output_path)
        output_entry.grid(column=0, row=1, sticky='ew')

        # Move the view of the entry widget to the end to see the end of the path, the most important part
        output_entry.xview('end')

        # Create the button for selecting the output dir and add it to the grid
        browse_output_button = ttk.Button(
            self, text='Browse…', command=partial(_select_output, self, output_entry))
        browse_output_button.grid(column=1, row=1)

        # Create the button to configure the render output settings and add it to the grid
        output_settings_button = ttk.Button(
            self, text='⚙️', command=partial(_ConfigOutputModal, self))
        output_settings_button.configure(width=3)
        output_settings_button.grid(column=2, row=1)


class _MainFrame(ttk.Frame):
    """Main frame for the archSnap GUI window"""

    def __init__(self, container):
        """Intialise the main frame"""
        super().__init__(container)

        # Multiple rows, single column layout, so only define the column configuration
        self.columnconfigure(0, weight=1)

        global inputs_frame
        # Create the frame for the input meshes
        inputs_frame = _InputsFrame(self)
        # Make it into a grid layout
        inputs_frame.grid(sticky='w', column=0, row=1, pady=(0, 10))

        # Create the frame for the buttons to add ocjects to render
        add_mesh_buttons_frame = _AddMeshButtonsFrame(self, inputs_frame)
        # Make it into a grid layour
        add_mesh_buttons_frame.grid(sticky='w', column=0, row=0, pady=(0, 10))

        # Create the frame for the output options section
        output_frame = _OutputsFrame(self)
        # Make it into a grid layout
        output_frame.grid(column=0, row=2, pady=(20, 20), sticky='nsew')

        # Create the frame for the render button
        render_frame = ttk.Frame(self)
        # Make it into a grid layout
        render_frame.grid(column=0, row=3)

        global render_button
        # Create the start render button and add it to the grid
        render_button = ttk.Button(
            render_frame, text='Generate images', command=partial(_handle_render, inputs_frame, output_frame))
        render_button.grid(column=0, row=0)

        # Add the first empty input mesh frame at start
        _NewInputMesh(inputs_frame)


class _App(tk.Tk):
    """Class for the main archSnap GUI window"""

    def __init__(self):
        super().__init__()

        # Set the title and icon
        self.title('ArchSnap')
        self.iconbitmap(files('archsnap').joinpath('data/icos/icon.ico'))
        # Prevent resizing
        self.resizable(False, False)

        # Set the weights of the main window row and column
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Create the main frame
        main_frame = _MainFrame(self)
        main_frame.grid(sticky='nsew', padx=10, pady=10)


# Set up the global variables for the config values and default values
CONFIG_VALUES = None
DEFAULT_VALUES = None


def init_gui(config_values, default_values):
    """Initialise the GUI for ArchSnap"""

    # Declare the config values and default values as global variables
    global CONFIG_VALUES, DEFAULT_VALUES
    # Set the global variables to the provided config and default values
    CONFIG_VALUES = config_values
    DEFAULT_VALUES = default_values

    # Declare the root as main variable (for modals dialogs to use as parent)
    global main_window
    # Create a new root window
    main_window = _App()
    # Run the Tkinter main loop
    main_window.mainloop()
