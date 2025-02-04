// Mantid Repository : https://github.com/mantidproject/mantid
//
// Copyright &copy; 2018 ISIS Rutherford Appleton Laboratory UKRI,
//   NScD Oak Ridge National Laboratory, European Spallation Source,
//   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
// SPDX - License - Identifier: GPL - 3.0 +
#include "MantidQtWidgets/Common/PluginLibraries.h"
#include "MantidKernel/ConfigService.h"
#include "MantidKernel/LibraryManager.h"
#include "MantidKernel/Strings.h"

#include <QtGlobal>

using Mantid::Kernel::ConfigService;
using Mantid::Kernel::LibraryManager;
using Mantid::Kernel::LibraryManagerImpl;

namespace MantidQt::API {

/**
 * Retrieve the path to some qt-related plugins from the mantid configuration
 * If the value contains %V then this sequence is replaced with the major
 * version of Qt
 * @param key The name of a key in the Mantid config
 * @return The value of the key
 */
std::string qtPluginPathFromCfg(const std::string &key) {
  static std::string qtMajorVersion;
  static std::string qtTag("%V");
  if (qtMajorVersion.empty()) {
    qtMajorVersion = std::string(QT_VERSION_STR, 0, 1);
  }
  using Mantid::Kernel::Strings::replace;
  return replace(ConfigService::Instance().getString(key), qtTag, qtMajorVersion);
}

/**
 * Load all plugins from the path specified by the given configuration key.
 * @param key The name of a key in the Mantid config. It's value may contain
 * %V to specify the Qt version
 * @return The number of libraries successfully loaded
 */
int loadPluginsFromCfgPath(const std::string &key) { return loadPluginsFromPath(qtPluginPathFromCfg(key)); }

/**
 * Load all plugins from the path specified.
 * @return The number of libraries successfully loaded
 */
int loadPluginsFromPath(const std::string &path) {
// We must *NOT* load plugins compiled against a different version of Qt
// so we set exclude flags by Qt version.
#if (QT_VERSION < QT_VERSION_CHECK(5, 0, 0))
  static std::vector<std::string> excludes{"Qt5"};
#else
  static std::vector<std::string> excludes{"Qt4"};
#endif
  return LibraryManager::Instance().openLibraries(path, LibraryManagerImpl::NonRecursive, excludes);
}
} // namespace MantidQt::API
