// Mantid Repository : https://github.com/mantidproject/mantid
//
// Copyright &copy; 2018 ISIS Rutherford Appleton Laboratory UKRI,
//   NScD Oak Ridge National Laboratory, European Spallation Source,
//   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
// SPDX - License - Identifier: GPL - 3.0 +
/*
 * ClusterIntegrationBaseTest.h
 *
 *  Created on: May 23, 2014
 *      Author: spu92482
 */

#pragma once

#include "MantidAPI/AlgorithmManager.h"
#include "MantidAPI/Workspace.h"
#include "MantidDataObjects/PeaksWorkspace.h"
#include "MantidFrameworkTestHelpers/ComponentCreationHelper.h"
#include "MantidFrameworkTestHelpers/MDEventsTestHelper.h"
#include "MantidFrameworkTestHelpers/WorkspaceCreationHelper.h"
#include "MantidGeometry/MDGeometry/HKL.h"
#include "MantidKernel/UnitLabelTypes.h"
#include "MantidKernel/V3D.h"
#include <cxxtest/TestSuite.h>

#include <boost/tuple/tuple.hpp>
#include <set>

using namespace Mantid::API;
using namespace Mantid::Kernel;
using namespace Mantid::DataObjects;
using namespace Mantid::Geometry;

// Helper typedef
using MDHistoPeaksWSTuple = boost::tuple<IMDHistoWorkspace_sptr, PeaksWorkspace_sptr>;
// Helper typedef
using MDEventPeaksWSTuple = boost::tuple<IMDEventWorkspace_sptr, PeaksWorkspace_sptr>;

class ClusterIntegrationBaseTest {
protected:
  // Helper to determine if container holds a value.
  template <typename Container>
  bool does_contain(const Container &container, const typename Container::value_type &value) {
    return container.end() != std::find(container.begin(), container.end(), value);
  }

  // Add a fake peak to an MDEventWorkspace
  void add_fake_md_peak(const IMDEventWorkspace_sptr &mdws, const size_t &nEvents, const double &h, const double &k,
                        const double &l, const double &radius) {
    auto fakeMDEventDataAlg = AlgorithmManager::Instance().createUnmanaged("FakeMDEventData");
    fakeMDEventDataAlg->setChild(true);
    fakeMDEventDataAlg->initialize();
    fakeMDEventDataAlg->setProperty("InputWorkspace", mdws);
    std::stringstream peakstream;
    peakstream << nEvents << ", " << h << ", " << k << ", " << l << ", " << radius;
    fakeMDEventDataAlg->setPropertyValue("PeakParams", peakstream.str());
    fakeMDEventDataAlg->execute();
  }

  MDEventPeaksWSTuple make_peak_and_mdew(const std::vector<V3D> &hklValuesVec, const double &min, const double &max,
                                         const std::vector<double> &peakRadiusVec,
                                         const std::vector<size_t> &nEventsInPeakVec) {
    Instrument_sptr inst = ComponentCreationHelper::createTestInstrumentRectangular(1, 100, 0.05);

    // --- Make a fake md histo workspace ---
    auto mdworkspaceAlg = AlgorithmManager::Instance().createUnmanaged("CreateMDWorkspace");
    mdworkspaceAlg->setChild(true);
    mdworkspaceAlg->initialize();
    mdworkspaceAlg->setProperty("Dimensions", 3);
    std::vector<double> extents = {min, max, min, max, min, max};
    mdworkspaceAlg->setProperty("Extents", extents);
    mdworkspaceAlg->setPropertyValue("Names", "H,K,L");
    std::string units = Mantid::Kernel::Units::Symbol::RLU.ascii() + "," + Mantid::Kernel::Units::Symbol::RLU.ascii() +
                        "," + Mantid::Kernel::Units::Symbol::RLU.ascii();
    mdworkspaceAlg->setProperty("Units", units);
    std::string frames =
        Mantid::Geometry::HKL::HKLName + "," + Mantid::Geometry::HKL::HKLName + "," + Mantid::Geometry::HKL::HKLName;
    mdworkspaceAlg->setProperty("Frames", frames);
    mdworkspaceAlg->setPropertyValue("OutputWorkspace", "IntegratePeaksMDTest_MDEWS");
    mdworkspaceAlg->execute();
    Workspace_sptr temp = mdworkspaceAlg->getProperty("OutputWorkspace");
    IMDEventWorkspace_sptr mdws = std::dynamic_pointer_cast<IMDEventWorkspace>(temp);

    // --- Set speical coordinates on fake mdworkspace --
    auto coordsAlg = AlgorithmManager::Instance().createUnmanaged("SetSpecialCoordinates");
    coordsAlg->setChild(true);
    coordsAlg->initialize();
    coordsAlg->setProperty("InputWorkspace", mdws);
    coordsAlg->setProperty("SpecialCoordinates", "HKL");
    coordsAlg->execute();

    // --- Make a fake PeaksWorkspace ---
    PeaksWorkspace_sptr peakWS(new PeaksWorkspace());
    peakWS->setInstrument(inst);

    // --- Set speical coordinates on fake PeaksWorkspace --
    coordsAlg = AlgorithmManager::Instance().createUnmanaged("SetSpecialCoordinates");
    coordsAlg->setChild(true);
    coordsAlg->initialize();
    coordsAlg->setProperty("InputWorkspace", peakWS);
    coordsAlg->setProperty("SpecialCoordinates", "HKL");
    coordsAlg->execute();

    for (size_t i = 0; i < hklValuesVec.size(); ++i) {
      Peak peak(inst, 15050, 1.0);

      const double &h = hklValuesVec[i][0];
      const double &k = hklValuesVec[i][1];
      const double &l = hklValuesVec[i][2];

      peak.setHKL(h, k, l);
      peakWS->addPeak(peak);

      add_fake_md_peak(mdws, nEventsInPeakVec[i], h, k, l, peakRadiusVec[i]);
    }

    return MDEventPeaksWSTuple(mdws, peakWS);
  }

  // Make a fake peaks workspace and corresponding mdhistoworkspace and return
  // both
  MDHistoPeaksWSTuple make_peak_and_md_ws(const std::vector<V3D> &hklValuesVec, const double &min, const double &max,
                                          const std::vector<double> &peakRadiusVec,
                                          const std::vector<size_t> &nEventsInPeakVec, const size_t &nBins = 20) {

    MDEventPeaksWSTuple mdew_peak = make_peak_and_mdew(hklValuesVec, min, max, peakRadiusVec, nEventsInPeakVec);

    auto binMDAlg = AlgorithmManager::Instance().createUnmanaged("BinMD");
    binMDAlg->setChild(true);
    binMDAlg->initialize();
    binMDAlg->setProperty("InputWorkspace", mdew_peak.get<0>());
    binMDAlg->setPropertyValue("OutputWorkspace", "output_ws");
    binMDAlg->setProperty("AxisAligned", true);

    std::stringstream dimensionstring;
    dimensionstring << "," << min << ", " << max << "," << nBins;

    binMDAlg->setPropertyValue("AlignedDim0", "H" + dimensionstring.str());
    binMDAlg->setPropertyValue("AlignedDim1", "K" + dimensionstring.str());
    binMDAlg->setPropertyValue("AlignedDim2", "L" + dimensionstring.str());
    binMDAlg->execute();

    Workspace_sptr temp = binMDAlg->getProperty("OutputWorkspace");
    IMDHistoWorkspace_sptr outMDWS = std::dynamic_pointer_cast<IMDHistoWorkspace>(temp);
    return MDHistoPeaksWSTuple(outMDWS, mdew_peak.get<1>());
  }

  // Make a fake peaks workspace and corresponding mdhistoworkspace and return
  // both
  MDEventPeaksWSTuple make_peak_and_mdew(const std::vector<V3D> &hklValues, const double &min, const double &max,
                                         const double &peakRadius = 1, const size_t nEventsInPeak = 1000) {
    std::vector<size_t> nEventsInPeakVec(hklValues.size(), nEventsInPeak);
    std::vector<double> peakRadiusVec(hklValues.size(), peakRadius);
    return make_peak_and_mdew(hklValues, min, max, peakRadiusVec, nEventsInPeakVec);
  }

  // Make a fake peaks workspace and corresponding mdhistoworkspace and return
  // both
  MDHistoPeaksWSTuple make_peak_and_md_ws(const std::vector<V3D> &hklValues, const double &min, const double &max,
                                          const double &peakRadius = 1, const size_t nEventsInPeak = 1000,
                                          const size_t &nBins = 20) {
    std::vector<size_t> nEventsInPeakVec(hklValues.size(), nEventsInPeak);
    std::vector<double> peakRadiusVec(hklValues.size(), peakRadius);
    return make_peak_and_md_ws(hklValues, min, max, peakRadiusVec, nEventsInPeakVec, nBins);
  }

public:
  virtual ~ClusterIntegrationBaseTest() {}
};
