# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +
from Muon.GUI.Common.plot_widget.plotting_canvas.plotting_canvas_widget import PlottingCanvasWidget
from Muon.GUI.Common.plot_widget.plot_widget_presenter import PlotWidgetPresenterMain
from Muon.GUI.Common.plot_widget.plot_widget_view import PlotWidgetView, SharedPlotWidgetView
from Muon.GUI.Common.plot_widget.plot_muon_data_pane_model import PlotMuonDataPanetModel
from Muon.GUI.Common.plot_widget.plot_muon_data_presenter import PlotMuonFreqPresenter, PlotMuonDataPresenter

#from mantidqt.utils.observer_pattern import GenericObserver, GenericObserverWithArgPassing, GenericObservable


class PlotWidget(object):
    def __init__(self, context=None, get_active_fit_results=lambda: [], parent=None):
        # The plotting canvas widget
        self.plotting_canvas_widget1 = PlottingCanvasWidget(parent, context=context)
        self.plotting_canvas_widget2 = PlottingCanvasWidget(parent, context=context)
        # The UI view
        self._view1 = SharedPlotWidgetView(parent)
        self._view1.add_canvas_widget(self.plotting_canvas_widget1.widget)

        self._view2 = SharedPlotWidgetView(parent)
        self._view2.add_canvas_widget(self.plotting_canvas_widget2.widget)

        self.view = PlotWidgetView(parent)
        self.model = PlotMuonDataPanetModel(context)
        # generate the presenter

        self.data_mode = PlotMuonDataPresenter(self._view1, self.model, context,self.plotting_canvas_widget1.presenter)
        self.fit_mode = PlotMuonFreqPresenter(self._view2, self.model, context,self.plotting_canvas_widget2.presenter)

        self.presenter = PlotWidgetPresenterMain(self.view,
                                                   [self.data_mode, self.fit_mode])

        context.update_plots_notifier.add_subscriber(self.data_mode.workspace_replaced_in_ads_observer)
        #context.deleted_plots_notifier.add_subscriber(self.presenter.workspace_deleted_from_ads_observer)

    def close(self):
        self.view.close()
