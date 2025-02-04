// Mantid Repository : https://github.com/mantidproject/mantid
//
// Copyright &copy; 2018 ISIS Rutherford Appleton Laboratory UKRI,
//   NScD Oak Ridge National Laboratory, European Spallation Source,
//   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
// SPDX - License - Identifier: GPL - 3.0 +
#pragma once

#include "MantidAPI/FrameworkManager.h"
#include "MantidDataObjects/LeanElasticPeaksWorkspace.h"
#include "MantidDataObjects/PeaksWorkspace.h"
#include "MantidFrameworkTestHelpers/ComponentCreationHelper.h"
#include "MantidFrameworkTestHelpers/WorkspaceCreationHelper.h"
#include "MantidKernel/PropertyWithValue.h"
#include "MantidMDAlgorithms/FindPeaksMD.h"

#include <cxxtest/TestSuite.h>

using namespace Mantid::API;
using namespace Mantid::MDAlgorithms;
using namespace Mantid::DataObjects;
using Mantid::Geometry::Instrument_sptr;
using Mantid::Kernel::PropertyWithValue;

//-------------------------------------------------------------------------------
/** Create the (blank) MDEW */
static void createMDEW() {
  // ---- Start with empty MDEW ----
  FrameworkManager::Instance().exec("CreateMDWorkspace", 18, "Dimensions", "3", "EventType", "MDEvent", "Extents",
                                    "-10,10,-10,10,-10,10", "Names", "Q_lab_x,Q_lab_y,Q_lab_z", "Units", "-,-,-",
                                    "SplitInto", "5", "SplitThreshold", "20", "MaxRecursionDepth", "15",
                                    "OutputWorkspace", "MDWS");

  // Give it an instrument
  Instrument_sptr inst = ComponentCreationHelper::createTestInstrumentRectangular2(1, 100, 0.05);
  IMDEventWorkspace_sptr ws;
  TS_ASSERT_THROWS_NOTHING(ws = AnalysisDataService::Instance().retrieveWS<IMDEventWorkspace>("MDWS"));
  ExperimentInfo_sptr ei(new ExperimentInfo());
  ei->setInstrument(inst);
  // Give it a run number
  ei->mutableRun().addProperty(new PropertyWithValue<std::string>("run_number", "12345"), true);
  ws->addExperimentInfo(ei);
}

//-------------------------------------------------------------------------------
/** Add a fake peak */
static void addPeak(size_t num, double x, double y, double z, double radius) {
  std::ostringstream mess;
  mess << num / 2 << ", " << x << ", " << y << ", " << z << ", " << radius;
  FrameworkManager::Instance().exec("FakeMDEventData", 4, "InputWorkspace", "MDWS", "PeakParams", mess.str().c_str());

  // Add a center with more events (half radius, half the total), to create a
  // "peak"
  std::ostringstream mess2;
  mess2 << num / 2 << ", " << x << ", " << y << ", " << z << ", " << radius / 2;
  FrameworkManager::Instance().exec("FakeMDEventData", 4, "InputWorkspace", "MDWS", "PeakParams", mess2.str().c_str());
}

//=====================================================================================
// Functional Tests
//=====================================================================================
class FindPeaksMDTest : public CxxTest::TestSuite {
public:
  void test_Init() {
    FindPeaksMD alg;
    TS_ASSERT_THROWS_NOTHING(alg.initialize())
    TS_ASSERT(alg.isInitialized())
  }

  void do_test(bool deleteWS, int MaxPeaks, int expectedPeaks, bool AppendPeaks = false, bool histo = false,
               int edge = 0) {
    // Name of the output workspace.
    std::string outWSName("peaksFound");

    // Make the fake data
    createMDEW();
    addPeak(100, 1, 2, 3, 0.1);
    addPeak(300, 4, 5, 6, 0.2);
    addPeak(500, -5, -5, 5, 0.2);
    // This peak will be rejected as non-physical
    addPeak(500, -5, -5, -5, 0.2);

    // Convert to a MDHistoWorkspace on option
    if (histo) {
      FrameworkManager::Instance().exec("BinMD", 14, "AxisAligned", "1", "AlignedDim0", "Q_lab_x,-10,10,100",
                                        "AlignedDim1", "Q_lab_y,-10,10,100", "AlignedDim2", "Q_lab_z,-10,10,100",
                                        "IterateEvents", "1", "InputWorkspace", "MDWS", "OutputWorkspace", "MDWS");
    }

    FindPeaksMD alg;
    TS_ASSERT_THROWS_NOTHING(alg.initialize())
    TS_ASSERT(alg.isInitialized())
    TS_ASSERT_THROWS_NOTHING(alg.setPropertyValue("InputWorkspace", "MDWS"));
    TS_ASSERT_THROWS_NOTHING(alg.setPropertyValue("OutputWorkspace", outWSName));
    TS_ASSERT_THROWS_NOTHING(alg.setPropertyValue("DensityThresholdFactor", "2.0"));
    TS_ASSERT_THROWS_NOTHING(alg.setPropertyValue("PeakDistanceThreshold", "0.7"));
    TS_ASSERT_THROWS_NOTHING(alg.setProperty("MaxPeaks", int64_t(MaxPeaks)));
    TS_ASSERT_THROWS_NOTHING(alg.setProperty("AppendPeaks", AppendPeaks));
    TS_ASSERT_THROWS_NOTHING(alg.setProperty("EdgePixels", edge));

    TS_ASSERT_THROWS_NOTHING(alg.execute(););
    TS_ASSERT(alg.isExecuted());

    // Retrieve the workspace from data service.
    PeaksWorkspace_sptr ws;
    TS_ASSERT_THROWS_NOTHING(ws = AnalysisDataService::Instance().retrieveWS<PeaksWorkspace>(outWSName));
    TS_ASSERT(ws);
    if (!ws)
      return;
    if (edge > 0) {
      TS_ASSERT_EQUALS(ws->getNumberPeaks(), 0);
      return;
    }
    // Should find 3 peaks.
    TS_ASSERT_EQUALS(ws->getNumberPeaks(), 1);
    if (ws->getNumberPeaks() != expectedPeaks)
      return;
    // Stop checking for the AppendPeaks case. This is good enough.
    if (AppendPeaks)
      return;

    // The order of the peaks found is a little random because it depends on the
    // way the boxes were sorted...
    TS_ASSERT_DELTA(ws->getPeak(0).getQLabFrame()[0], -5.0, 0.20);
    TS_ASSERT_DELTA(ws->getPeak(0).getQLabFrame()[1], -5.0, 0.20);
    TS_ASSERT_DELTA(ws->getPeak(0).getQLabFrame()[2], 5.0, 0.20);
    TS_ASSERT_EQUALS(ws->getPeak(0).getRunNumber(), 12345);
    // Bin count = density of the box / 1e6
    double BinCount = ws->getPeak(0).getBinCount();
    if (histo) {
      TS_ASSERT_DELTA(BinCount, 0.0102, 0.001);
    } else {
      TS_ASSERT_DELTA(BinCount, 7., 001000.);
    }

    if (MaxPeaks > 1) {
      TS_ASSERT_DELTA(ws->getPeak(1).getQLabFrame()[0], 4.0, 0.11);
      TS_ASSERT_DELTA(ws->getPeak(1).getQLabFrame()[1], 5.0, 0.11);
      TS_ASSERT_DELTA(ws->getPeak(1).getQLabFrame()[2], 6.0, 0.11);

      TS_ASSERT_DELTA(ws->getPeak(2).getQLabFrame()[0], 1.0, 0.11);
      TS_ASSERT_DELTA(ws->getPeak(2).getQLabFrame()[1], 2.0, 0.11);
      TS_ASSERT_DELTA(ws->getPeak(2).getQLabFrame()[2], 3.0, 0.11);
    }

    if (deleteWS) {
      // Remove workspace from the data service.
      AnalysisDataService::Instance().remove(outWSName);
    }
    AnalysisDataService::Instance().remove("MDWS");
  }

  /** Running the algo twice with same output workspace = replace the output,
   * don't append */
  void test_exec_twice_replaces_workspace() {
    do_test(false, 100, 3);
    do_test(true, 100, 3);
  }

  /** Run normally */
  void test_exec() { do_test(true, 100, 3); }

  /** Run normally, but limit to 1 peak */
  void test_exec_withMaxPeaks() { do_test(true, 1, 1); }

  /** Run twice and append to the peaks workspace*/
  void test_exec_AppendPeaks() {
    do_test(false, 100, 3);
    // do_test(true, 100, 6, true /* Append */);
  }

  void test_exec_gives_PeaksWorkspace_Containing_DetectorIDs_That_Form_Part_Of_Peak() {
    do_test(false, 100, 3);

    auto peaksWS = AnalysisDataService::Instance().retrieveWS<PeaksWorkspace>("peaksFound");

    const auto &peaks = peaksWS->getPeaks();
    const Mantid::DataObjects::Peak &peak1 = peaks[0];
    const auto &detIDs1 = peak1.getContributingDetIDs();
    TS_ASSERT_EQUALS(7, detIDs1.size());

    // const Mantid::DataObjects::Peak & peak2 = peaks[1];
    // const auto & detIDs2 = peak2.getContributingDetIDs();
    // TS_ASSERT_EQUALS(0, detIDs2.size());

    AnalysisDataService::Instance().remove("peaksFound");
  }

  /** Run on MDHistoWorkspace */
  void test_exec_histo() { do_test(true, 100, 3, false, true /*histo conversion*/); }

  /** Run on MDHistoWorkspace, but limit to 1 peak */
  void test_exec_histo_withMaxPeaks() { do_test(true, 1, 1, false, true /*histo conversion*/); }

  /** Test edge */
  void test_exec_edge() { do_test(true, 100, 3, false, false, 100 /*edge pixels*/); }

  /**Test number of event normalization selection fails for MDHistoWorkspace */
  void test_that_number_of_event_normalization_selection_throws_when_MDHistoWorkspace_is_selected() {
    // Create an MDHistoWorkspace
    createMDEW();
    addPeak(100, 1, 2, 3, 0.1);
    FrameworkManager::Instance().exec("BinMD", 14, "AxisAligned", "1", "AlignedDim0", "Q_lab_x,-10,10,100",
                                      "AlignedDim1", "Q_lab_y,-10,10,100", "AlignedDim2", "Q_lab_z,-10,10,100",
                                      "IterateEvents", "1", "InputWorkspace", "MDWS", "OutputWorkspace", "MDWS");

    FindPeaksMD alg;
    alg.setRethrows(true);
    TS_ASSERT_THROWS_NOTHING(alg.initialize());
    TS_ASSERT(alg.isInitialized());
    TS_ASSERT_THROWS_NOTHING(alg.setPropertyValue("InputWorkspace", "MDWS"));
    TS_ASSERT_THROWS_NOTHING(alg.setPropertyValue("OutputWorkspace", "place_holder"));
    TS_ASSERT_THROWS_NOTHING(alg.setPropertyValue("DensityThresholdFactor", "2.0"));
    TS_ASSERT_THROWS_NOTHING(alg.setPropertyValue("PeakDistanceThreshold", "0.7"));
    TS_ASSERT_THROWS_NOTHING(alg.setProperty("MaxPeaks", int64_t(10)));
    TS_ASSERT_THROWS_NOTHING(alg.setProperty("PeakFindingStrategy", "NumberOfEventsNormalization"));
    TS_ASSERT_THROWS_NOTHING(alg.setProperty("SignalThresholdFactor", 1.3));
    TS_ASSERT_THROWS(alg.execute(), const std::runtime_error &);

    AnalysisDataService::Instance().remove("MDWS");
  }

  void do_test_LeanElastic(bool expInfo, bool histo) {
    FrameworkManager::Instance().exec("CreateMDWorkspace", 18, "Dimensions", "3", "EventType", "MDEvent", "Extents",
                                      "-10,10,-10,10,-10,10", "Names", "Q_sample_x,Q_sample_y,Q_sample_z", "Units",
                                      "-,-,-", "SplitInto", "5", "SplitThreshold", "20", "MaxRecursionDepth", "15",
                                      "OutputWorkspace", "MDWS");

    if (expInfo) {
      Instrument_sptr inst = ComponentCreationHelper::createTestInstrumentRectangular2(1, 100, 0.05);
      IMDEventWorkspace_sptr ws;
      TS_ASSERT_THROWS_NOTHING(ws = AnalysisDataService::Instance().retrieveWS<IMDEventWorkspace>("MDWS"));
      ExperimentInfo_sptr ei(new ExperimentInfo());
      ei->setInstrument(inst);
      // Give it a run number
      ei->mutableRun().addProperty(new PropertyWithValue<std::string>("run_number", "12345"), true);
      ws->addExperimentInfo(ei);
    }

    addPeak(1000, 1, 2, 3, 0.1);
    addPeak(3000, 4, 5, 6, 0.2);
    addPeak(5000, -5, -5, 5, 0.2);

    if (histo) {
      FrameworkManager::Instance().exec("BinMD", 14, "AxisAligned", "1", "AlignedDim0", "Q_sample_x,-10,10,100",
                                        "AlignedDim1", "Q_sample_y,-10,10,100", "AlignedDim2", "Q_sample_z,-10,10,100",
                                        "IterateEvents", "1", "InputWorkspace", "MDWS", "OutputWorkspace", "MDWS");
    }

    std::string outWSName("peaksFound");
    FindPeaksMD alg;
    TS_ASSERT_THROWS_NOTHING(alg.initialize())
    TS_ASSERT(alg.isInitialized())
    TS_ASSERT_THROWS_NOTHING(alg.setPropertyValue("InputWorkspace", "MDWS"));
    TS_ASSERT_THROWS_NOTHING(alg.setPropertyValue("OutputWorkspace", outWSName));
    TS_ASSERT_THROWS_NOTHING(alg.setPropertyValue("DensityThresholdFactor", "2.0"));
    TS_ASSERT_THROWS_NOTHING(alg.setPropertyValue("PeakDistanceThreshold", "0.7"));

    if (expInfo)
      TS_ASSERT_THROWS_NOTHING(alg.setPropertyValue("OutputType", "LeanElasticPeak"));

    TS_ASSERT_THROWS_NOTHING(alg.execute(););
    TS_ASSERT(alg.isExecuted());

    // Retrieve the workspace from data service.
    LeanElasticPeaksWorkspace_sptr ws;
    TS_ASSERT_THROWS_NOTHING(ws = AnalysisDataService::Instance().retrieveWS<LeanElasticPeaksWorkspace>(outWSName));
    TS_ASSERT(ws);
    if (!ws)
      return;

    // Should find all 3 peaks.
    TS_ASSERT_EQUALS(ws->getNumberPeaks(), 3);

    TS_ASSERT_DELTA(ws->getPeak(0).getQSampleFrame()[0], -5.0, 0.11);
    TS_ASSERT_DELTA(ws->getPeak(0).getQSampleFrame()[1], -5.0, 0.11);
    TS_ASSERT_DELTA(ws->getPeak(0).getQSampleFrame()[2], 5.0, 0.11);
    if (expInfo) {
      TS_ASSERT_EQUALS(ws->getPeak(0).getRunNumber(), 12345);
    } else {
      TS_ASSERT_EQUALS(ws->getPeak(0).getRunNumber(), -1);
    }
    // Bin count = density of the box / 1e6
    double BinCount = ws->getPeak(0).getBinCount();
    if (histo) {
      TS_ASSERT_DELTA(BinCount, 0.08375, 0.001);
    } else {
      TS_ASSERT_DELTA(BinCount, 7., 001000.);
    }

    TS_ASSERT_DELTA(ws->getPeak(1).getQSampleFrame()[0], 4.0, 0.11);
    TS_ASSERT_DELTA(ws->getPeak(1).getQSampleFrame()[1], 5.0, 0.11);
    TS_ASSERT_DELTA(ws->getPeak(1).getQSampleFrame()[2], 6.0, 0.11);

    TS_ASSERT_DELTA(ws->getPeak(2).getQSampleFrame()[0], 1.0, 0.11);
    TS_ASSERT_DELTA(ws->getPeak(2).getQSampleFrame()[1], 2.0, 0.11);
    TS_ASSERT_DELTA(ws->getPeak(2).getQSampleFrame()[2], 3.0, 0.11);

    AnalysisDataService::Instance().remove("MDWS");
  }

  void test_exec_LeanElastic() { do_test_LeanElastic(false, false); }

  void test_exec_LeanElastic_histo() { do_test_LeanElastic(false, true); }

  void test_exec_LeanElastic_with_expInfo() { do_test_LeanElastic(true, false); }

  void test_exec_LeanElastic_histo_with_expInfo() { do_test_LeanElastic(true, true); }
};

//=====================================================================================
// Performance Tests
//=====================================================================================
class FindPeaksMDTestPerformance : public CxxTest::TestSuite {

private:
  // Input data

public:
  // This pair of boilerplate methods prevent the suite being created statically
  // This means the constructor isn't called when running other tests
  static FindPeaksMDTestPerformance *createSuite() { return new FindPeaksMDTestPerformance(); }
  static void destroySuite(FindPeaksMDTestPerformance *suite) { delete suite; }
  FindPeaksMDTestPerformance() {
    FrameworkManager::Instance();

    // Make the fake data
    createMDEW();

    for (double x = -5; x <= 5; x += 1.0) {
      for (double y = -2; y <= 2; y += 1.0) {
        for (double z = -2; z <= 2; z += 1.0) {
          addPeak(100, x, y, z, 0.01);
        }
      }
    }
  }

  void test_performance() {
    // Name of the output workspace.
    std::string outWSName("peaksFound");

    FindPeaksMD alg;
    alg.initialize();

    alg.setPropertyValue("InputWorkspace", "MDWS");
    alg.setPropertyValue("OutputWorkspace", outWSName);
    alg.setPropertyValue("DensityThresholdFactor", "2.0");
    alg.setPropertyValue("PeakDistanceThreshold", "0.7");
    alg.setProperty("MaxPeaks", int64_t(300));

    alg.execute();

    // Retrieve the workspace from data service.
    PeaksWorkspace_sptr ws = AnalysisDataService::Instance().retrieveWS<PeaksWorkspace>(outWSName);
    TS_ASSERT(ws);
  }
};
