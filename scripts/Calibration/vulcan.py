from collections import namedtuple
import h5py
from mantid.simpleapi import (LoadEventAndCompress, CloneWorkspace, CompressEvents, ConvertDiffCal, ConvertUnits, CreateGroupingWorkspace,
                              CropWorkspace, CrossCorrelate, DeleteWorkspace, GeneratePythonScript, GetDetectorOffsets,
                              LoadInstrument, mtd, Plus, Rebin, SaveDiffCal, SaveNexusProcessed)
import numpy as np
import os
from typing import Any, Dict, Tuple, Union


CROSS_CORRELATE_PEAK_FIT_NUMBER = 1
"""
Total = 81920 * 2 + (24900 - 6468) * 2 = 200704
Bank 1: 81920 .. center = 40,960 - ??? ...  40960
Bank 2: 81920 ... center = 61,140  ...  61140
Bank 5: 36864 ... center = 182,272 ...182272
"""
VULCAN_X_PIXEL_RANGE = {'Bank1': (0, 81920),  # 160 tubes
                        'Bank2': (81920, 163840),   # 160 tubes
                        'Bank5': (163840, 200704)   # 72 tubes
                        }
VULCAN_X_PIXEL_NUMBER = 200704


class CrossCorrelateParameter(namedtuple('CrossCorrelateParameter',
                                         'name reference_peak_position reference_peak_width reference_ws_index '
                                         'cross_correlate_number bin_step start_ws_index end_ws_index')):
    """
    A data class for cross correlation parameters
    """
    def __new__(cls, name: str, reference_peak_position: float = 1.07577, reference_peak_width: float = 0.01,
                reference_ws_index: int = 40704, cross_correlate_number: int = 80, bin_step: float = -0.0003,
                start_ws_index: int = -1, end_ws_index: int = -1):
        return super(CrossCorrelateParameter, cls).__new__(cls, name, reference_peak_position, reference_peak_width, reference_ws_index,
                                                           cross_correlate_number, bin_step, start_ws_index, end_ws_index)


def load_and_crop(runnumbers, bin_step: float = -.001, tof_min: float = 500, tof_max: float = 16666.7,
                  d_min: float = 0.3, d_max: float = 2.1,
                  bad_pulse_threashold: float = 10, reload_instrument: bool = False, convert_to_dspace=False):
    # put instrument name into filenames
    filenames = [f'VULCAN_{runnum}' for runnum in runnumbers]
    # workspace to accumulate to is just first runnumber
    dia_wksp = filenames[0]

    # load and accumulate
    for filename in filenames:
        LoadEventAndCompress(Filename=filename, OutputWorkspace=filename,
                             MaxChunkSize=16, FilterBadPulses=bad_pulse_threashold)
        # accumulate if not the first file
        if filename != dia_wksp:
            Plus(LHSWorkspace=dia_wksp,
                 RHSWorkspace=filename,
                 OutputWorkspace=dia_wksp, ClearRHSWorkspace=True)
            DeleteWorkspace(Workspace=str(filename))
    if len(filenames) > 1:
        CompressEvents(InputWorkspace=dia_wksp, OutputWorkspace=dia_wksp)

    # reduce the time-of-flight range
    CropWorkspace(InputWorkspace=dia_wksp, OutputWorkspace=dia_wksp, XMin=tof_min, XMax=tof_max)

    # optionally Reload instrument from the version on disk
    if reload_instrument:
        LoadInstrument(Workspace=dia_wksp, InstrumentName='VULCAN', RewriteSpectraMap=False)

    if convert_to_dspace:
        ConvertUnits(InputWorkspace=dia_wksp, OutputWorkspace=dia_wksp, Target='dSpacing')
        Rebin(InputWorkspace=dia_wksp, OutputWorkspace=dia_wksp,
              Params=(d_min, bin_step, d_max))
    else:
        Rebin(InputWorkspace=dia_wksp, OutputWorkspace=dia_wksp,
              Params=(tof_min,bin_step,tof_max))

    return mtd[dia_wksp]


def default_cross_correlation_setup() -> Dict[str, CrossCorrelateParameter]:
    # peak position in d-Spacing
    bank1_cc_param = CrossCorrelateParameter('Bank1', reference_peak_position=1.2614, reference_peak_width=0.04,
                                             reference_ws_index=40704, cross_correlate_number=80,
                                             bin_step=-0.0003, start_ws_index=0, end_ws_index=512 * 160)
    bank2_cc_param = CrossCorrelateParameter('Bank2', reference_peak_position=1.2614, reference_peak_width=0.04,
                                             reference_ws_index=40704, cross_correlate_number=80,
                                             bin_step=-0.0003, start_ws_index=512 * 160, end_ws_index=512 * 320)
    bank5_cc_param = CrossCorrelateParameter('Bank3', reference_peak_position=1.07577, reference_peak_width=0.01,
                                             reference_ws_index=182528, cross_correlate_number=20,
                                             bin_step=-0.0003, start_ws_index=512 * 320, end_ws_index=512 * (320 + 72))

    # do cross correlation
    cross_correlate_param_dict = {'Bank1': bank1_cc_param,
                                  'Bank2': bank2_cc_param,
                                  'Bank5': bank5_cc_param}

    return cross_correlate_param_dict


def process_calibration_flag(cross_correlate_param_dict: Dict[str, CrossCorrelateParameter],
                             bank_calibration_flag: Union[Dict[str, bool], None]) -> Dict[str, bool]:

    if bank_calibration_flag is None:
        # default: all True
        bank_calibration_flag = dict()
        for module_name in cross_correlate_param_dict:
            bank_calibration_flag[module_name] = True

    elif len(bank_calibration_flag) < len(cross_correlate_param_dict):
        # fill in blanks
        flags = bank_calibration_flag.values()
        flag_sum = np.sum(np.array(flags))
        if flag_sum == 0:
            # user specifies False
            default_flag = True
        elif flag_sum != len(flags):
            # user specifies both True and False
            raise RuntimeError(f'User specifies both True and False but not all the components.'
                               f'It causes confusion')
        else:
            default_flag = False

        # fill in the default values
        for component_name in cross_correlate_param_dict:
            if component_name not in bank_calibration_flag:
                bank_calibration_flag[component_name] = default_flag

    return bank_calibration_flag


def calculate_detector_2theta(workspace, ws_index):
    """ Calculate a detector's 2theta angle
    :param workspace:
    :param ws_index: where the detector is
    :return:
    """
    detpos = workspace.getDetector(ws_index).getPos()
    samplepos = workspace.getInstrument().getPos()
    sourcepos = workspace.getInstrument().getSource().getPos()
    q_out = detpos - samplepos
    q_in = samplepos - sourcepos

    twotheta = q_out.angle(q_in) / np.pi * 180

    return twotheta


def cross_correlate_calibrate2(ws_name: str,
                               peak_position: float,
                               peak_min: float,
                               peak_max: float,
                               ws_index_range: Tuple[int, int],
                               reference_ws_index: int,
                               cc_number: int,
                               max_offset: float,
                               binning: float,
                               ws_name_posfix: str = '',
                               peak_fit_time: int = 1,
                               debug_mode: bool = False):
    """Calibrate instrument (with a diamond run) with cross correlation algorithm
    on a specified subset of spectra in a diamond workspace
    This is the CORE workflow algorithm for cross-correlation calibration
    Parameters
    ----------
    ws_name: str
        diamond workspace name
    peak_position: float
        reference peak position
    peak_min: float
        peak range lower boundary
    peak_max: float
        peak range upper boundary
    ws_index_range: ~tuple
        starting workspace index, ending workspace index (excluded)
    reference_ws_index: int
        workspace index of the reference detector
    cc_number: int
        Cross correlation range (for XMin and XMax)
    max_offset: float
        Maximum offset allowed for detector offsets
    binning: float
        binning step
    ws_name_posfix: str
        posfix of the workspace created in the algorithm
    peak_fit_time: int
        number of peak fitting in GetDetectorOffsets
    debug_mode: bool
        Flag to output internal workspace to process NeXus files for debugging
    Returns
    -------
    ~tuple
        OffsetsWorkspace name, MaskWorkspace name
    """
    # Process inputs: reference of input workspace
    diamond_event_ws = retrieve_workspace(ws_name, True)
    if peak_fit_time == 1:
        fit_twice = False
    else:
        fit_twice = True
    if fit_twice:
        raise RuntimeError('Fit twice is not supported yet')

    # get reference detector position
    det_pos = diamond_event_ws.getDetector(reference_ws_index).getPos()
    twotheta = calculate_detector_2theta(diamond_event_ws, reference_ws_index)
    print(f'[INFO] Reference spectra = {reference_ws_index}  position @ {det_pos}   2-theta = {twotheta}  '
          f'Workspace Index range: {ws_index_range[0]}, {ws_index_range[1]}; Binning = {binning}')

    Rebin(InputWorkspace=ws_name, OutputWorkspace=ws_name, Params='0.5, -{}, 1.5'.format(abs(binning)))

    # Cross correlate spectra using interval around peak at peakpos (d-Spacing)
    cc_ws_name = 'cc_' + ws_name + '_' + ws_name_posfix
    CrossCorrelate(InputWorkspace=ws_name,
                   OutputWorkspace=cc_ws_name,
                   ReferenceSpectra=reference_ws_index,
                   WorkspaceIndexMin=ws_index_range[0],
                   WorkspaceIndexMax=ws_index_range[1],
                   XMin=peak_min,
                   XMax=peak_max)

    # optionally save
    if debug_mode:
        SaveNexusProcessed(InputWorkspace=cc_ws_name,
                           Filename=os.path.join(os.getcwd(), f'step1_ref{reference_ws_index}_{cc_ws_name}.nxs'))

    # TODO - THIS IS AN IMPORTANT PARAMETER TO SET THE MASK
    # min_peak_height = 1.0
    # Get offsets for pixels using interval around cross correlations center and peak at peakpos (d-Spacing)
    offset_ws_name = 'offset_' + ws_name + '_' + ws_name_posfix
    mask_ws_name = 'mask_' + ws_name + '_' + ws_name_posfix

    print('[INFO] ref peak pos = {}, xrange = {}, {}'.format(peak_position, -cc_number, cc_number))
    try:
        GetDetectorOffsets(InputWorkspace=cc_ws_name,
                           OutputWorkspace=offset_ws_name,
                           MaskWorkspace=mask_ws_name,
                           Step=abs(binning),
                           DReference=peak_position,
                           XMin=-cc_number,
                           XMax=cc_number,
                           MaxOffset=max_offset,
                           PeakFunction='Gaussian')
        if debug_mode and False:
            SaveNexusProcessed(InputWorkspace=offset_ws_name, Filename=f'Step2_Offset_{offset_ws_name}.nxs')
    except RuntimeError as run_err:
        # failed to do cross correlation
        print(f'[ERROR] Failed to cross correlation on ({ws_index_range[0]}, {ws_index_range[1]}):'
              f' Step = {abs(binning)}, DReference = {peak_position}, XMin/XMax = +/- {cc_number},'
              f'MaxOffset = {max_offset}')
        if debug_mode:
            SaveNexusProcessed(InputWorkspace=cc_ws_name, Filename=f'Step1_CC_{cc_ws_name}.nxs')
        # raise run_err
        return None, run_err

    # Do analysis to the calibration result
    # it returns full set of spectra
    # report_masked_pixels(diamond_event_ws, mtd[mask_ws_name], ws_index_range[0], ws_index_range[1])

    # check result and remove interval result
    if mtd.doesExist(ws_name + "cc" + ws_name_posfix):
        mtd.remove(ws_name + "cc")

    return offset_ws_name, mask_ws_name


def cross_correlate_vulcan_data(diamond_ws_name: str,
                                cross_correlate_param_dict: Dict[str, CrossCorrelateParameter],
                                calib_flag: Dict[str, bool],
                                cc_fit_time: int = 1,
                                prefix: str = '1fit') -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Calibrate VULCAN runs with cross correlation algorithm
    Main entrance cross-correlation (for VULCAN Bank1/2/5).
    Vulcan Team (Ke):
    VULCAN-X: when auto reducing, time focus data to pixel (ID) 48840 for bank 1 and 2,
    ...       and 422304 (ID) for bank 5.
    ...       those are centers.
    wsindex = 40704    pixel id = 48840
    wsindex = 182528   pixel id = 422304
    Parameters
    ----------
    diamond_ws_name: str
        input diamond workspace name
    cross_correlate_param_dict: ~dict
        parameters for cross correlation
    calib_flag: ~dict
        calibration panel flag
    cc_fit_time: int
        number of peak fitting in the GetDetectorOffsets
    prefix: str
        output workspace prefix
    Returns
    -------
    ~tuple
        offset workspace dictionary, mask workspace dictionary
    """
    # Check input
    assert isinstance(cross_correlate_param_dict, dict), f'Type mismatch: {cross_correlate_param_dict}:  {type(cross_correlate_param_dict)}'

    # Version issue
    if cc_fit_time == 2:
        raise RuntimeError(f'Current GetDetectorOffsets cannot support cc_fit_time = {cc_fit_time}')

    # Set up input
    offset_ws_dict = dict()
    mask_ws_dict = dict()

    # Loop over
    for bank_name in calib_flag:
        # skip disabled bank
        if not calib_flag[bank_name]:
            continue
        # retrieve parameter to set up cross correlation
        # start_ws_index, end_ws_index = VULCAN_X_PIXEL_RANGE[bank_name]

        bank_i_cc_param = cross_correlate_param_dict[bank_name]
        start_ws_index = bank_i_cc_param.start_ws_index
        end_ws_index = bank_i_cc_param.end_ws_index
        peak_pos_i = bank_i_cc_param.reference_peak_position
        # ref_ws_index = bank_i_cc_param.reference_ws_index
        peak_width = bank_i_cc_param.reference_peak_width
        # cc_number_i = bank_i_cc_param.cross_correlate_number
        bank_i_offset, bank_i_mask = cross_correlate_calibrate2(diamond_ws_name,
                                                                peak_pos_i,
                                                                peak_pos_i - peak_width, peak_pos_i + peak_width,
                                                                (start_ws_index, end_ws_index - 1),  # Note: inclusive
                                                                bank_i_cc_param.reference_ws_index,
                                                                bank_i_cc_param.cross_correlate_number,
                                                                1,
                                                                bank_i_cc_param.bin_step,
                                                                f'{bank_name}_{prefix}',
                                                                peak_fit_time=cc_fit_time,
                                                                debug_mode=False)
        if bank_i_offset is None:
            err_msg = bank_i_mask
            print('[ERROR] Unable to calibrate {} by cross correlation: {}'.format(bank_name, err_msg))
        else:
            offset_ws_dict[bank_name] = bank_i_offset
            mask_ws_dict[bank_name] = bank_i_mask
    # END-IF

    if len(offset_ws_dict) == 0:
        raise RuntimeError('No bank is calibrated.  Either none of them is flagged Or all of them failed')

    return offset_ws_dict, mask_ws_dict


def _merge_mask_workspaces(target_mask_ws_name: str,
                           source_mask_ws_name: str):
    """Merge (add) 2 MaskWorkspaces from source mask workspace to target mask workspace.
    The original masked pixels in the target workspace will be reserved
    Parameters
    ----------
    target_mask_ws_name: str
        name of the target mask workspace to have mask to merge into
    source_mask_ws_name: str
        name of the source mask workspace to have mask to merge from
    Returns
    -------
    None
    """
    print('[MERGING MASK] {} + {} = {}'.format(target_mask_ws_name, source_mask_ws_name, target_mask_ws_name))

    # Get the non-zero spectra from LHS and RHS (as masks)
    lhs_index_list = np.where(mtd[target_mask_ws_name].extractY().flatten() > 0.1)[0].tolist()
    rhs_index_list = np.where(mtd[source_mask_ws_name].extractY().flatten() > 0.1)[0].tolist()

    # Set the masked spectra from source MaskWorkspace to target MaskWorkspace
    target_mask_ws = mtd[target_mask_ws_name]

    for masked_index in rhs_index_list:
        masked_index = int(masked_index)
        target_mask_ws.dataY(masked_index)[0] = 1.

    # Mask pixels
    # merge 2 lists
    lhs_index_list.extend(rhs_index_list)
    lhs_index_list.extend(rhs_index_list)
    # remove redundant pixels
    merged_masked_pixels = list(set(lhs_index_list))
    # mask all detectors explicitly
    target_mask_ws.maskDetectors(WorkspaceIndexList=merged_masked_pixels)

    # verify output
    print(f'[MERGING MASK] {target_mask_ws_name}: sum(Y) = {np.sum(mtd[target_mask_ws_name].extractY().flatten())}')


def _merge_partial_offset_mask_workspaces(offset_ws_name: str,
                                          partial_offset_ws_name: str,
                                          mask_ws_name: str,
                                          partial_mask_ws_name: str) -> Tuple[str, str]:
    """Merge partially calibrated offsets and masks to the final offsets and masks workspace
    Parameters
    ----------
    offset_ws_name: str
        target final offset workspace name
    partial_offset_ws_name: str
        target
    mask_ws_name
    partial_mask_ws_name
    Returns
    -------
    ~tuple
        final offset workspace name, final mask workspace name
    """
    # Merge offsets
    # use Plus to combine 2 offsets workspace
    Plus(LHSWorkspace=offset_ws_name, RHSWorkspace=partial_offset_ws_name,
         OutputWorkspace=offset_ws_name)

    # Merge masks
    # Make sure mask_ws_name is a string for workspace name
    mask_ws_name = str(mask_ws_name)

    # merge masks workspace
    _merge_mask_workspaces(mask_ws_name, partial_mask_ws_name)

    return offset_ws_name, mask_ws_name


def retrieve_workspace(ws_name: str,
                       raise_if_not_exist: bool = False):
    """
    Retrieve workspace from AnalysisDataService
    Purpose:
        Get workspace from Mantid's analysis data service
    Requirements:
        workspace name is a string
    Guarantee:
        return the reference to the workspace or None if it does not exist
    :param ws_name:
    :param raise_if_not_exist:
    :return: workspace instance (1)
    """
    assert isinstance(ws_name, str), 'Input ws_name %s is not of type string, but of type %s.' % (str(ws_name),
                                                                                                  str(type(
                                                                                                      ws_name)))

    if mtd.doesExist(ws_name) is False:
        if raise_if_not_exist:
            raise RuntimeError('ADS does not exist workspace named as {0}.'.format(ws_name))
        else:
            return None

    return mtd.retrieve(ws_name)


def copy_bank_wise_offset_values(target_calib_ws, ref_calib_ws, bank_name):
    """Copy over offset values from reference calibration by bank
    Parameters
    ----------
    target_calib_ws: str
        target TableWorkspace
    ref_calib_ws: str
        source TableWorkspace
    bank_name: str
        bank name in (Bank1, Bank2, Bank5)
    Returns
    -------
    None
    """
    start_pid, end_pid = VULCAN_X_PIXEL_RANGE[bank_name]
    row_range = range(start_pid, end_pid)

    # Get the workspaces handlers
    if isinstance(target_calib_ws, str):
        target_calib_ws = retrieve_workspace(target_calib_ws, True)
    if isinstance(ref_calib_ws, str):
        ref_calib_ws = retrieve_workspace(ref_calib_ws, True)

    # Copy over values
    num_cols = target_calib_ws.columnCount()
    for row_index in row_range:
        for col_index in range(num_cols):
            target_calib_ws.setCell(row_index, col_index, ref_calib_ws.cell(row_index, col_index))


def copy_bank_wise_masks(target_mask_ws, ref_mask_ws: Union[str, Any], bank_name: str):
    """Copy over masks from reference mask workspace to target workspace for a specific bank
    Parameters
    ----------
    target_mask_ws
    ref_mask_ws: str, MaskWorkspace
        reference mask workspace
    bank_name
    Returns
    -------
    None
    """
    # Get pixel ID (detector ID) range
    start_pid, end_pid = VULCAN_X_PIXEL_RANGE[bank_name]
    ws_index_range = range(start_pid, end_pid)

    # apply
    if isinstance(target_mask_ws, str):
        mask_ws = retrieve_workspace(target_mask_ws, True)
    else:
        mask_ws = target_mask_ws
    if isinstance(ref_mask_ws, str):
        ref_mask_ws = retrieve_workspace(ref_mask_ws, True)

    # static
    num_masked = 0
    for iws in ws_index_range:
        ref_y_i = ref_mask_ws.dataY(iws)[0]
        mask_ws.dataY(iws)[0] = ref_y_i
        if ref_y_i > 0.5:
            num_masked += 1
    # END-FOR

    print('[REPORT] Apply {} masked detectors from workspace {} range workspace index {}:{}'
          ''.format(num_masked, ref_mask_ws, ws_index_range[0], ws_index_range[-1]))


def apply_masks(mask_ws):
    """
    apply masked Y to detector
    :param mask_ws:
    :return:
    """
    # collect the masked spectra
    mask_wsindex_list = list()
    for iws in range(mask_ws.getNumberHistograms()):
        if mask_ws.readY(iws)[0] > 0.5:
            mask_wsindex_list.append(iws)

    # mask all detectors explicitly
    mask_ws_name = mask_ws.name()
    mask_ws.maskDetectors(WorkspaceIndexList=mask_wsindex_list)
    mask_ws = mtd[mask_ws_name]

    print('[INFO] {}: # Masked Detectors = {}'.format(mask_ws.name(), len(mask_wsindex_list)))

    return mask_ws


def merge_detector_calibration(offset_ws_dict: Dict,
                               mask_ws_dict: Dict,
                               num_banks: int,
                               output_ws_name: str,
                               ref_calib_ws: Union[None, str],
                               ref_mask_ws: Union[None, str]) -> Tuple[str, Any, Any]:
    """Merge calibrated (per bank) detector offsets and masks
    Parameters
    ----------
    offset_ws_dict
    mask_ws_dict
    num_banks
    output_ws_name
    ref_calib_ws: str, None
        reference calibration workspace.
    ref_mask_ws: str, None
        reference mask workspace
    Returns
    -------
    ~tuple
        calibration workspace, offset workspace, mask workspace
    """
    # Get banks recorded in the calibrated offsets and masks
    bank_names = list(offset_ws_dict.keys())
    bank_names.sort()

    # Merge offsets and masks
    out_offset_ws_name = f'{output_ws_name}_offset'
    out_mask_ws_name = f'{output_ws_name}_mask'

    for ib, bank_name in enumerate(bank_names):
        if ib == 0:
            # Clone first bank's mask and offsets for output
            CloneWorkspace(InputWorkspace=offset_ws_dict[bank_name], OutputWorkspace=out_offset_ws_name)
            CloneWorkspace(InputWorkspace=mask_ws_dict[bank_name], OutputWorkspace=out_mask_ws_name)
        else:
            # merge
            _merge_partial_offset_mask_workspaces(out_offset_ws_name, offset_ws_dict[bank_name],
                                                  out_mask_ws_name, mask_ws_dict[bank_name])
    # END-FOR

    # Convert to diff calibratin table:  convert the offsets workspace to difc calibration workspace
    calib_ws_name = f'{output_ws_name}_cal'
    ConvertDiffCal(OffsetsWorkspace=out_offset_ws_name,
                   OutputWorkspace=calib_ws_name)

    # Copy value over reference mask and DIFC calibration workspace if
    # 1. some bank is not calibrated
    # 2. reference mask and offset workspaces are provided
    # TODO FIXME - VULCAN's banks name shall be defined as enumerate constants
    vulcan_bank_list = ['Bank1', 'Bank2', 'Bank2']
    for bank_name in vulcan_bank_list:
        # skip calibrated banks
        if bank_name in offset_ws_dict.keys():
            continue

        print('[INFO] Applying {}:{} to {}'.format(ref_calib_ws, bank_name, calib_ws_name))
        if ref_calib_ws:
            copy_bank_wise_offset_values(calib_ws_name, ref_calib_ws, bank_name)
        if ref_mask_ws:
            copy_bank_wise_masks(out_mask_ws_name, ref_mask_ws, bank_name)
            # Apply masks from mask bit to instrument (this is a pure Mantid issue)
            apply_masks(out_mask_ws_name)
    # END-FOR

    return calib_ws_name, out_offset_ws_name, out_mask_ws_name


def calculate_difc(ws, ws_index):
    """Calculate DIFC of one spectrum
    Parameters
    ----------
    ws:
        workspace instance
    ws_index: int
        workspace index from 0
    Returns
    -------
    float
        DIFC
    """
    det_pos = ws.getDetector(ws_index).getPos()
    source_pos = ws.getInstrument().getSource().getPos()
    sample_pos = ws.getInstrument().getSample().getPos()

    source_sample = sample_pos - source_pos
    det_sample = det_pos - sample_pos
    angle = det_sample.angle(source_sample)

    l1 = source_sample.norm()
    l2 = det_sample.norm()

    # DIFC:  ath.sqrt(L1+L2) #\sqrt{L1+L2}
    difc = 252.816 * 2 * np.sin(angle * 0.5) * (l1 + l2)

    return difc


def correct_difc_to_default(idf_difc_vec, cal_difc_vec, difc_tol,
                            start_row_number: int,
                            mask_ws,
                            mask_erroneous_pixels: bool,
                            cal_table: Union[Any, None] = None,
                            difc_col_index: Union[int, None] = None,
                            verbose: bool = False):
    """Process DIFC if calbirated value is out of tolerance
    Parameters
    ----------
    idf_difc_vec: numpy.array
         DIFC calculated from the instrument geometry (engineered)
    cal_difc_vec: numpy.array
        DIFC calculated from the calibration
    cal_table: ~TableWorkspace, None
        calibration table workspace, calibration value table (TableWorkspace)
    start_row_number: int
        starting row number the first element in DIFC vector
    difc_tol: float
        tolerance on the difference between calculated difc and calibrated difc
    difc_col_index: int, None
        column index of the DIFC in the table workspace
    mask_ws: ~MaskWorkspace
        mask workspace
    mask_erroneous_pixels: bool
        if True, mask the pixels with DIFC out of tolerance
    verbose: bool
        If True, print out detailed correction information
    Returns
    -------
    """
    # difference between IDF and calibrated DIFC
    difc_diff_vec = idf_difc_vec - cal_difc_vec

    # go over all the DIFCs
    num_wild_difc = 0
    message = ''
    for index in range(len(difc_diff_vec)):
        if abs(difc_diff_vec[index]) > difc_tol:
            # calibrated DIFC is out of tolerance

            # is it already masked
            if mask_ws.readY(index + start_row_number)[0] < 0.5:
                num_wild_difc += 1
                masked = False
            else:
                masked = True

            # fall back or mask
            if cal_table:
                # fallback DIFC to original
                cal_table.setCell(index + start_row_number, difc_col_index, idf_difc_vec[index])
            elif mask_erroneous_pixels and not masked:
                mask_ws.dataY(start_row_number + index)[0] = 1.

            # error message
            mask_sig = 'Previously masked' if masked else 'Fallback' if cal_table else 'Mask'
            message += '{0}: ws-index = {1}, diff = {2}...  {3}\n' \
                       ''.format(index, index + start_row_number, difc_diff_vec[index], mask_sig)
        # END-IF
    # END-FOR
    print(f'[INFO] Number of DIFC incorrect = {num_wild_difc} out of {cal_difc_vec.shape}')
    if verbose:
        print(f'{message}')

    # Mask detectors
    if mask_erroneous_pixels and num_wild_difc > 0:
        apply_masks(mask_ws)


# TODO - all the hardcoded pixel numbers will be replaced!
def verify_vulcan_difc(ws_name: str,
                       cal_table_name: str,
                       mask_ws_name: str,
                       fallback_incorrect_difc_pixels: bool,
                       mask_incorrect_difc_pixels: bool,
                       output_dir: str):
    """Verify and possibly correct DIFCs if necessary
    Parameters
    ----------
    ws_name
    cal_table_name: str
         name of Calibration workspace (a TableWorkspace)
    mask_ws_name
    fallback_incorrect_difc_pixels: bool
        If calibrated DIFC is obviously wrong, fallback to the engineered value
    mask_incorrect_difc_pixels: bool
        if fallback_incorrect_difc_pixels==False, choice to discard (aka mask) bad pixels
    output_dir: str
        output directory for DIFC
    Returns
    -------
    """
    # Define const parameterr
    diamond_event_ws = mtd[ws_name]
    mask_ws = mtd[mask_ws_name]
    cal_table_ws = mtd[cal_table_name]
    difc_col_index = 1

    # Generate a dictionary for each bank
    bank_info_dict = VULCAN_X_PIXEL_RANGE

    if diamond_event_ws.getNumberHistograms() != VULCAN_X_PIXEL_NUMBER:
        raise NotImplementedError('Bank information dictionary is out of date')

    # Init file
    difc_h5 = h5py.File(os.path.join(output_dir, f'{diamond_event_ws}_DIFC.h5'), 'w')

    for bank_name in ['Bank1', 'Bank2', 'Bank5']:
        # pixel range
        pid_0, pid_f = bank_info_dict[bank_name]
        num_pixels = pid_f - pid_0
        # calculate DIFC from IDF and get calibrated DIFC
        bank_idf_vec = np.ndarray(shape=(num_pixels,), dtype='float')
        bank_cal_vec = np.ndarray(shape=(num_pixels,), dtype='float')
        for irow in range(pid_0, pid_f):
            bank_idf_vec[irow - pid_0] = calculate_difc(diamond_event_ws, irow)
            bank_cal_vec[irow - pid_0] = cal_table_ws.cell(irow, difc_col_index)
        # compare and make report
        difc_diff_vec = bank_cal_vec - bank_idf_vec
        bank_entry = difc_h5.create_group(bank_name)
        # data
        h5_data = np.array([bank_cal_vec, bank_idf_vec, difc_diff_vec]).transpose()
        bank_entry.create_dataset('DIFC_cal_raw_diff', data=h5_data)

        # correct the unphysical (bad) calibrated DIFC to default DIF: Bank1, Bank2, Bank5
        param_dict = {}
        if fallback_incorrect_difc_pixels:
            param_dict['cal_table'] = cal_table_ws
            param_dict['difc_col_index'] = 1

        correct_difc_to_default(bank_idf_vec, bank_cal_vec, difc_tol=20,
                                start_row_number=pid_0,
                                mask_ws=mask_ws, mask_erroneous_pixels=mask_incorrect_difc_pixels,
                                **param_dict)

    # Close file
    difc_h5.close()


def create_groups(vulcan_ws_name=None) -> str:
    """Create group workspace
    """
    # create group workspace
    group_ws_name = 'VULCAN_3Bank_Groups'

    # 3 group mode
    group_ws = CreateGroupingWorkspace(InputWorkspace=vulcan_ws_name,
                                       GroupDetectorsBy='bank',
                                       OutputWorkspace=group_ws_name)

    # sanity check
    assert group_ws

    return group_ws_name


def export_difc(calib_ws_name, out_file_name):
    """
    Export DIFC file
    :param calib_ws_name:
    :param out_file_name:
    :return:
    """
    calib_ws = retrieve_workspace(calib_ws_name)

    wbuf = '{}\n'.format(calib_ws.getColumnNames())
    for ir in range(calib_ws.rowCount()):
        wbuf += '{}   {}   {}\n'.format(calib_ws.cell(ir, 0), calib_ws.cell(ir, 1), calib_ws.cell(ir, 2))

    out_file = open(out_file_name, 'w')
    out_file.write(wbuf)
    out_file.close()


def save_calibration(calib_ws_name: str,
                     mask_ws_name: str,
                     group_ws_name: str,
                     calib_file_prefix: str,
                     output_dir: str,
                     advanced_output: bool = False) -> str:
    """Export calibrated result to calibration file
    Save calibration (calibration table, mask and grouping) to legacy .cal and current .h5 file
    Parameters
    ----------
    calib_ws_name: str
        (DIFC) calibration workspace name
    mask_ws_name
    group_ws_name
    calib_file_prefix
    output_dir: str
        path to output directory
    Returns
    -------
    str
        calibration file name
    """
    # save:  get file name and unlink existing one
    out_file_name = os.path.join(output_dir, calib_file_prefix + '.h5')
    if os.path.exists(out_file_name):
        os.unlink(out_file_name)

    print(f'[SAVING CAL] Mask {mask_ws_name} Y = {np.sum(mtd[mask_ws_name].extractY().flatten())} '
          f'Masked = {mtd[mask_ws_name].getNumberMasked()}')

    # Save for Mantid diffraction calibration file
    if advanced_output:
        SaveNexusProcessed(InputWorkspace=calib_ws_name, Filename=f'{calib_ws_name}.nxs')

    # Save diffraction calibration file
    SaveDiffCal(CalibrationWorkspace=calib_ws_name,
                GroupingWorkspace=group_ws_name,
                MaskWorkspace=mask_ws_name,
                Filename=out_file_name)

    # Save calibration script to python file
    # FIXME - I doubt how many useful information can be saved
    py_name = os.path.join(output_dir, calib_file_prefix + '.py')
    GeneratePythonScript(InputWorkspace=calib_ws_name, Filename=py_name)

    # Save DIFC
    difc_file_name = os.path.join(output_dir, calib_file_prefix + '_difc.dat')
    export_difc(calib_ws_name, difc_file_name)

    return out_file_name


def calibrate_vulcan(diamond_ws: str,
                     cross_correlate_param_dict: Dict[str, CrossCorrelateParameter],
                     calibration_flag: Dict[str, bool],
                     output_dir: str) -> Tuple[str, str]:
    """Main calibration workflow algorithm
    Refer to pyvdrive.script.calibration.vulcan_cal_instruent_calibration.py
    Parameters
    ----------
    diamond_ws_name:
    cross_correlate_param_dict: ~dict
        cross correlation parameters
    calibration_flag: ~dict
        flag to calibrate components
    output_dir:
    Returns
    -------
    ~tuple
        calibration file name, diamond event workspace
    """
    # Check inputs
    diamond_ws_name = str(diamond_ws)
    assert mtd.doesExist(diamond_ws_name), f'Workspace {diamond_ws_name} does not exist'

    # Call workflow algorithm to calibrate VULCAN data by cross-correlation
    r = cross_correlate_vulcan_data(diamond_ws_name,
                                    cross_correlate_param_dict,
                                    calibration_flag,
                                    cc_fit_time=CROSS_CORRELATE_PEAK_FIT_NUMBER,
                                    prefix='1fit')
    offset_ws_dict, mask_ws_dict = r

    # About output
    base_output_ws_name = f'VULCAN_Calibration_{CROSS_CORRELATE_PEAK_FIT_NUMBER}Fit'

    # Merge calibration and masks
    rt = merge_detector_calibration(ref_calib_ws=None,
                                    ref_mask_ws=None,
                                    offset_ws_dict=offset_ws_dict,
                                    mask_ws_dict=mask_ws_dict,
                                    num_banks=3,
                                    output_ws_name=base_output_ws_name)
    calib_ws_name, offset_ws, mask_ws = rt

    # Check, mask or fallback the difference between calibrated and engineered DIFCs
    verify_vulcan_difc(ws_name=diamond_ws_name,
                       cal_table_name=calib_ws_name,
                       mask_ws_name=str(mask_ws),
                       fallback_incorrect_difc_pixels=False,
                       mask_incorrect_difc_pixels=True,
                       output_dir=output_dir)

    # merge calibration result from bank-based cross correlation and  save calibration file
    # Export cross correlated result, DIFC and etc for analysis
    # Generate grouping workspace
    grouping_ws_name = create_groups(diamond_ws_name)

    output_calib_file_name = f'{diamond_ws_name}_Calibration_CC'
    calib_file_name = save_calibration(calib_ws_name=calib_ws_name,
                                       mask_ws_name=str(mask_ws),
                                       group_ws_name=grouping_ws_name,
                                       calib_file_prefix=output_calib_file_name,
                                       output_dir=output_dir)

    return calib_file_name, diamond_ws_name


def cross_correlate_calibrate(input_workspace,
                              cross_correlate_param_dict: Union[None, Dict[str, CrossCorrelateParameter]] = None,
                              bank_calibration_flag: Union[None, Dict[str, bool]] = None,
                              output_dir: str = os.getcwd(),
                              vulcan_x_idf: Union[str, None] = None) -> Tuple[str, str]:
    """
    Default VULCAN-X: when auto reducing, time focus data to pixel 48840 for bank 1 and 2, and 422304 for bank 5.
    those are centers.
    Parameters
    ----------
    diamond_runs: str, ~list
        2 possible inputs: (1) name of diamond MatrixWorkspace (2) list of diamond run numbers or nexus file paths
    cross_correlate_param_dict: ~dict
        cross correlation parameters
    bank_calibration_flag: ~dict, None
        flag to calibrate components
    output_dir
    vulcan_x_idf
    Returns
    -------
    ~tuple
        name of calibration file (generated), name of raw diamond EventWorkspace
    """
    if str(input_workspace) not in mtd:
        raise RuntimeError('Workspace "{}" does not exist'.format(str(input_workspace)))

    # Set up default
    if cross_correlate_param_dict is None:
        cross_correlate_param_dict = default_cross_correlation_setup()

    # Set up process calibration
    bank_calibration_flag = process_calibration_flag(cross_correlate_param_dict, bank_calibration_flag)

    # Do cross correlation calibration
    cal_file_name, diamond_ws_name = calibrate_vulcan(input_workspace,
                                                      cross_correlate_param_dict,
                                                      bank_calibration_flag,
                                                      output_dir=output_dir)

    return cal_file_name, diamond_ws_name


def cross_correlation_in_tubes():
    # peak position in d-Spacing
    # Tube 1
    tube1_cc_param = CrossCorrelateParameter('Tube1', reference_peak_position=1.2614, reference_peak_width=0.04,
                                             reference_ws_index=256,
                                             cross_correlate_number=80,
                                             bin_step=-0.0003, start_ws_index=0, end_ws_index=512)
    boundary_index = 512
    # Rest of 8-Pack 1:center = 2 * 512 + 256
    pack1_cc_param = CrossCorrelateParameter('Bank1', reference_peak_position=1.2614, reference_peak_width=0.04,
                                             reference_ws_index=2 * 512 + 256,
                                             cross_correlate_number=80,
                                             bin_step=-0.0003, start_ws_index=boundary_index, end_ws_index=512 * 4)
    boundary_index = 512 * 4
    # Rest of bank 1
    bank1_cc_param = CrossCorrelateParameter('Bank1', reference_peak_position=1.2614, reference_peak_width=0.04,
                                             reference_ws_index=40704, cross_correlate_number=80,
                                             bin_step=-0.0003, start_ws_index=boundary_index, end_ws_index=512 * 160)
    # Bank 2
    bank2_cc_param = CrossCorrelateParameter('Bank2', reference_peak_position=1.2614, reference_peak_width=0.04,
                                             reference_ws_index=40704, cross_correlate_number=80,
                                             bin_step=-0.0003, start_ws_index=512 * 160, end_ws_index=512 * 320)
    # Bank 5
    bank5_cc_param = CrossCorrelateParameter('Bank3', reference_peak_position=1.07577, reference_peak_width=0.01,
                                             reference_ws_index=182528, cross_correlate_number=20,
                                             bin_step=-0.0003, start_ws_index=512 * 320, end_ws_index=512 * (320 + 72))

    # do cross correlation
    cross_correlate_param_dict = {'Tube1': tube1_cc_param,
                                  'Pack1': pack1_cc_param,
                                  'Bank1': bank1_cc_param,
                                  'Bank2': bank2_cc_param,
                                  'Bank5': bank5_cc_param}

    return cross_correlate_param_dict


# TODO should be trapped in main check
#if __name__ == '__main__':
dia_runs = [192226, 192227] #, 192228, 192229, 192230]
diamond_ws = load_and_crop(runnumbers=dia_runs, bin_step=-0.0003, bad_pulse_threashold=0, reload_instrument=True, convert_to_dspace=True)
#cross_correlate_calibrate called in calibrate_vulcan_x.pyL298
tube_cc_plan = cross_correlation_in_tubes()
cc_calib_file, diamond_ws_name = cross_correlate_calibrate(diamond_ws, cross_correlate_param_dict = tube_cc_plan)
print('file:', cc_calib_file)
#create grouping for sub-sections of the instrument
#AlignAndFocusPowder using that information
#peak_position_calibrate in calibrate_vulcan_x.pyL319 (does this combine the two parts of the DIFC calculation?)
#create the actual grouping workspace
#SaveDIFC
