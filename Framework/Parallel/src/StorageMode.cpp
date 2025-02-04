// Mantid Repository : https://github.com/mantidproject/mantid
//
// Copyright &copy; 2018 ISIS Rutherford Appleton Laboratory UKRI,
//   NScD Oak Ridge National Laboratory, European Spallation Source,
//   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
// SPDX - License - Identifier: GPL - 3.0 +
#include "MantidParallel/StorageMode.h"

namespace Mantid::Parallel {

/// Returns a human-readable string representation of a StorageMode.
std::string toString(StorageMode mode) {
  switch (mode) {
  case StorageMode::Cloned:
    return "Parallel::StorageMode::Cloned";
  case StorageMode::Distributed:
    return "Parallel::StorageMode::Distributed";
  case StorageMode::MasterOnly:
    return "Parallel::StorageMode::MasterOnly";
  default:
    return "Parallel::StorageMode::<undefined>";
  }
}

/// Returns a human-readable string representation of a StorageMode map.
std::string toString(const std::map<std::string, StorageMode> &map) {
  std::string ret("\n");
  for (const auto &item : map)
    ret.append(item.first + " " + toString(item.second) + "\n");
  return ret;
}

/// Returns a StorageMode for a human-readable string representation.
StorageMode fromString(const std::string &mode) {
  if (mode == "Parallel::StorageMode::Cloned")
    return StorageMode::Cloned;
  if (mode == "Parallel::StorageMode::Distributed")
    return StorageMode::Distributed;
  if (mode == "Parallel::StorageMode::MasterOnly")
    return StorageMode::MasterOnly;
  throw std::invalid_argument("Parallel::fromString could not convert provided input into a "
                              "Parallel::StorageMode.");
}

} // namespace Mantid::Parallel
