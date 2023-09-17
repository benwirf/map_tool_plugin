#-----------------------------------------------------------
# Copyright (C) 2023 Ben Wirf
#-----------------------------------------------------------
# Licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#---------------------------------------------------------------------

from qgis.PyQt.QtCore import Qt

from qgis.PyQt.QtWidgets import (QAction, QMenu)

from qgis.PyQt.QtGui import QColor

from qgis.core import (QgsWkbTypes, QgsGeometry, QgsRectangle)

from qgis.gui import (QgsMapToolEmitPoint, QgsRubberBand)


def classFactory(iface):
    return MapToolPlugin(iface)


class MapToolPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.main_action = None
        self.mapTool = None

    def initGui(self):
        self.main_action = QAction('Test Map Tools', self.iface.mainWindow())
        self.menu = QMenu()
        self.drag_rect_action = QAction('Drag a rectangle', self.menu)
        self.drag_rect_action.triggered.connect(self.setRectangleMapTool)
        self.draw_polygon_action = QAction('Draw a polygon', self.menu)
        self.draw_polygon_action.triggered.connect(self.setPolygonMapTool)
        self.menu.addAction(self.drag_rect_action)
        self.menu.addAction(self.draw_polygon_action)
        self.main_action.setMenu(self.menu)
        self.iface.addToolBarIcon(self.main_action)
        
    def setRectangleMapTool(self):
        if self.mapTool:
            self.mapTool.deactivate()
        self.mapTool = RectangleMapTool(self.canvas)
        self.canvas.setMapTool(self.mapTool)
        
    def setPolygonMapTool(self):
        if self.mapTool:
            self.mapTool.deactivate()
        self.mapTool = PolygonMapTool(self.canvas)
        self.canvas.setMapTool(self.mapTool)

    def unload(self):
        self.iface.removeToolBarIcon(self.main_action)
        del self.main_action

#####################POLYGON TOOL###################################

class PolygonMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, self.canvas)
        self.rubber_band_line = None
        self.rubber_band_fixed = None
        self.points = []
        self.drawing = False
        
    def canvasPressEvent(self, e):
        set_point = self.toMapCoordinates(e.pos())
        if self.rubber_band_fixed:
            self.rubber_band_fixed.reset()
        if e.button() == Qt.LeftButton:
            self.drawing = True
            self.points.append(set_point)
            if len(self.points) == 2:
                self.rubber_band_fixed = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
                self.rubber_band_fixed.setStrokeColor(QColor(255, 0, 0, 150))
                self.rubber_band_fixed.setWidth(2)
                geom = QgsGeometry().fromPolylineXY(self.points)
                self.rubber_band_fixed.setToGeometry(geom)
                self.rubber_band_fixed.show()
            elif len(self.points) > 2:
                self.rubber_band_fixed = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
                self.rubber_band_fixed.setStrokeColor(QColor(255, 0, 0, 150))
                self.rubber_band_fixed.setWidth(2)
                pnt_ring = [p for p in self.points]
                pnt_ring.append(pnt_ring[0])
                geom = QgsGeometry().fromPolygonXY([pnt_ring])
                self.rubber_band_fixed.setToGeometry(geom)
                self.rubber_band_fixed.show()
        elif e.button() == Qt.RightButton:
            self.drawing = False
            if len(self.points) <= 2:
                self.clean_up()
            elif len(self.points) > 2:
                if self.rubber_band_line is not None:
                    self.rubber_band_line.reset()
                # Here you could create a QgsFeature instead of a rubber band
                pnt_ring = [p for p in self.points]
                pnt_ring.append(pnt_ring[0])
                geom = QgsGeometry().fromPolygonXY([pnt_ring])
                # and set the feature geometry to geom
                self.rubber_band_fixed.setToGeometry(geom)
                self.rubber_band_fixed.show()
                self.points.clear()
                
    def canvasMoveEvent(self, e):
        if self.drawing:
            point = self.toMapCoordinates(e.pos())
            if self.rubber_band_line is not None:
                self.rubber_band_line.reset()
            if self.points:
                self.rubber_band_line = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
                self.rubber_band_line.setLineStyle(Qt.DashLine)
                self.rubber_band_line.setColor(QColor('Grey'))
                if len(self.points) == 1:
                    geom = QgsGeometry().fromPolylineXY([self.points[0], point])
                    self.rubber_band_line.setToGeometry(geom)
                    self.rubber_band_line.show()
                elif len(self.points) > 1:
                    geom = QgsGeometry().fromPolylineXY([self.points[0], point, self.points[-1]])
                    self.rubber_band_line.setToGeometry(geom)
                    self.rubber_band_line.show()
    
    def clean_up(self):
        if self.rubber_band_line is not None:
            self.rubber_band_line.reset()
            self.rubber_band_line = None
        if self.rubber_band_fixed is not None:
            self.rubber_band_fixed.reset()
            self.rubber_band_fixed = None
        self.points.clear()
        
    def deactivate(self):
        self.clean_up()
        
######################################################################
#####################RECTANGLE TOOL###################################

class RectangleMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, self.canvas)
        self.start_point = None
        self.end_point = None
        self.rubber_band = None
        
    def canvasPressEvent(self, e):
        if self.rubber_band:
            self.rubber_band.reset()
        self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubber_band.setStrokeColor(Qt.red)
        self.rubber_band.setWidth(1)
        self.start_point = self.toMapCoordinates(e.pos())
        self.end_point = self.start_point
    
    def canvasMoveEvent(self, e):
        if self.start_point:
            self.end_point = self.toMapCoordinates(e.pos())
            self.rubber_band.reset()
            r = self.get_rectangle()
            self.rubber_band.setToGeometry(QgsGeometry().fromRect(r))
                
    def canvasReleaseEvent(self, e):
        self.end_point = self.toMapCoordinates(e.pos())
        r = self.get_rectangle()
        self.rubber_band.setToGeometry(QgsGeometry().fromRect(r))
        self.start_point = None
        self.end_point = None
        
    def get_rectangle(self): 
        rect = QgsRectangle(self.start_point, self.end_point)
        return rect
        
    def deactivate(self):
        if self.rubber_band:
            self.rubber_band.reset()
        