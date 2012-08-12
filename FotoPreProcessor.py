#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FotoPreProcessor: manage (EXIF) metadata of images in a directory
Copyright (C) 2012 Frank Abelbeck <frank.abelbeck@googlemail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

$Id$
"""

# FPP displays image files in a given directory and allows extended selection;
# meant for batch manipulation of orientation, location, timestamp, keywords,
# copyright notice and filename.
#
# 2012-08-10: initial release as "works for me" version

import sys,os,subprocess,time,pytz,datetime,codecs,xml.dom.minidom,base64,re

from PyQt4 import QtGui, QtCore

import FotoPreProcessorWidgets,FotoPreProcessorItem


class FPPMainWindow(QtGui.QMainWindow):	
	"""Main window class. Core element of the HQ."""
	
	def __init__(self):
		"""Constructor: initialise fields, load timezone DB and construct GUI ."""
		QtGui.QMainWindow.__init__(self)
		self.dct_iconsize = {
			u" 32x32":   QtCore.QSize( 32, 32),
			u" 64x64":   QtCore.QSize( 64, 64),
			u"128x128": QtCore.QSize(128,128),
			u"160x160": QtCore.QSize(160,160)
		}
		self.str_path = unicode()
		self.set_keywords = set()
		self.setupGUI()
		self.updateImageList()
	
	def setupGUI(self):
		"""Setup GUI: define widget, layouts and wiring."""
		
		#---------------------------------------------------------------
		
		action_openDir = QtGui.QAction(QtCore.QCoreApplication.translate(u"Menu",u"Open directory..."),self)
		self.action_apply = QtGui.QAction(QtCore.QCoreApplication.translate(u"Menu",u"Apply changes..."),self)
		action_quit = QtGui.QAction(QtCore.QCoreApplication.translate(u"Menu",u"Quit"),self)
		self.action_rotateLeft = QtGui.QAction(QtCore.QCoreApplication.translate(u"Menu",u"Rotate left"),self)
		self.action_rotateRight = QtGui.QAction(QtCore.QCoreApplication.translate(u"Menu",u"Rotate right"),self)
		self.action_locationLookUp = QtGui.QAction(QtCore.QCoreApplication.translate(u"Menu",u"Look up coordinates..."),self)
		self.action_openGimp = QtGui.QAction(QtCore.QCoreApplication.translate(u"Menu",u"Open with the GIMP..."),self)
		self.action_resetOrientation = QtGui.QAction(QtCore.QCoreApplication.translate(u"Menu",u"Reset orientation"),self)
		self.action_resetLocation = QtGui.QAction(QtCore.QCoreApplication.translate(u"Menu",u"Reset coordinates"),self)
		self.action_resetKeywords = QtGui.QAction(QtCore.QCoreApplication.translate(u"Menu",u"Reset keywords"),self)
		self.action_resetTimezones = QtGui.QAction(QtCore.QCoreApplication.translate(u"Menu",u"Reset timezones"),self)
		self.action_resetCopyright = QtGui.QAction(QtCore.QCoreApplication.translate(u"Menu",u"Reset copyright notice"),self)
		self.action_resetAll = QtGui.QAction(QtCore.QCoreApplication.translate(u"Menu",u"Reset everything"),self)
		
		action_config = QtGui.QAction(QtCore.QCoreApplication.translate(u"Menu",u"Configure FPP..."),self)
		action_config.setEnabled(False)
		
		self.action_sortByName = QtGui.QAction(QtCore.QCoreApplication.translate(u"Menu",u"Sort by filename"),self)
		self.action_sortByTime = QtGui.QAction(QtCore.QCoreApplication.translate(u"Menu",u"Sort by timestamp"),self)
		self.action_sortByCamera = QtGui.QAction(QtCore.QCoreApplication.translate(u"Menu",u"Sort by camera"),self)
		self.action_sortByName.setCheckable(True)
		self.action_sortByTime.setCheckable(True)
		self.action_sortByCamera.setCheckable(True)
		self.action_sortByName.setChecked(True)
		
		self.action_rotateLeft.setShortcut(QtGui.QKeySequence(u"l"))
		self.action_rotateRight.setShortcut(QtGui.QKeySequence(u"r"))
		self.action_locationLookUp.setShortcut(QtGui.QKeySequence(u"g"))
		self.action_openGimp.setShortcut(QtGui.QKeySequence(u"c"))
		self.action_resetOrientation.setShortcut(QtGui.QKeySequence(u"n"))
		action_quit.setShortcut(QtGui.QKeySequence(u"Ctrl+Q"))
		action_openDir.setShortcut(QtGui.QKeySequence(u"Ctrl+O"))
		self.action_apply.setShortcut(QtGui.QKeySequence(u"Ctrl+S"))
		
		#---------------------------------------------------------------
		
		self.list_images = QtGui.QListWidget(self)
		self.list_images.setItemDelegate(FotoPreProcessorItem.FPPGalleryItemDelegate(QtGui.QIcon(os.path.join(sys.path[0],u"icons",u"changed.png"))))
		self.list_images.setIconSize(QtCore.QSize(128,128))
		self.list_images.setViewMode(QtGui.QListView.IconMode)
		self.list_images.setResizeMode(QtGui.QListView.Adjust)
		self.list_images.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
		self.list_images.setDragEnabled(False)
		self.list_images.setUniformItemSizes(True)
		
		#---------------------------------------------------------------
		
		self.dock_geotagging = FotoPreProcessorWidgets.FPPGeoTaggingDock()
		self.dock_timezones  = FotoPreProcessorWidgets.FPPTimezonesDock()
		self.dock_keywords   = FotoPreProcessorWidgets.FPPKeywordsDock()
		self.dock_copyright  = FotoPreProcessorWidgets.FPPCopyrightDock()
		
		self.dock_geotagging.setEnabled(False)
		self.dock_timezones.setEnabled(False)
		self.dock_keywords.setEnabled(False)
		self.dock_copyright.setEnabled(False)
		
		#---------------------------------------------------------------
		# construct menubar
		#
		# &File  &Edit       &View    &Bookmarks   Sess&ions  &Tools  &Settings      &Help
		# &Datei &Bearbeiten &Ansicht &Lesezeichen &Sitzungen E&xtras &Einstellungen &Hilfe
		#---------------------------------------------------------------
		
		menu_file = self.menuBar().addMenu(QtCore.QCoreApplication.translate(u"Menu",u"&File"))
		menu_file.addAction(action_openDir)
		menu_file.addSeparator()
		menu_file.addAction(self.action_apply)
		menu_file.addSeparator()
		menu_file.addAction(action_quit)
		
		self.menu_edit = self.menuBar().addMenu(QtCore.QCoreApplication.translate(u"Menu",u"&Edit"))
		self.menu_edit.addAction(self.action_rotateLeft)
		self.menu_edit.addAction(self.action_rotateRight)
		self.menu_edit.addSeparator()
		self.menu_edit.addAction(self.action_locationLookUp)
		self.menu_edit.addSeparator()
		menu_reset = self.menu_edit.addMenu(QtCore.QCoreApplication.translate(u"Menu",u"Reset values"))
		menu_reset.addAction(self.action_resetOrientation)
		menu_reset.addAction(self.action_resetLocation)
		menu_reset.addAction(self.action_resetTimezones)
		menu_reset.addAction(self.action_resetKeywords)
		menu_reset.addAction(self.action_resetCopyright)
		menu_reset.addSeparator()
		menu_reset.addAction(self.action_resetAll)
		self.menu_edit.addSeparator()
		self.menu_edit.addAction(self.action_openGimp)
		
		#---------------------------------------------------------------
		
		menu_settings = self.menuBar().addMenu(QtCore.QCoreApplication.translate(u"Menu",u"&Settings"))
		menu_docks = menu_settings.addMenu(QtCore.QCoreApplication.translate(u"Menu",u"Dockable windows"))
		menu_iconSize = menu_settings.addMenu(QtCore.QCoreApplication.translate(u"Menu",u"Icon size"))
		menu_sorting = menu_settings.addMenu(QtCore.QCoreApplication.translate(u"Menu",u"Sort criterion"))
		menu_settings.addSeparator()
		menu_settings.addAction(action_config)
		
		menu_docks.addAction(self.dock_geotagging.toggleViewAction())
		menu_docks.addAction(self.dock_timezones.toggleViewAction())
		menu_docks.addAction(self.dock_keywords.toggleViewAction())
		menu_docks.addAction(self.dock_copyright.toggleViewAction())
		
		actiongroup_iconSize = QtGui.QActionGroup(self)
		sizes = self.dct_iconsize.keys()
		sizes.sort()
		for size in sizes:
			action_iconSize = QtGui.QAction(size,self)
			action_iconSize.setCheckable(True)
			action_iconSize.setChecked(size == u"128x128")
			actiongroup_iconSize.addAction(action_iconSize)
			menu_iconSize.addAction(action_iconSize)
		
		actiongroup_sorting = QtGui.QActionGroup(self)
		actiongroup_sorting.addAction(self.action_sortByName)
		actiongroup_sorting.addAction(self.action_sortByTime)
		actiongroup_sorting.addAction(self.action_sortByCamera)
		menu_sorting.addAction(self.action_sortByName)
		menu_sorting.addAction(self.action_sortByTime)
		menu_sorting.addAction(self.action_sortByCamera)
		
		#---------------------------------------------------------------
		# wiring: connect widgets to functions (signals to slots)
		#---------------------------------------------------------------
		
		self.connect(
			self.list_images,
			QtCore.SIGNAL('itemSelectionChanged()'),
			self.listImagesSelectionChanged
		)
		self.connect(
			self.list_images,
			QtCore.SIGNAL('itemChanged(QListWidgetItem*)'),
			self.listImagesItemChanged
		)
		
		#---------------------------------------------------------------
		
		self.connect(
			action_quit,
			QtCore.SIGNAL('triggered()'),
			QtGui.QApplication.instance().quit
		)
		self.connect(
			self.action_apply,
			QtCore.SIGNAL('triggered()'),
			self.applyChanges
		)
		self.connect(
			action_openDir,
			QtCore.SIGNAL('triggered()'),
			self.selectDirectory
		)
		self.connect(
			menu_iconSize,
			QtCore.SIGNAL('triggered(QAction*)'),
			self.adjustIconSize
		)
		self.connect(
			menu_sorting,
			QtCore.SIGNAL('triggered(QAction*)'),
			self.setSortCriterion
		)
		
		self.connect(
			self.action_rotateLeft,
			QtCore.SIGNAL('triggered()'),
			self.rotateImageLeft
		)
		self.connect(
			self.action_rotateRight,
			QtCore.SIGNAL('triggered()'),
			self.rotateImageRight
		)
		
		self.connect(
			self.action_resetAll,
			QtCore.SIGNAL('triggered()'),
			self.resetAll
		)
		self.connect(
			self.action_resetOrientation,
			QtCore.SIGNAL('triggered()'),
			self.resetOrientation
		)
		self.connect(
			self.action_resetLocation,
			QtCore.SIGNAL('triggered()'),
			self.resetLocation
		)
		self.connect(
			self.action_resetTimezones,
			QtCore.SIGNAL('triggered()'),
			self.resetTimezones
		)
		self.connect(
			self.action_resetKeywords,
			QtCore.SIGNAL('triggered()'),
			self.resetKeywords
		)
		self.connect(
			self.action_resetCopyright,
			QtCore.SIGNAL('triggered()'),
			self.resetCopyright
		)
		
		self.connect(
			self.action_locationLookUp,
			QtCore.SIGNAL('triggered()'),
			self.dock_geotagging.lookUpCoordinates
		)
		self.connect(
			self.action_openGimp,
			QtCore.SIGNAL('triggered()'),
			self.openWithTheGimp
		)
		
		#---------------------------------------------------------------
		
		self.connect(
			self.action_resetOrientation,
			QtCore.SIGNAL('changed()'),
			self.updateResetAllAction
		)
		self.connect(
			self.action_resetLocation,
			QtCore.SIGNAL('changed()'),
			self.updateResetAllAction
		)
		self.connect(
			self.action_resetTimezones,
			QtCore.SIGNAL('changed()'),
			self.updateResetAllAction
		)
		self.connect(
			self.action_resetKeywords,
			QtCore.SIGNAL('changed()'),
			self.updateResetAllAction
		)
		self.connect(
			self.action_resetCopyright,
			QtCore.SIGNAL('changed()'),
			self.updateResetAllAction
		)
		
		#---------------------------------------------------------------
		
		self.connect(
			self.dock_geotagging,
			QtCore.SIGNAL('dockDataUpdated(PyQt_PyObject)'),
			self.updateLocation
		)
		self.connect(
			self.dock_geotagging,
			QtCore.SIGNAL('dockResetTriggered()'),
			self.resetLocation
		)
		
		#---------------------------------------------------------------
		
		self.connect(
			self.dock_timezones,
			QtCore.SIGNAL('dockDataUpdated(PyQt_PyObject)'),
			self.updateTimezones
		)
		self.connect(
			self.dock_timezones,
			QtCore.SIGNAL('dockResetTriggered()'),
			self.resetTimezones
		)
		
		#---------------------------------------------------------------
		
		self.connect(
			self.dock_keywords,
			QtCore.SIGNAL('dockKeywordAdded(PyQt_PyObject)'),
			self.addKeyword
		)
		self.connect(
			self.dock_keywords,
			QtCore.SIGNAL('dockKeywordRemoved(PyQt_PyObject)'),
			self.removeKeyword
		)
		self.connect(
			self.dock_keywords,
			QtCore.SIGNAL('dockResetTriggered()'),
			self.resetKeywords
		)
		
		#---------------------------------------------------------------
		
		self.connect(
			self.dock_copyright,
			QtCore.SIGNAL('dockDataUpdated(PyQt_PyObject)'),
			self.updateCopyright
		)
		self.connect(
			self.dock_copyright,
			QtCore.SIGNAL('dockResetTriggered()'),
			self.resetCopyright
		)
		
		#---------------------------------------------------------------
		
		self.connect(
			action_config,
			QtCore.SIGNAL('triggered()'),
			self.configureProgram
		)
		
		#---------------------------------------------------------------
		# construct main window
		#---------------------------------------------------------------
		self.setCentralWidget(self.list_images)
		#self.resize(640,400)
		
		self.addDockWidget(QtCore.Qt.RightDockWidgetArea,self.dock_geotagging)
		self.addDockWidget(QtCore.Qt.RightDockWidgetArea,self.dock_timezones)
		self.addDockWidget(QtCore.Qt.RightDockWidgetArea,self.dock_keywords)
		self.addDockWidget(QtCore.Qt.RightDockWidgetArea,self.dock_copyright)
		
		self.setWindowTitle(QtCore.QCoreApplication.translate(u"MainWindow",u"FotoPreProcessor"))
		#self.setWindowIcon(self.icon_tpgui)
		self.setStyleSheet(u":disabled { color: gray; }")
		self.show()
	
	
	def closeEvent(self,event):
		"""Window received close event: toggles visibility (ie close to tray)."""
		edited = False
		for i in xrange(0,self.list_images.count()):
			if self.list_images.item(i).edited():
				edited = True
				break
		if edited:
			answer = QtGui.QMessageBox.question(
				self,
				QtCore.QCoreApplication.translate(u"Dialog",u"Exit Application"),
				QtCore.QCoreApplication.translate(u"Dialog",u"Some changes were made.\nDo you want to apply them before exiting?"),
				QtGui.QMessageBox.Yes | QtGui.QMessageBox.No
			)
			if answer == QtGui.QMessageBox.Yes:
				self.applyChanges()
		self.dock_copyright.close() # i.e.: save copyright DB
		self.dock_keywords.close()  # i.e.: save keywords DB
		event.accept()
	
	
	def selectDirectory(self):
		path = QtGui.QFileDialog.getExistingDirectory(self,
			QtCore.QCoreApplication.translate(u"Dialog",u"Select Directory"),
			self.str_path,
			QtGui.QFileDialog.DontUseNativeDialog
		)
		if len(path) > 0:
			self.setDirectory(path)
	
	
	def setDirectory(self,path=unicode()):
		path = unicode(path)
		if os.path.isdir(path):
			self.str_path = path
			self.setWindowTitle(
				QtCore.QCoreApplication.translate(
					u"MainWindow",
					u"FotoPreProcessor"
				) + u": " + path
			)
			self.updateImageList()
		else:
			# delete list, reset path and title...
			self.str_path = unicode()
			self.setWindowTitle(
				QtCore.QCoreApplication.translate(
					u"MainWindow",
					u"FotoPreProcessor"
				)
			)
			self.list_images.clear()
	
	
	def adjustIconSize(self,action):
		self.list_images.setIconSize(self.dct_iconsize[unicode(action.text())])
		for i in xrange(0,self.list_images.count()):
			self.list_images.item(i).updateIcon()
	
	
	def setSortCriterion(self,action):
		if action == self.action_sortByTime:
			sortCriterion = FotoPreProcessorItem.FPPGalleryItem.SortByTime
		elif action == self.action_sortByCamera:
			sortCriterion = FotoPreProcessorItem.FPPGalleryItem.SortByCamera
		else:
			sortCriterion = FotoPreProcessorItem.FPPGalleryItem.SortByName
		
		for i in xrange(0,self.list_images.count()):
			self.list_images.item(i).setSortCriterion(sortCriterion)
		self.list_images.sortItems()
	
	
	def getFirstTextChild(self,node=None):
		value = unicode()
		for child in node.childNodes:
			if child.nodeType == node.TEXT_NODE and len(child.nodeValue.strip()) > 0:
				value = unicode(node.childNodes[0].nodeValue.strip())
				break
		return value
	
	
	def updateImageList(self):
		self.list_images.clear()
		
		try:
			filelist = [os.path.join(self.str_path,i) for i in os.listdir(self.str_path)]
			pathlist = list()
			for fileresult in subprocess.check_output([u"/usr/bin/file",u"-iN"]+filelist).splitlines():
				if u": image/" in fileresult:
					pathlist.append(fileresult.split(": image/")[0])
			pathlist.sort()
		except:
			pathlist = list()
		
		progress = QtGui.QProgressDialog(self)
		progress.setMinimumDuration(0)
		progress.setRange(0,100)
		progress.setWindowModality(QtCore.Qt.WindowModal)
		progress.setValue(0)
		progress.setLabelText(QtCore.QCoreApplication.translate(
			u"Dialog",
			u"Extracting EXIF information..."
		))
		progress.forceShow()
		
		if self.action_sortByName.isChecked():
			sortCriterion = FotoPreProcessorItem.FPPGalleryItem.SortByName
		elif self.action_sortByTime.isChecked():
			sortCriterion = FotoPreProcessorItem.FPPGalleryItem.SortByTime
		elif self.action_sortByCamera.isChecked():
			sortCriterion = FotoPreProcessorItem.FPPGalleryItem.SortByCamera
			
		if len(pathlist) > 0:
			with codecs.open("/tmp/FotoPreProcessor.xml","w") as f:
				try:
					subprocess.call([ u"/usr/bin/exiftool",
					    u"-X",
						u"-b",
						u"-m",
						u"-d",u"%Y %m %d %H %M %S",
						u"-Orientation",
						u"-DateTimeOriginal",
						u"-Keywords",
						u"-FocalLength#",
						u"-ScaleFactor35efl",
						u"-Aperture",
						u"-ShutterSpeed",
						u"-ISO",
						u"-Model",
						u"-LensType",
						u"-ThumbnailImageValidArea",
						u"-Copyright",
						u"-GPS:GPSLatitude#",
						u"-GPS:GPSLatitudeRef#",
						u"-GPS:GPSLongitude#",
						u"-GPS:GPSLongitudeRef#",
						u"-GPS:GPSAltitude#",
						u"-GPS:GPSAltitudeRef#",
						u"-ThumbnailImage"
					] + pathlist,stdout=f)
				except:
					pass
			with codecs.open(f.name,"r") as f:
				try:    dom = xml.dom.minidom.parse(f)
				except: dom = None
			os.remove(f.name)
			
			try:    descriptionElements = dom.getElementsByTagName("rdf:Description")
			except: descriptionElements = tuple()
		else:
			descriptionElements = tuple()
		
		i_max = len(descriptionElements)
		for i,description in enumerate(descriptionElements):
			
			filepath = unicode(description.getAttribute("rdf:about"))
			if len(filepath) == 0: continue
			filename = os.path.basename(filepath)
			
			progress.setValue(9+80*(float(i)/i_max))
			progress.setLabelText(u"{0} {1}...".format(
				QtCore.QCoreApplication.translate(u"Dialog",u"Processing Image"),
				filename
			))
			
			timestamp    = unicode()
			focalLength  = unicode()
			cropFactor   = unicode()
			aperture     = unicode()
			shutterSpeed = unicode()
			isoValue     = unicode()
			cameraModel  = unicode()
			lensType     = unicode()
			thumbArea    = unicode()
			latitude     = unicode()
			latitudeRef  = unicode()
			longitude    = unicode()
			longitudeRef = unicode()
			elevation    = unicode()
			elevationRef = unicode()
			thumbData    = unicode()
			
			item = FotoPreProcessorItem.FPPGalleryItem(self.list_images)
			item.setFilename(filename)
			
			for node in description.childNodes:
				if node.nodeType != node.ELEMENT_NODE: continue
				if node.localName == "Orientation":
					item.setOrientation(self.getFirstTextChild(node))
				elif node.localName == "DateTimeOriginal":
					timestamp = self.getFirstTextChild(node)
				elif node.localName == "Keywords":
					keywords = list()
					try:
						for bagItem in node.getElementsByTagName("rdf:Bag")[0].getElementsByTagName("rdf:li"):
							keywords.append(self.getFirstTextChild(bagItem))
					except:
						pass
					item.setKeywords(keywords)
				elif node.localName == "FocalLength":
					focalLength = self.getFirstTextChild(node)
				elif node.localName == "ScaleFactor35efl":
					cropFactor = self.getFirstTextChild(node)
				elif node.localName == "Aperture":
					aperture = self.getFirstTextChild(node)
				elif node.localName == "ShutterSpeed":
					shutterSpeed = self.getFirstTextChild(node)
				elif node.localName == "ISO":
					isoValue = self.getFirstTextChild(node)
				elif node.localName == "Model":
					cameraModel = self.getFirstTextChild(node)
				elif node.localName == "LensType":
					lensType = self.getFirstTextChild(node)
				elif node.localName == "ThumbnailImageValidArea":
					thumbArea = self.getFirstTextChild(node)
				elif node.localName == "Copyright":
					cr = self.getFirstTextChild(node)
					try:    cr = re.match(r'^(©|\(C\)|\(c\)) \d{4} (.*)',cr).groups()[1]
					except: pass
					item.setCopyright(cr)
				elif node.localName == "GPSLatitude":
					latitude = self.getFirstTextChild(node)
				elif node.localName == "GPSLatitudeRef":
					latitudeRef = self.getFirstTextChild(node)
				elif node.localName == "GPSLongitude":
					longitude = self.getFirstTextChild(node)
				elif node.localName == "GPSLongitudeRef":
					longitudeRef = self.getFirstTextChild(node)
				elif node.localName == "GPSAltitude":
					elevation = self.getFirstTextChild(node)
				elif node.localName == "GPSAltitudeRef":
					elevationRef = self.getFirstTextChild(node)
				elif node.localName == "ThumbnailImage":
					thumbData = base64.b64decode(self.getFirstTextChild(node))
			
			thumbImage = QtGui.QPixmap()
			if not thumbImage.loadFromData(thumbData):
				try:
					thumbImage = QtGui.QPixmap(filepath)
					thumbImage.scaled(QtCore.QSize(160,160),QtCore.Qt.KeepAspectRatio,QtCore.Qt.SmoothTransformation)
				except:
					thumbImage = QtGui.QPixmap(os.path.join(sys.path[0],u"icons",u"unknownPicture2.png"))
			else:
				try:
					(x1,x2,y1,y2) = tuple(thumbArea.split(u" "))
					thumbRect = QtCore.QRect()
					thumbRect.setTop(int(y1))
					thumbRect.setBottom(int(y2))
					thumbRect.setLeft(int(x1))
					thumbRect.setRight(int(x2))
					thumbImage = thumbImage.copy(thumbRect)
				except:
					pass
			item.setThumbnail(thumbImage)
			
			if len(timestamp) == 0:
				# obtain timestamp from filesystem
				timestamp = time.strftime(
					u"%Y %m %d %H %M %S",
					time.localtime(os.path.getctime(filepath))
				)
			try:    item.setTimestamp(timestamp.split(u" "))
			except: pass
			
			settings = []
			if len(focalLength) != 0:
				try:
					settings.append(u"{0} mm ({1})".format(
						int(float(focalLength) * float(cropFactor)),
						QtCore.QCoreApplication.translate(u"ItemToolTip",u"on full-frame")
					))
				except:
					settings.append(u"{0} ({1})".format(
						focalLength,
						QtCore.QCoreApplication.translate(u"ItemToolTip",u"physical")
					))
			if len(aperture) != 0:
				settings.append(u"f/" + aperture)
			if len(shutterSpeed) != 0:
				settings.append(shutterSpeed + u" s")
			if len(isoValue) != 0:
				settings.append(u"ISO " + isoValue)
			if len(settings) != 0:
				item.setCameraSettings(u", ".join(settings))
			
			settings = []
			if len(cameraModel) > 0 and not cameraModel.startswith(u"Unknown"):
				settings.append(cameraModel)
			if len(lensType) > 0 and not lensType.startswith(u"Unknown"):
				settings.append(lensType)
			if len(settings) != 0:
				item.setCameraHardware(u", ".join(settings))
			
			try:
				latitude = float(latitude)
				longitude = float(longitude)
				if latitudeRef == u"S": latitude = -latitude
				if longitudeRef == u"W": longitude = -longitude
				try:    elevation = float(elevation)
				except: elevation = 0.0
				if elevationRef == u"1": elevation = -elevation
				item.setLocation(latitude,longitude,elevation)
			except:
				pass
			
			item.setSortCriterion(sortCriterion)
			item.saveState()
		
		self.list_images.sortItems()
		
		progress.close()
		
		self.action_apply.setEnabled(False)
		
		self.action_locationLookUp.setEnabled(False)
		self.action_openGimp.setEnabled(False)
		
		self.action_resetAll.setEnabled(False)
		self.action_resetOrientation.setEnabled(False)
		self.action_resetLocation.setEnabled(False)
		self.action_resetTimezones.setEnabled(False)
		self.action_resetKeywords.setEnabled(False)
		self.action_resetCopyright.setEnabled(False)
		
		self.action_rotateLeft.setEnabled(False)
		self.action_rotateRight.setEnabled(False)
	
	
	def listImagesItemChanged(self,item):
		edited = False
		for i in xrange(0,self.list_images.count()):
			if self.list_images.item(i).edited():
				edited = True
				break
		self.action_apply.setEnabled(edited)
	
	
	def listImagesSelectionChanged(self):
		items = self.list_images.selectedItems()
		if len(items) > 0:
			# collect data of selected items
			location  = set()
			timezones = set()
			keywords  = set()
			copyright = set()
			orientationEdited = False
			locationEdited = False
			timezonesEdited = False
			keywordsEdited = False
			copyrightEdited = False
			for item in items:
				location.add(item.location())
				timezones.add(item.timezones())
				keywords.add(item.keywords())
				copyright.add(item.copyright())
				orientationEdited = orientationEdited or item.orientationEdited()
				locationEdited = locationEdited or item.locationEdited()
				timezonesEdited = timezonesEdited or item.timezonesEdited()
				keywordsEdited = keywordsEdited or item.keywordsEdited()
				copyrightEdited = copyrightEdited or item.copyrightEdited()
			l_timezones = len(timezones)
			l_location  = len(location)
			l_keywords  = len(keywords)
			l_copyright = len(copyright)
			
			# import location data or resolve location conflicts
			self.dock_geotagging.setEnabled(True)
			self.action_locationLookUp.setEnabled(True)
			latitude,longitude,elevation = None,None,None
			if l_location == 1:
				try:    (latitude,longitude,elevation) = location.pop()
				except: pass
			elif l_location > 1:
				answer = QtGui.QMessageBox.question(
					self,
					QtCore.QCoreApplication.translate(u"Dialog",u"Location Collision"),
					QtCore.QCoreApplication.translate(u"Dialog",u"The selected images are tagged with different locations.\nDo you want to reset them?\nIf you answer \"No\", GeoTagging will be disabled."),
					QtGui.QMessageBox.Yes | QtGui.QMessageBox.No
				)
				if answer == QtGui.QMessageBox.Yes:
					locationEdited = False
					for item in items:
						item.setLocation(None,None,None)
						locationEdited = locationEdited or item.locationEdited()
				else:
					self.dock_geotagging.setEnabled(False)
					self.action_locationLookUp.setEnabled(False)
			
			self.dock_geotagging.setLocation(latitude,longitude,elevation)
			self.dock_timezones.setLocation(latitude,longitude)
			self.dock_geotagging.setResetEnabled(locationEdited)
			
			# import timezone corrections or resolve conflicts
			self.dock_timezones.setEnabled(True)
			fromTz,toTz = u"UTC",u"UTC"
			if l_timezones == 1:
				try:    (fromTz,toTz) = timezones.pop()
				except: pass
			elif l_timezones > 1:
				lst_timezones = list()
				timezones.add((u"UTC",u"UTC"))
				for tz in timezones:
					lst_timezones.append(u"{0} → {1}".format(*tz))
				lst_timezones.sort()
				lst_timezones.insert(0,u"Disable timezone settings.")
				(answer,ok) = QtGui.QInputDialog.getItem(self,
					QtCore.QCoreApplication.translate(u"Dialog",u"Timezones Collision"),
					QtCore.QCoreApplication.translate(u"Dialog",u"The selected images feature different timezone correction information.\nWhich one should be used?\nIf you cancel this dialog, timezone settings will be disabled."),
					lst_timezones,0,False
				)
				if ok and answer != lst_timezones[0]:
					(fromTz,toTz) = tuple(unicode(answer).split(u" → ",1))
					timezonesEdited = False
					for item in items:
						item.setTimezones(fromTz,toTz)
						timezonesEdited = timezonesEdited or item.timezonesEdited()
				else:
					self.dock_timezones.setEnabled(False)
			self.dock_timezones.setTimezones(fromTz,toTz)
			self.dock_timezones.setResetEnabled(timezonesEdited)
			
			# import keywords or resolve conflicts
			self.dock_keywords.setEnabled(True)
			self.dock_keywords.setKeywords()
			tpl_kws = tuple()
			if l_keywords ==  1:
				try:    tpl_kws = tuple(keywords.pop())
				except: pass
			elif l_keywords > 1:
				str_disable = QtCore.QCoreApplication.translate(u"Dialog",u"Disable keyword settings.")
				str_empty = QtCore.QCoreApplication.translate(u"Dialog",u"Remove all keywords from all images.")
				str_union = QtCore.QCoreApplication.translate(u"Dialog",u"Apply union of all keywords to all images.")
				str_inter = QtCore.QCoreApplication.translate(u"Dialog",u"Only edit keywords common to all images.")
				str_diff  = QtCore.QCoreApplication.translate(u"Dialog",u"Remove common keywords and merge the remaining.")
				(answer,ok) = QtGui.QInputDialog.getItem(self,
					QtCore.QCoreApplication.translate(u"Dialog",u"Keyword Collision"),
					QtCore.QCoreApplication.translate(u"Dialog",u"The selected images feature different sets of keywords.\nWhat do you want to do?\nIf you cancel this dialog, keyword settings will be disabled."),
					(str_disable,str_empty,str_union,str_inter,str_diff),0,False
				)
				if ok and answer != str_disable:
					set_kws = set(keywords.pop())
					keywordsEdited = False
					if answer == str_empty:
						# clear keywords of all selected items
						tpl_kws = tuple()
						for item in items:
							item.setKeywords(tpl_kws)
							keywordsEdited = keywordsEdited or item.keywordsEdited()
					elif answer == str_union:
						# create union of all keywords and apply it to all selected items
						for kws in keywords:
							set_kws = set_kws.union(set(kws))
						tpl_kws = tuple(set_kws)
						for item in items:
							item.setKeywords(tpl_kws)
							keywordsEdited = keywordsEdited or item.keywordsEdited()
					elif answer == str_inter:
						# create intersection, but don't apply it to the selected items;
						# editing will be done on this set; addKeyword and
						# removeKeyword will apply the settings to the items
						for kws in keywords:
							set_kws = set_kws.intersection(set(kws))
						tpl_kws = tuple(set_kws)
						for item in items:
							keywordsEdited = keywordsEdited or item.keywordsEdited()
					elif answer == str_diff:
						# create symmetric difference and apply it to all selected items
						for kws in keywords:
							set_kws = set_kws.symmetric_difference(set(kws))
						tpl_kws = tuple(set_kws)
						for item in items:
							item.setKeywords(tpl_kws)
							keywordsEdited = keywordsEdited or item.keywordsEdited()
				else:
					self.dock_keywords.setEnabled(False)
			self.dock_keywords.setKeywords(tpl_kws)
			self.dock_keywords.setResetEnabled(keywordsEdited)
			
			# import copyright data or resolve conflicts
			self.dock_copyright.setEnabled(True)
			copyrightNotice = unicode()
			if l_copyright == 1:
				try:    copyrightNotice = copyright.pop()
				except: pass
			elif l_copyright > 1:
				lst_copyright = [u"None (clear copyright notice)"]
				lst_copyright.extend(list(copyright))
				(answer,ok) = QtGui.QInputDialog.getItem(self,
					QtCore.QCoreApplication.translate(u"Dialog",u"Copyright Collision"),
					QtCore.QCoreApplication.translate(u"Dialog",u"The selected images feature different copyright notices.\nWhich one should be used?\nIf you cancel this dialog, copyright settings will be disabled."),
					lst_copyright,0,False
				)
				if ok:
					if answer != lst_copyright[0]:
						copyrightNotice = unicode(answer)
					copyrightEdited = False
					for item in items:
						item.setCopyright(copyrightNotice)
						copyrightEdited = copyrightEdited or item.copyrightEdited()
				else:
					self.dock_copyright.setEnabled(False)
			self.dock_copyright.setCopyright(copyrightNotice)
			self.dock_copyright.setResetEnabled(copyrightEdited)
			
			self.action_openGimp.setEnabled(True)
			
			self.action_resetAll.setEnabled(orientationEdited or locationEdited or timezonesEdited or keywordsEdited)
			self.action_resetOrientation.setEnabled(orientationEdited)
			self.action_resetLocation.setEnabled(locationEdited)
			self.action_resetTimezones.setEnabled(timezonesEdited)
			self.action_resetKeywords.setEnabled(keywordsEdited)
			self.action_resetCopyright.setEnabled(copyrightEdited)
			
			self.action_rotateLeft.setEnabled(True)
			self.action_rotateRight.setEnabled(True)
		else:
			self.dock_geotagging.setEnabled(False)
			self.dock_timezones.setEnabled(False)
			self.dock_keywords.setEnabled(False)
			self.dock_copyright.setEnabled(False)
			
			self.action_locationLookUp.setEnabled(False)
			self.action_openGimp.setEnabled(False)
			
			self.action_resetAll.setEnabled(False)
			self.action_resetOrientation.setEnabled(False)
			self.action_resetLocation.setEnabled(False)
			self.action_resetTimezones.setEnabled(False)
			self.action_resetKeywords.setEnabled(False)
			self.action_resetCopyright.setEnabled(False)
			
			self.action_rotateLeft.setEnabled(False)
			self.action_rotateRight.setEnabled(False)
	
	#-----------------------------------------------------------------------
	# orientation: methods
	#-----------------------------------------------------------------------
	
	def rotateImageLeft(self):
		for item in self.list_images.selectedItems(): item.rotateLeft()
		self.action_resetOrientation.setEnabled(True)
	
	
	def rotateImageRight(self):
		for item in self.list_images.selectedItems(): item.rotateRight()
		self.action_resetOrientation.setEnabled(True)
	
	
	def resetOrientation(self):
		for item in self.list_images.selectedItems(): item.resetOrientation()
	
	#-----------------------------------------------------------------------
	# geotagging: methods
	#-----------------------------------------------------------------------
	
	def updateLocation(self,location=tuple()):
		try:
			latitude  = float(location[0])
			longitude = float(location[1])
			elevation = float(location[2])
		except:
			latitude  = None
			longitude = None
			elevation = 0.0
		edited = False
		for item in self.list_images.selectedItems():
			item.setLocation(latitude,longitude,elevation)
			edited = edited or item.edited()
		self.dock_timezones.setLocation(latitude,longitude)
		self.dock_geotagging.setResetEnabled(edited)
		self.action_resetLocation.setEnabled(edited)
	
	
	def resetLocation(self):
		for item in self.list_images.selectedItems(): item.resetLocation()
		self.listImagesSelectionChanged()
	
	#-----------------------------------------------------------------------
	# timezones: methods
	#-----------------------------------------------------------------------
	
	def updateTimezones(self,timezones=tuple()):
		try:
			fromTz = unicode(timezones[0])
			toTz   = unicode(timezones[1])
			edited = False
			for item in self.list_images.selectedItems():
				item.setTimezones(fromTz,toTz)
				edited = edited or item.edited()
			self.dock_timezones.setResetEnabled(edited)
			self.action_resetTimezones.setEnabled(edited)
		except:
			pass
	
	
	def resetTimezones(self):
		for item in self.list_images.selectedItems(): item.resetTimezones()
		self.listImagesSelectionChanged()
	
	#-----------------------------------------------------------------------
	# keywords: methods
	#-----------------------------------------------------------------------
	
	def addKeyword(self,keyword=unicode()):
		try:
			keyword = unicode(keyword)
			edited = False
			for item in self.list_images.selectedItems():
				item.addKeyword(keyword)
				edited = edited or item.edited()
			self.dock_keywords.setResetEnabled(edited)
			self.action_resetKeywords.setEnabled(edited)
		except:
			pass
	
	
	def removeKeyword(self,keyword=unicode()):
		try:
			keyword = unicode(keyword)
			edited = False
			for item in self.list_images.selectedItems():
				item.removeKeyword(keyword)
				edited = edited or item.edited()
			self.dock_keywords.setResetEnabled(edited)
			self.action_resetKeywords.setEnabled(edited)
		except:
			pass
	
	
	def resetKeywords(self):
		for item in self.list_images.selectedItems(): item.resetKeywords()
		self.listImagesSelectionChanged()
	
	#-----------------------------------------------------------------------
	# copyright: methods
	#-----------------------------------------------------------------------
	
	def updateCopyright(self,notice=unicode()):
		try:
			notice = unicode(notice)
			edited = False
			for item in self.list_images.selectedItems():
				item.setCopyright(notice)
				edited = edited or item.edited()
			self.dock_copyright.setResetEnabled(edited)
			self.action_resetCopyright.setEnabled(edited)
		except:
			pass
	
	
	def resetCopyright(self):
		for item in self.list_images.selectedItems(): item.resetCopyright()
		self.listImagesSelectionChanged()
	
	#-----------------------------------------------------------------------
	
	def applyChanges(self):
		dct_parameters = dict()
		lst_all_files = list()
		for i in xrange(0,self.list_images.count()):
			item = self.list_images.item(i)
			name = unicode(os.path.join(self.str_path,item.filename()))
			lst_all_files.append(name)
			
			if item.edited():
				parameters = list()
				
				if item.orientationEdited():
					parameters.append(u"-Orientation={0}".format(item.orientation()))
				
				if item.locationEdited():
					try:
						(lat,lon,ele) = item.location()
						latitude  = unicode(abs(lat))
						longitude = unicode(abs(lon))
						elevation = unicode(abs(ele))
						if lat < 0:
							latitudeRef = u"S"
						else:
							latitudeRef = u"N"
						if lon < 0:
							longitudeRef = u"W"
						else:
							longitudeRef = u"E"
						if ele < 0:
							elevationRef = u"1"
						else:
							elevationRef = u"0"
					except:
						latitude     = unicode()
						latitudeRef  = unicode()
						longitude    = unicode()
						longitudeRef = unicode()
						elevation    = unicode()
						elevationRef = unicode()
					parameters.append(u"-GPSLatitude={0}".format(latitude))
					parameters.append(u"-GPSLatitudeRef={0}".format(latitudeRef))
					parameters.append(u"-GPSLongitude={0}".format(longitude))
					parameters.append(u"-GPSLongitudeRef={0}".format(longitudeRef))
					parameters.append(u"-GPSAltitude={0}".format(elevation))
					parameters.append(u"-GPSAltitudeRef={0}".format(elevationRef))
				
				if item.timezonesEdited():
					try:
						t     = item.shiftedTimestamp().strftime("%Y:%m:%d %H:%M:%S")
						t_utc = item.utcTimestamp().strftime("%Y:%m:%d %H:%M:%S")
					except:
						t     = unicode()
						t_utc = unicode()
					parameters.append(u"-AllDates={0}".format(t))
					parameters.append(u"-GPSDateStamp={0}".format(t_utc))
					parameters.append(u"-GPSTimeStamp={0}".format(t_utc))
				
				if item.keywordsEdited():
					keywords = item.keywords()
					if len(keywords) == 0: keywords = (u"",)
					for keyword in keywords:
						parameters.append(u"-Keywords={0}".format(keyword))
				
				if item.copyrightEdited():
					parameters.append(u"-Copyright=(C) {0} {1}".format(
						item.shiftedTimestamp().strftime("%Y"),
						item.copyright()
					))
				
				dct_parameters[name] = parameters
		
		# result: dictionary mapping files to sets of parameters
		# todo: calculate intersections between these sets to reduce exiftool calls
		
		dlg = FotoPreProcessorWidgets.FPPApplyChangesDialog()
		for name,parameters in dct_parameters.iteritems():
			command = [u"/usr/bin/exiftool",u"-P",u"-overwrite_original"]
			command.extend(parameters)
			command.append(name)
			dlg.addCommand(command)
		
		command = [ u"/usr/bin/exiftool",
			u"-config",unicode(os.path.join(sys.path[0],u"FotoPreProcessor.exiftool")),
			u"-P",
			u"-overwrite_original",
			u"-d",u"%Y%m%d-%H%M%S",
			u"-FileName<${DateTimeOriginal}%-2nc-${FPPModel}.%le"
		]
		command.extend(lst_all_files)
		dlg.addCommand(command)
		
		if dlg.exec_() == QtGui.QDialog.Accepted:
			# everything worked as expected
			# clear image list
			self.setDirectory()
	
	
	def resetAll(self):
		for item in self.list_images.selectedItems():
			item.resetAll()
		self.dock_geotagging.resetData()
		self.dock_timezones.resetData()
		self.dock_keywords.resetData()
		self.listImagesSelectionChanged()
	
	
	def updateResetAllAction(self):
		self.action_resetAll.setEnabled(
			self.action_resetOrientation.isEnabled() or \
			self.action_resetLocation.isEnabled() or \
			self.action_resetTimezones.isEnabled() or \
			self.action_resetKeywords.isEnabled()
		)
	
	#-----------------------------------------------------------------------
	
	def openWithTheGimp(self):
		try:
			command = [u"/usr/bin/gimp"]
			for item in self.list_images.selectedItems():
				command.append(unicode(os.path.join(self.str_path,item.filename())))
			subprocess.Popen(command)
		except:
			pass
	
	#-----------------------------------------------------------------------
	
	def configureProgram(self):
		pass



if __name__ == '__main__':
	try:
		argpath = sys.argv[1].decode(sys.getfilesystemencoding())
		argpath = os.path.expanduser(argpath)
		if not os.path.isabs(argpath):
			argpath = os.path.join(os.getcwd(),argpath)
		argpath = os.path.normpath(argpath)
	except:
		argpath = unicode()
	
	# setup Qt application
	app = QtGui.QApplication(sys.argv)
	app.setApplicationName(u"FotoPreProcessor")
	
	# initialise translation service
	system_locale = unicode(QtCore.QLocale.system().name()[0:2])
	
	qtTranslator = QtCore.QTranslator()
	qtTranslator.load(
		u"qt_"+system_locale,
		unicode(QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.TranslationsPath))
	)
	
	fppTranslator = QtCore.QTranslator()
	fppTranslator.load(
		u"FotoPreProcessor."+system_locale,
		os.path.join(sys.path[0],u"i18n")
	)
	
	app.installTranslator(qtTranslator)
	app.installTranslator(fppTranslator)
	
	# create main window and start event loop
	mainwindow = FPPMainWindow()
	mainwindow.setDirectory(argpath)
	app.exec_()

