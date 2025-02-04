.. _reflectometry_gui_testing:

Reflectometry GUI Testing
=========================

.. contents::
   :local:

Introduction
------------

The ISIS Reflectometry interface is a graphical front end for the main ISIS reflectometry reduction algorithm :ref:`ReflectometryISISLoadAndProcess <algm-ReflectometryISISLoadAndProcess>` and post-processing algorithm :ref:`Stitch1DMany <algm-Stitch1DMany>`. The purpose of the interface is to speed up the analysis of the Reflectometry spectra by providing batch-mode execution of these algorithms on groups of runs.

This documentation refers to the `new interface <http://docs.mantidproject.org/nightly/interfaces/ISIS%20Reflectometry.html>`__. For reference, there are also instructions for testing the `old interface here <https://www.mantidproject.org/ISIS_Reflectometry_GUI>`__.

Set up
------

For the testing you require the ISIS reflectometry Example material:

- INTER_NR_test.json
- INTER00013460.nxs
- INTER00013462.nxs
- INTER00013463.nxs
- INTER00013464.nxs
- INTER00013469.nxs
- INTER00013470.nxs

These can be found in the `ISIS Sample Data <http://download.mantidproject.org>`__.

These instructions assume use of MantidWorkbench or MantidPlot 3.7 or higher.

**Set your log level to "information" for these tests before you start the interface for the first time**, by right clicking the Results Log view (in MantidPlot) or Messages view (in MantidWorkbench) and selecting ``Log Level->Information``.

Loading batch files
-------------------

- To load a batch file go to ``Batch->Load`` from inside the interface.
- Browse to the file that you want to load (e.g. ``INTER_NR_test.json``).
- The interface should now have all of the information for the runs and settings from the batch file populated in the display.
- Compare against a version of the batch file opened in your favourite text editor.
- Try to re-open the batch file again. You should not be asked if you want to discard the changes (unless you changed anything).

Changing the Default instrument
-------------------------------

- At the top-left and bottom-right of the interface is a drop-down menu called Instrument - it can switch between INTER, SURF, CRISP, POLREF, and OFFSPEC.  Make a selection from it.
- Check that a log was printed into the Results Log / Messages window.
- Check that the default instrument has actually changed by either looking at the instrument in the ``Help->First Time Setup`` dialog (in MantidPlot) or ``File->Settings`` (in MantidWorkbench) in the mantid main window or by running ``print(config['default.instrument'])`` or ``print(config.getInstrument().name())``.

Resizing the List Box
---------------------

The division between the Search Runs and Process Runs sections is a handle. It can be used to widen or shrink the list box. Check that it works.

Processing
----------

- Make sure the sample data directory is in your managed user directories.
- Load the batch file from the sample data. This should populate the main table with two groups, each containing two rows (you may need to click the little triangle next to the group name to expand the group).
- Select a single row within a group by clicking on it.
- Click Process. Some output workspaces should be produced and the row should turn green.
- The process bar along the bottom should go from empty to full.
- Repeat this test for multiple lines (selecting using Shift and Ctrl)
- Repeat this for a group by selecting the group header line and clicking Process.
- Repeat for the entire table (click off the table to deselect all rows and then Process will process everything that is left).

Generating Plots and the 'plot' button
--------------------------------------

There are two plotting buttons at the top of the interface - they look like little plots.

- Select a processed group:

  - Plot the "unstitched" data; the left of the two plot buttons. This should produce a plot with two separate lines for the individual reduced runs.
  - Plot the "stitched" data; the right of the two buttons. This should produce a plot with a single line for the stitched output.

- Select a processed row:

  - Plot the "unstitched" data; the left of the two plot buttons. This should produce a plot with one lines for that reduced run.
  - Plot the "stitched" data; this should do nothing for a row.

Polarisation Corrections
------------------------

Polarisation corrections settings are under the Settings tab in the interface. These should only work with CRISP, POLREF or OFFSPEC.

- In the Runs tab choose an instrument other than CRISP, POLREF or OFFSPEC.
- Switch to the Experiment Settings tab - the Polarisation corrections check box should be greyed out.
- Switch back to Runs and set the instrument to POLREF, CRISP or OFFSPEC.
- Switch back to Experiment Settings - the Polarisation corrections check box should now be enabled. Tick it and try processing something

  - e.g. (this will require the archive) OFFSPEC run 44956, angle 0.4, transmission run 44937.

Search for an RB Number
-----------------------
*You require a connection to the archives for this. Make sure the archive is mounted and is enabled in the Manage User Directories dialog.*.

- Find an experiment number e.g. INTER 1120015. There are a number of ways to find other experiment numbers:

  - the `JournalViewer <https://www.projectaten.com/jv>`__ provides an easy way to browse experiments
  - alternatively, in the archives, go to the ``\Instrument\logs\journal`` subdirectory of one of the instrument directories (named '**NDX{Instrument}**') and select an xml journal other than journal_main.xml. Look for a pair of ``experiment_identifier`` tags and note the number inside the tags. This is the RB number that the search functionality looks for.

- On the ISIS Reflectometry interface, change to the relevant instrument and enter the RB number in the Investigation Id textbox.
- Hit search, and enter your ICat login details if required.
- The search results list will fill with all the runs from ICat with that RB number.

Transfer Run Number and Transmission Runs
-----------------------------------------

- Perform a valid search in order to populate the search results list.
- Make sure the runs table is empty. Select one or more entries in the search results list.
- Press the 'Transfer' button.
- The run numbers should be filled into the table.

  - Runs with the same title will appear in the same group.
  - Runs in the same group with different angles will appear on different rows.
  - Runs in the same group with the same angle will be combined into the same row with the ``Run(s)`` field showing as a sum of all runs for that angle, e.g. ``13460+13462``.

- Click Transfer again with the same selection. If the runs are already in the table, nothing should happen, because duplicates should not be added.
- Select some different runs and click Transfer. The new runs should be added to the table.

Clearing the table
------------------

To empty the table: use ``Ctrl-A`` to select all rows and groups in the table and then press ``Delete`` to delete them.

Copy, Cut and Paste
-------------------

Copy, Cut and Paste are available from the toolbar buttons, the right-click contenx menu, or the standard Ctrl- C, X, and V shortcuts.

- Select a row, copy it, and paste it onto a different row. The values should be overwritten.
- Select 2 rows from one group, copy them, and paste onto 2 rows in another group. Note that you must select the same number of rows in the destination group or you will get an error.
- Select a group and copy it. Paste it onto another group. The group should be replaced with the one you copied.
- Copy a group and deselect everything in the table before you paste. It should be pasted as a new group at the end.
- Copy a row and try pasting with nothing selected. This should be disallowed because you can't paste a row without a group.
- Copy a row and try pasting onto a group. This should be disallowed.
- Copy a group and try pasting onto a row. This should be disallowed.

Closing the interface
---------------------

- Open the interface and load some data.
- Go to the Tools menu and select Options. Ensure the warnings are all enabled.
- Edit the data (note that processing does not count as an edit even though it changes the state displayed).
- Close the interface using the `x` button at the top.
- The interface should show a 'Save/Discard/Cancel' dialogue.

Saving
------

There are a few ways to save within the interface. The native save format is to a ``*.json`` batch file. Custom, 3-column, ANSTO and Ill cosmos are treated as export formats.

Batch Menu
^^^^^^^^^^
The Save action in the Batch menu allows you to save and re-load the interface contents. It saves to ``*.json`` format which is not intended to be particularly human-friendly, although it should still be readable.

- Load a ``*.json`` file and make a modification to it within the table.
- Go ``Batch->Save``.
- A Save dialog will appear. Select the location to save the file to. You should get a warning if you attempt to overwrite an existing file.
- Check using a plain text editor that the file has been created and contains some json data.
- Close and re-open the interface, don't load anything. Type some values into the table.
- Go ``Batch->Save``. A Save dialog will appear, select a location and provide a file name and hit 'Cancel'.
- Make sure no file was saved.

On Exit Prompt
^^^^^^^^^^^^^^

- Open the interface, don't load anything. Type some values into the table.
- Close the interface by hitting the close button in the title bar.
- You should receive a prompt with OK and Cancel (or whatever variation your OS uses).
- Make sure that 'Cancel' returns you to the interface without closing it. Try again and make sure that 'OK' closes the interface.

Export as ASCII
^^^^^^^^^^^^^^^
*Before doing anything else, make sure that the mantid main window has no loaded workspaces. Custom, 3-column, ANSTO and Ill cosmos are saved from existing workspaces, not from the interface's data. By clearing Mantid's workspaces you're making sure that the dialog this tests isn't getting entries from nowhere.*

- Open the interface, don't load anything.
- Go to the Save tab. The workspaces list should be empty.
- Load a batch file and process it.
- Go to the Save tab and hit Refresh. The workspaces list will contain the names of the workspaces created when you processed.
- Type an existing path into the Save path textbox.
- Type something in the prefix field you'd like to use to identify the file. *The files are saved in the form [prefix][workspace][ext]*.
- In the File Format section, select ``Custom format (*.dat)``, untick ``Header`` and ``Q resolution`` and set the separator to ``Comma``.
- Click ``Save`` and open the file that should have been saved to the save directory you specified. It should contain 3 columns of numbers, separated by commas.
- Tick ``Q resolution`` and re-save. It should now contain 4 columns of numbers.
- Double-click on a workspace name in the left list, e.g. ``IvsQ_13460``. The right list should be populated with parameters but be disabled.
- Tick ``Header`` and the parameters list should be enabled. Select a couple of them, e.g. ``nperiods`` and ``run_start``, and re-save.

  - The file should now contain some header text starting with ``MFT``.
  - Amongst other things this text should contain the logs you selected, e.g. ``nperiods : 1`` and ``run_end : 2011-12-15T14:19:13``.

- Try changing the separator to spaces or tabs and check that the 3 or 4 columns of numbers are separated using that separator.
- Change the dropdown to ``3 column (*.dat)``. The checkboxes, separators and parameter settings are not applicable so they should be greyed out. Click save and you should get 3 columns of numbers separated by tabs (including a leading tab). At the top there is an integer indicating the number of lines in the data.
- Change the dropdown to ``ANSTO, MotoFit, 4 Column (*.txt)``. The settings remain greyed out. Click save and you should get 4 columns of numbers separated by tabs (with no leading tab).
- Change the dropdown to ``ILL Cosmos (*.mft)``. The settings remain greyed out apart from the parameters which should now be enabled. Click save and you should get 3 columns of numbers padded by spaces (including leading spaces). There should be a header starting ``MFT`` which includes any parameters you selected, the same as the Custom format.

- Try entering a non-existent or invalid save path and then try to Save. You should get an error saying that the path is invalid.
