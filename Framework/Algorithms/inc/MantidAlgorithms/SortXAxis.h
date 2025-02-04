// Mantid Repository : https://github.com/mantidproject/mantid
//
// Copyright &copy; 2018 ISIS Rutherford Appleton Laboratory UKRI,
//   NScD Oak Ridge National Laboratory, European Spallation Source,
//   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
// SPDX - License - Identifier: GPL - 3.0 +
#pragma once

#include "MantidAPI/Algorithm.h"
#include "MantidAlgorithms/DllConfig.h"

namespace Mantid {
namespace Algorithms {

/**
 * @brief SortXAxis will take Histogram or Point data and reorder it based on
 * the X Axis' values, whilst maintaining it's Dx, Y and E axis relative values.
 * @author Samuel Jones
 * @version 2.0
 * @date 07-2018
 * @copyright GNU General Public License
 */

class MANTID_ALGORITHMS_DLL SortXAxis : public API::Algorithm {
public:
  const std::string name() const override;
  int version() const override;
  const std::string category() const override;
  const std::string summary() const override;

private:
  void init() override;
  void exec() override;
  std::vector<std::size_t> createIndexes(const size_t);

  void sortIndicesByX(std::vector<std::size_t> &workspaceIndices, const std::string &order,
                      const Mantid::API::MatrixWorkspace &inputWorkspace, unsigned int specNum);

  void copyYandEToOutputWorkspace(std::vector<std::size_t> &workspaceIndices,
                                  const Mantid::API::MatrixWorkspace &inputWorkspace,
                                  Mantid::API::MatrixWorkspace &outputWorkspace, unsigned int SpecNum,
                                  bool isAProperHistogram);

  void copyXandDxToOutputWorkspace(const std::vector<std::size_t> &workspaceIndices,
                                   const Mantid::API::MatrixWorkspace &inputWorkspace,
                                   Mantid::API::MatrixWorkspace &outputWorkspace, unsigned int specNum);

  void copyToOutputWorkspace(std::vector<std::size_t> &workspaceIndices,
                             const Mantid::API::MatrixWorkspace &inputWorkspace,
                             Mantid::API::MatrixWorkspace &outputWorkspace, unsigned int specNum,
                             bool isAProperHistogram);

  bool determineIfHistogramIsValid(const Mantid::API::MatrixWorkspace &inputWorkspace);
};

} // namespace Algorithms
} // namespace Mantid
