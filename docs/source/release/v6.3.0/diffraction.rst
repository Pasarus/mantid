===================
Diffraction Changes
===================

.. contents:: Table of Contents
   :local:

.. warning:: **Developers:** Sort changes under appropriate heading
    putting new features at the top of the section, followed by
    improvements, followed by bug fixes.

Powder Diffraction
------------------
- `GetDetOffsetsMultiPeaks`, which is deprecate since v6.2.0, is removed.
- `CalibrateRectangularDetectors`, which is deprecate since v6.2.0, is removed. And system test CalibrateRectangularDetectors_Test is removed.
- Extending :ref:`MultipleScatteringCorrection <algm-MultipleScatteringCorrection>` to the sample and container case.
- `absorptioncorrutils` now have the capability to calculate effective absorption correction (considering both absorption and multiple scattering).
- Both :ref:`MultipleScatteringCorrection <algm-MultipleScatteringCorrection>` and :ref:`PaalmanPingsAbsorptionCorrection <algm-PaalmanPingsAbsorptionCorrection>` can use a different element size for container now.

Bugfixes
########
- For processing vanadium run, we don't want to find environment automatically in :ref:`SetSampleFromLogs <algm-SetSampleFromLogs>`.
- Restored behavior in :ref:`ConvertUnits <algm-ConvertUnits>` where negative time-of-flight converts to negative d-spacing when ``DIFA==0``
- Identification in :ref:`AlignComponents <algm-AlignComponents>` of the first and last detector-ID for an instrument component with unsorted detector-ID's.

Engineering Diffraction
-----------------------

Single Crystal Diffraction
--------------------------
- Existing :ref:`PolDiffILLReduction <algm-PolDiffILLReduction>` and :ref:`D7AbsoluteCrossSections <algm-D7AbsoluteCrossSections>` can now reduce and properly normalise single-crystal data for the D7 ILL instrument.
- Enabling :ref:`SCDCalibratePanels <algm-SCDCalibratePanels-v2>` to calibrate each detector bank's size if it is a rectagular detector optionally.

:ref:`Release 6.3.0 <v6.3.0>`
