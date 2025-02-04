// Mantid Repository : https://github.com/mantidproject/mantid
//
// Copyright &copy; 2018 ISIS Rutherford Appleton Laboratory UKRI,
//   NScD Oak Ridge National Laboratory, European Spallation Source,
//   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
// SPDX - License - Identifier: GPL - 3.0 +
#pragma once

#include "MantidAPI/Algorithm.h"
#include "MantidAPI/ExperimentInfo.h"
#include "MantidGeometry/Crystal/SymmetryOperationFactory.h"
#include "MantidMDAlgorithms/DllConfig.h"
#include "MantidMDAlgorithms/SlicingAlgorithm.h"

namespace Mantid {
namespace MDAlgorithms {

/** MDNormalization : Bin single crystal diffraction or direct geometry
 * inelastic data and calculate the corresponding statistical weight
 */
class MANTID_MDALGORITHMS_DLL MDNorm : public API::Algorithm {
public:
  MDNorm();
  const std::string name() const override;
  int version() const override;
  const std::string category() const override;
  const std::string summary() const override;
  const std::vector<std::string> seeAlso() const override {
    return {"CropWorkspaceForMDNorm", "MDNormSCD", "MDNormDirectSC", "RecalculateTrajectoriesExtents"};
  }

private:
  void init() override;
  void exec() override;
  void validateBinningForTemporaryDataWorkspace(const std::map<std::string, std::string> &,
                                                const Mantid::API::IMDHistoWorkspace_sptr &);
  std::map<std::string, std::string> validateInputs() override final;
  std::string QDimensionName(std::vector<double> projection);
  std::string QDimensionNameQSample(int i);
  std::map<std::string, std::string> getBinParameters();
  void createNormalizationWS(const DataObjects::MDHistoWorkspace &dataWS);
  void createBackgroundNormalizationWS(const DataObjects::MDHistoWorkspace &dataWS);

  /// Bin(MD) input MDE workspace
  DataObjects::MDHistoWorkspace_sptr binInputWS(const std::vector<Geometry::SymmetryOperation> &symmetryOps);

  /// Bin(MD) input Background workspace
  DataObjects::MDHistoWorkspace_sptr binBackgroundWS(const std::vector<Geometry::SymmetryOperation> &symmetryOps);

  /// build symmetry matrix
  Mantid::Kernel::DblMatrix buildSymmetryMatrix(const Geometry::SymmetryOperation &so);
  void determineBasisVector(const size_t &qindex, const std::string &value, const Kernel::DblMatrix &Qtransform,
                            std::vector<double> &projection, std::stringstream &basisVector,
                            std::vector<size_t> &qDimensionIndices);
  inline void setQUnit(const std::vector<size_t> &qDimensionIndices,
                       const Mantid::DataObjects::MDHistoWorkspace_sptr &outputMDHWS);

  std::vector<coord_t> getValuesFromOtherDimensions(bool &skipNormalization, uint16_t expInfoIndex = 0) const;

  void cacheDimensionXValues();
  void calculateNormalization(const std::vector<coord_t> &otherValues, const Geometry::SymmetryOperation &so,
                              uint16_t expInfoIndex, size_t soIndex);

  void calculateIntersections(std::vector<std::array<double, 4>> &intersections, const double theta, const double phi,
                              const Kernel::DblMatrix &transform, double lowvalue, double highvalue);

  void calcIntegralsForIntersections(const std::vector<double> &xValues, const API::MatrixWorkspace &integrFlux,

                                     size_t sp, std::vector<double> &yValues);

  void calcDiffractionIntersectionIntegral(std::vector<std::array<double, 4>> &intersections,
                                           std::vector<double> &xValues, std::vector<double> &yValues,
                                           const API::MatrixWorkspace &integrFlux, const size_t &wsIdx);

  Mantid::Kernel::DblMatrix calQTransform(const Mantid::API::ExperimentInfo &currentExpInfo,
                                          const Geometry::SymmetryOperation &so);

  void calcSingleDetectorNorm(const std::vector<std::array<double, 4>> &intersections, const double &solid,
                              std::vector<double> &yValues, const size_t &vmdDims, std::vector<coord_t> &pos,
                              std::vector<coord_t> &posNew, std::vector<std::atomic<signal_t>> &signalArray,
                              const double &solidBkgd, std::vector<std::atomic<signal_t>> &bkgdSignalArray);

  API::IMDWorkspace_sptr divideMD(const API::IMDHistoWorkspace_sptr &lhs, const API::IMDHistoWorkspace_sptr &rhs,
                                  const std::string &outputwsname, const double &startProgress,
                                  const double &endProgress);

  /// Normalization workspace
  DataObjects::MDHistoWorkspace_sptr m_normWS;
  DataObjects::MDHistoWorkspace_sptr m_bkgdNormWS;
  /// Input workspace
  API::IMDEventWorkspace_sptr m_inputWS;
  /// Input background workspace
  API::IMDEventWorkspace_sptr m_backgroundWS;

  /// flag for reciprocal lattice units
  bool m_isRLU;
  /// The projection vectors
  std::vector<double> m_Q0Basis{1., 0., 0.}, m_Q1Basis{0., 1., 0.}, m_Q2Basis{0., 0., 1.};
  /// UB matrix
  Mantid::Kernel::DblMatrix m_UB;
  /// W matrix
  Mantid::Kernel::DblMatrix m_W;
  /** matrix for transforming from intersections to positions in the
  normalization workspace */
  Mantid::Kernel::Matrix<coord_t> m_transformation;
  /// cached X values along dimensions h,k,l. dE
  std::vector<double> m_hX, m_kX, m_lX, m_eX;
  /// index of h,k,l, dE dimensions in the output workspaces
  size_t m_hIdx, m_kIdx, m_lIdx, m_eIdx;
  /// number of experimentInfo objects
  size_t m_numExptInfos;
  /// number of symmetry operations
  size_t m_numSymmOps;
  /// Cached value of incident energy dor direct geometry
  double m_Ei;
  /// Flag indicating if the input workspace is from diffraction
  bool m_diffraction;
  /// Flag to accumulate normalization
  bool m_accumulate;
  /// Flag to indicate that the energy dimension is integrated
  bool m_dEIntegrated;
  /// Sample position
  Kernel::V3D m_samplePos;
  /// Beam direction
  Kernel::V3D m_beamDir;
  /// ki-kf for Inelastic convention; kf-ki for Crystallography convention
  std::string convention;
};

} // namespace MDAlgorithms
} // namespace Mantid
