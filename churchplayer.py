#!/usr/bin/python

import cpmodel
import sys
import time
import stat
import os

from PyQt4.QtCore import *
from PyQt4.QtGui import *

#  Show a simple message in a modal dialog box with an "OK" button.
def showMessage( text ):
   mb = QMessageBox()
   mb.setText( text )
   mb.exec_();

def add( layout, widget ):
   if isinstance( widget, QLayout ):
      layout.addLayout( widget )
   else:
      layout.addWidget( widget )

# ----------------------------------------------------------------------
class PlayerListener(QThread):
   stopped = pyqtSignal()
   started = pyqtSignal('QString')

   def __init__(self):
      QThread.__init__(self)

   def run(self):
      waited = 0
      while waited < 20 and not stat.S_ISFIFO(os.stat(cpmodel.WFIFO).st_mode):
         time.sleep(1)
         waited += 1

      if waited >= 20:
         raise ChurchPlayerError("\n\nTimeout whilst waiting to "
                                 "connect to the player process")
      else:
         fd = os.open(cpmodel.WFIFO, os.O_RDONLY)
         code = ' '
         while code != cpmodel.ENDING_CODE:
            try:
               code = os.read(fd,1)
               print( "PlayerListener received '{0}'".format(code))
               if code == cpmodel.PLAYING_CODE:
                  path = os.read(fd,1000)
                  self.started.emit( path )

               elif code == cpmodel.STOPPED_CODE:
                  self.stopped.emit()

            except OSError:
               pass


         os.close(fd)


# ----------------------------------------------------------------------
class PlayerButton(QLabel):
   size = 20
   def __init__(self,parent,enabled,enabledFile,disabledFile,id):
      QLabel.__init__(self,parent)
      self.enabledPixmap = QPixmap(enabledFile).scaledToHeight( PlayerButton.size, Qt.SmoothTransformation )
      self.disabledPixmap = QPixmap(disabledFile).scaledToHeight( PlayerButton.size, Qt.SmoothTransformation )
      self.id = id
      self.setAlignment(Qt.AlignHCenter)
      self.setFixedSize( PlayerButton.size*1.1, PlayerButton.size*1.1 )
      if enabled:
         self.enable()
      else:
         self.disable()

   def enable(self):
      self.enabled = True
      self.setPixmap(self.enabledPixmap)

   def disable(self):
      self.enabled = False
      self.setPixmap(self.disabledPixmap)

   def enterEvent(self,event):
      QApplication.setOverrideCursor(QCursor(Qt.PointingHandCursor))

   def leaveEvent(self,event):
      QApplication.restoreOverrideCursor()



# ----------------------------------------------------------------------
class PlayerWidget(QWidget):
   def __init__(self,parent,player,playable,end=cpmodel.STOP):
      QWidget.__init__(self,parent)
      self.player = player
      self.playable = playable
      self.end = end

      self.layout = QHBoxLayout()
      self.layout.setSpacing(0)
      self.layout.addStretch()

      self.playButton = PlayerButton( self, True, 'icons/Play.png',
                                      'icons/Play-disabled.png', 'Play' )
      self.playButton.mouseReleaseEvent = self.play
      self.playButton.setToolTip("Click to play {0}".format(playable.desc()))
      self.layout.addWidget(self.playButton)

      self.stopButton = PlayerButton( self, False, 'icons/Stop.png',
                                'icons/Stop-disabled.png', 'Stop' )
      self.stopButton.mouseReleaseEvent = self.stop
      self.stopButton.setToolTip("Click to stop {0}".format(playable.desc()))
      self.layout.addWidget(self.stopButton)

      self.layout.addStretch()
      self.setLayout( self.layout )
      self.setFixedSize( self.width(), self.height() )

   def play(self, event ):
      if self.playButton.enabled:
         self.playButton.disable()
         self.stopButton.enable()
         self.player.listener.stopped.connect(self.ended)
         self.player.play( self.playable, cpmodel.STOP )

   def stop(self, event):
      if self.stopButton.enabled:
         self.playButton.enable()
         self.stopButton.disable()
         self.player.stop( self.end )

   @pyqtSlot()
   def ended(self):
      if self.stopButton.enabled:
         self.playButton.enable()
         self.stopButton.disable()


# ------------------------------------------------------------------------
# ------------------------------------------------------------------------
# ------------------------------------------------------------------------

class CatItem(object):
   def __init__(self,parent,cat,irow,icol,opts,descs,t):
      self.parent = parent
      self.cat = cat
      self.irow = irow
      self.icol = icol
      self.opts = opts
      self.descs = descs
      self.type = t
      self.col = cat[ cat.colnames[icol] ]

   @staticmethod
   def create(parent,cat,irow,icol):
      (t,opts,descs) = cat.getOptions(icol)
      if t == 't':
         return CatLineEdit(parent,cat,irow,icol,opts,descs,t)

      elif t == 'i':
         return CatSpinBox(parent,cat,irow,icol,opts,descs,t)

      elif t == 'm':
         return CatComboBoxM(parent,cat,irow,icol,opts,descs,t)

      elif t == 's':
         return CatComboBoxS(parent,cat,irow,icol,opts,descs,t)

      else:
         return CatLabel(parent,cat,irow,icol,opts,descs,t)

   def widthHint(self):
      return self.sizeHint().width()

   def catStore(self, text ):
      self.col[ self.irow ] = text
      self.parent.catItemChanged( self )

class CatSpinBox(QSpinBox,CatItem):
   def __init__(self,parent,cat,irow,icol,opts,descs,t):
      QSpinBox.__init__(self,parent)
      CatItem.__init__(self,parent,cat,irow,icol,opts,descs,t)
      self.valueChanged.connect(self.valueHasChanged)

   def valueHasChanged(self, value ):
      self.catStore( str(value) )

class CatComboBoxS(QComboBox,CatItem):
   def __init__(self,parent,cat,irow,icol,opts,descs,t):
      QComboBox.__init__(self,parent)
      CatItem.__init__(self,parent,cat,irow,icol,opts,descs,t)

      curval = cat[ cat.colnames[icol] ][irow]
      icurr = -1
      i = 0
      for opt in opts:
         self.addItem(opt)
         if descs:
            self.setItemData( i, descs[i], Qt.ToolTipRole )
         if opt == curval:
            icurr = i
         i += 1

      if icurr == -1:
         self.addItem(curval)
         icurr = i

      self.setCurrentIndex( icurr )
      self.currentIndexChanged.connect(self.indexHasChanged)

   def indexHasChanged(self, item ):
      self.catStore( str(self.itemText(item)) )

class CatComboBoxM(QComboBox,CatItem):
   def __init__(self,parent,cat,irow,icol,opts,descs,t):
      QComboBox.__init__(self,parent)
      CatItem.__init__(self,parent,cat,irow,icol,opts,descs,t)

      self.curval = cat[ cat.colnames[icol] ][irow]
      self.addItem(" ")
      self.addItem("<clear>")
      i = 0
      for opt in opts:
         self.addItem(opt)
         if descs:
            self.setItemData( i+2, descs[i], Qt.ToolTipRole )
         i += 1

      self.setCurrentIndex( 0 )
      self.setEditable( True )
      self.lineEdit().setReadOnly(True)
      self.setFixedWidth(self.minimumSizeHint().width())
      self.currentIndexChanged.connect(self.indexHasChanged)

   def indexHasChanged(self, item ):
      text = self.itemText(item)
      if text == "Clear":
         self.curval = ""
      elif item != "":
         self.curval = self.curval + text
      self.catStore( str(self.curval) )
      self.setEditText(self.curval)


class CatLineEdit(QLineEdit,CatItem):

   def __init__(self,parent,cat,irow,icol,opts,descs,t):
      QLineEdit.__init__(self,parent)
      CatItem.__init__(self,parent,cat,irow,icol,opts,descs,t)
      text = cat[ cat.colnames[icol] ][irow]
      self.setText( text )
      self.setFrame(False)
      width = self.fontMetrics().boundingRect(text).width()
      self.setMinimumWidth(width)
      self.textChanged.connect(self.textHasChanged)

   def textHasChanged(self, text ):
      self.catStore( str(text) )

   def widthHint(self):
      return self.minimumWidth()


class CatLabel(QLabel,CatItem):

   def __init__(self,parent,cat,irow,icol,opts,descs,t):
      QLabel.__init__(self,parent)
      CatItem.__init__(self,parent,cat,irow,icol,opts,descs,t)
      text = cat[ cat.colnames[icol] ][irow]
      self.setText( text )
      width = self.fontMetrics().boundingRect(text).width()
      self.setMinimumWidth(width)

   def widthHint(self):
      return self.minimumWidth()



class PlayerControl(QLabel):

   def __init__(self,parent,type,record,player,row):
      super(PlayerControl, self).__init__(parent)
      self.record = record;
      self.player = player;
      self.parent = parent
      self.row = row
      self.type = type

      if type == 'p':
         handler = self.play
         tip = "Click to play {0}".format(record.title)
         self.enable()
      elif type == 's':
         handler = self.stop
         tip = "Click to stop playing {0}".format(record.title)
         self.disable()
      elif type == 'c':
         handler = self.toggleSelect
         tip = "Click to select or unselect {0}".format(record.title)
         self.disable()

      self.setAlignment(Qt.AlignHCenter)
      self.mouseReleaseEvent = handler
      self.setToolTip(tip)

   def play(self, event ):
      if self.enabled:
         self.parent.play( self.row )
         self.player.play( self.record, cpmodel.STOP )


   def stop(self, event):
      if self.enabled:
         self.parent.stop( self.row )
         self.player.stop( cpmodel.STOP )

   def toggleSelect(self, event):
      if self.enabled:
         self.parent.rowDeselect( self.row )
         self.disable()
      else:
         self.parent.rowSelect( self.row )
         self.enable()

   def enable(self):
      self.enabled = True
      self._setPixmap()

   def disable(self):
      self.enabled = False
      self._setPixmap()

   def _setPixmap(self):
      if self.type == 'p':
         if self.enabled:
            file = 'icons/Play.png'
         else:
            file = 'icons/Play-disabled.png'

      elif self.type == 's':
         if self.enabled:
            file = 'icons/Stop.png'
         else:
            file = 'icons/Stop-disabled.png'

      elif self.type == 'c':
         if self.enabled:
            file = 'icons/Select.jpg'
         else:
            file = 'icons/Select-disabled.jpg'

      else:
         file = None

      if file:
         pixmap = QPixmap(file).scaledToHeight( 20, Qt.SmoothTransformation )
         self.setPixmap(pixmap)




class CatTable(QTableWidget):
   def __init__(self, cat, controls="", player=None ):

      if player:
         ncontrol = len(controls)
      else:
         ncontrol = 0
      self.ncol = ncontrol+cat.ncol

      QTableWidget.__init__(self, cat.nrow, self.ncol )
      self.cat = cat
      self.player = player
      self.verticalHeader().setVisible(False);
      headers = QStringList()
      self.widthHints = []

      self.selectCol = -1
      for i in range(ncontrol):
         headers.append("")
         self.widthHints.append(0)
         if controls[i] == 'c':
            self.selectCol = i

      n = 0
      for key in cat.colnames:
         hitem = QString(key)
         headers.append(hitem)

         widthHint = 0
         m = 0
         for item in cat[key]:
            if cat.midifiles[ m ]:
               newitem = CatItem.create(self, cat, m, n )
               self.setCellWidget( m, n+ncontrol, newitem )
               w = newitem.widthHint()
               if w > widthHint:
                  widthHint = w
            else:
               newitem = QTableWidgetItem(item)
               newitem.setFlags( Qt.NoItemFlags )
               self.setItem( m, n+ncontrol, newitem )

            m += 1

         self.widthHints.append(widthHint)
         n += 1

      ipath = cat.colnames.index('PATH')+ncontrol
      for irow in range(cat.nrow):
         if not cat.midifiles[ irow ]:
            if ipath > 1:
               self.setSpan( irow, 0, 1, ipath )
            self.setSpan( irow, ipath + 1, 1, self.ncol-ipath-1 )
            newitem = QTableWidgetItem("<-- This appears not to be a "
                                       "standard MIDI file!" )
            self.setItem( irow, ipath+1, newitem )
            newitem.setFlags( Qt.NoItemFlags )


      self.setHorizontalHeaderLabels( headers )
      self.horizontalHeader().setMinimumSectionSize( 30 )
      self.setFocusPolicy( Qt.StrongFocus )

      if ncontrol:
         icol = 0
         for con in controls:
            for irow in range(cat.nrow):
               if cat.midifiles[ irow ]:

                  if con == "p":
                     control = PlayerWidget(self, self.player, cat.getRecord(irow))
                  elif con == "c":
                     control = PlayerControl( self, con, cat.getRecord(irow),
                                              self.player, irow  )

                  self.setCellWidget( irow, icol, control )

            icol += 1


      self.resizeColumnsToContents()
      self.resizeRowsToContents()
      self.setSelectionBehavior(QAbstractItemView.SelectRows)
      self.setSelectionMode(QAbstractItemView.NoSelection)

   def sizeHintForColumn(self,icol):
      if self.widthHints[icol] > 0:
         return self.widthHints[icol]
      else:
         return super(CatTable,self).sizeHintForColumn(icol)

   def sizeHintForRow(self,irow):
      if self.cat.midifiles[ irow ]:
         userow = irow
      else:
         userow = 0
      return super(CatTable,self).sizeHintForRow(userow)

   def selectAll(self):
      if self.selectCol > -1:
         for irow in range(self.rowCount()):
            wdg = self.cellWidget(irow, self.selectCol)
            if isinstance(wdg, PlayerControl):
               if not wdg.enabled:
                  wdg.enable()
                  self.rowSelect( irow )
      super(CatTable,self).selectAll()


   def deselectRow(self,irow):
      if self.selectCol > -1:
         wdg = self.cellWidget(irow, self.selectCol)
         if isinstance(wdg, PlayerControl):
            if wdg.enabled:
               wdg.disable()
               self.rowDeselect( irow )

   def selectRow(self,irow):
      if self.selectCol > -1:
         wdg = self.cellWidget(irow, self.selectCol)
         if isinstance(wdg, PlayerControl):
            if not wdg.enabled:
               wdg.enable()
               self.rowSelect( irow )

   def clearSelection(self):
      for irow in range(self.rowCount()):
         self.deselectRow( irow )
      super(CatTable,self).clearSelection()

   def rowSelect( self, row ):
      range = QTableWidgetSelectionRange( row, 0, row, self.ncol - 1 )
      self.setRangeSelected( range, True )

   def rowDeselect( self, row ):
      range = QTableWidgetSelectionRange( row, 0, row, self.ncol - 1 )
      self.setRangeSelected( range, False )

   def stop( self, row ):
      self.clearSelection()
      for irow in range(self.cat.nrow):
         if self.cat.midifiles[ irow ]:
            for icol in range(self.cat.ncol):
               item = self.item( irow, icol )
               if item:
                  flags = item.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled
                  item.setFlags( flags )
               else:
                  wdg = self.cellWidget( irow, icol )
                  if isinstance( wdg, PlayerControl ):
                     if wdg.type == 'p':
                        wdg.enable()
                     else:
                        wdg.disable()

   def play( self, row ):
      self.clearSelection()
      for irow in range(self.cat.nrow):
         if self.cat.midifiles[ irow ]:
            for icol in range(self.cat.ncol):
               item = self.item( irow, icol )
               if item:
                  flags = item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled
                  item.setFlags( flags )
               else:
                  wdg = self.cellWidget( irow, icol )
                  if isinstance( wdg, PlayerControl ):
                     if wdg.type == 'p':
                        wdg.disable()
                     elif irow == row:
                        wdg.enable()

   def catItemChanged(self, catitem ):
      self.selectRow( catitem.irow )



class CatWidget(QWidget):
   def __init__( self, parent, cat, headtext=None, controls=None,
                 player=None ):
      super(CatWidget, self).__init__(parent)
      self.setSizePolicy( QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding )

      self.cat = cat
      self.headtext = headtext
      self.controls = controls
      self.player = player

      self.vbox = QVBoxLayout()

      self.head = self.makeHead()
      add( self.vbox, self.head )

      self.centre = self.makeCentre()
      add( self.vbox, self.centre )

      self.foot = self.makeFoot()
      add( self.vbox, self.foot )

      self.setLayout(self.vbox)

   def makeHead(self):
      if self.headtext:
         text = self.headtext
      else:
         text = ""
      return QLabel( text )

   def makeCentre(self):
      return self.makeTable()

   def makeFoot(self):
      buttonbox = QHBoxLayout()
      self.addButtons( buttonbox )
      return buttonbox

   def makeTable(self):
      self.table = CatTable( self.cat, self.controls, self.player )
      return self.table

   def addButtons(self, buttonbox ):
      buttonbox.addStretch(1)
      ok = QPushButton('OK', self)
      ok.setToolTip("Close this dialog without any further action")
      ok.clicked.connect(self.close)
      buttonbox.addWidget( ok )




class ImportWidget(CatWidget):

   headtext = "\nEdit the cell contents in the following table to show the required values, and then select the required rows and press 'Import' to add them to the music catalogue.\n"
   dialog = None

   def __init__( self, parent, dialog, fromcat, tocat ):
      self.tocat = tocat
      self.fromcat = fromcat
      self.dialog = dialog
      self.player = parent.player
      heading = "{0} uncatalogued music files found.\n{1}".format(fromcat.nrow,self.headtext)
      super(ImportWidget, self).__init__(parent, fromcat, heading,
                                         "cps", self.player )

   def addButtons(self, buttonbox ):
      selectAll = QPushButton('Select All', self)
      selectAll.setToolTip("Select all available rows for importing")
      selectAll.clicked.connect( self.table.selectAll )
      buttonbox.addWidget( selectAll )

      deselectAll = QPushButton('Deselect All', self)
      selectAll.setToolTip("Deselect all rows")
      deselectAll.clicked.connect( self.table.clearSelection)
      buttonbox.addWidget( deselectAll )

      buttonbox.addStretch(1)

      importSelected = QPushButton('Import Selected', self)
      importSelected.setToolTip("Import selected rows into the music "
                                "catalogue, keeping this dialog open.")
      importSelected.clicked.connect(self.importSelected)
      buttonbox.addWidget( importSelected )

      importAll = QPushButton('Import All', self)
      importAll.setToolTip("Import all available rows into the music "
                           "catalogue and close this dialog")
      importAll.clicked.connect(self.importAll)
      buttonbox.addWidget( importAll )

      ok = QPushButton('OK', self)
      ok.setToolTip("Import any currently selected files into the music "
                    "catalogue and then close this dialog")
      ok.clicked.connect(self.oker)
      buttonbox.addWidget( ok )

      cancel = QPushButton('Cancel', self)
      cancel.setToolTip("Close this dialog without importing any further "
                        "files into the music catalogue")
      cancel.clicked.connect(self.closer)
      buttonbox.addWidget( cancel )

   def closer(self):
      self.player.stop( cpmodel.STOP )
      self.dialog.close()

   def oker(self):
      self.importSelected()
      self.dialog.close()

   def importAll(self):
      self.table.selectAll()
      self.importSelected()
      self.dialog.close()

   def importSelected(self):
      for selectedItem in self.table.selectionModel().selectedRows():
        irow = selectedItem.row()
        newrow = []
        for colname in self.fromcat.colnames:
           newrow.append( self.fromcat[colname][irow] )
        self.tocat.addrow( newrow )

        self.table.hideRow(irow)

      self.player.stop( cpmodel.STOP )


class ImportDialog(QDialog):

   def __init__( self, parent, fromcat, tocat ):
      super(ImportDialog, self).__init__(parent)
      self.setWindowTitle('Music importer')
      layout = QVBoxLayout()
      add( layout, ImportWidget( parent, self, fromcat, tocat ) )
      self.setLayout( layout )



class ChurchPlayer(QMainWindow):

   def __init__(self, app, cat, player ):
      super(ChurchPlayer, self).__init__()
      self.initUI( app, cat, player )

#  ---------------------------------------------------------------
#  Create the GUI.
#  ---------------------------------------------------------------
   def initUI(self, app, cat, player ):
      self.cat = cat
      self.app = app
      self.player = player

#  Set up tool tips
      QToolTip.setFont(QFont('SansSerif', 10))

#  Actions...
      exitAction = QAction(QIcon('icons/Exit.png'), '&Exit', self)
      exitAction.setStatusTip('Exit application')
      exitAction.triggered.connect(self.exit)

      openAction = QAction(QIcon('icons/Open.png'), '&Open', self)
      openAction.setStatusTip('Open an existing service or playlist')
      openAction.triggered.connect(self.open)

      saveCatAction = QAction(QIcon('icons/SaveCat.png'), '&Save Catalogue', self)
      saveCatAction.setStatusTip('Save the music catalogue to disk')
      saveCatAction.triggered.connect(self.saveCatalogue)

      scanAction = QAction( '&Scan', self)
      scanAction.setShortcut('Ctrl+I')
      scanAction.setStatusTip('Scan the music directory for uncatalogued MIDI files')
      scanAction.triggered.connect(self.scan)

#  Set up status bar
      self.statusBar()

#  Set up menu bar
      menubar = self.menuBar()
      fileMenu = menubar.addMenu('&File')
      fileMenu.addAction(openAction)
      fileMenu.addAction(exitAction)

      catMenu = menubar.addMenu('&Catalogue')
      catMenu.addAction(scanAction)
      catMenu.addAction(saveCatAction)

#  Set up the toolbar.
      toolbar = self.addToolBar('tools')
      toolbar.addAction(exitAction)
      toolbar.addAction(openAction)

#  The central widget
#      centralWidget = QWidget(self)
#      layout = QVBoxLayout()
#      centralWidget.setLayout( layout )
#      self.setCentralWidget( centralWidget )
#      add( layout, PlayerWidget( self, player,cat.getRecord(0) ) )
      pw = PlayerWidget( self, player, cat.getRecord(0) )
      self.setCentralWidget( pw )

#  Set up the main window.
      self.setWindowTitle('Church Player')
      qr = app.desktop().availableGeometry()
      wid =  0.95*qr.width()
      hgt =  0.95*qr.height()
      ax = qr.center().x() - wid/2
      ay = qr.center().y() - hgt/2
      self.setGeometry( ax, ay, wid, hgt )
      self.show()




#  Display any warnings about the catalogue.
      if len( cat.warnings ) > 0:
         mb = QMessageBox()
         mb.setText("Warnings were issued whilst reading the music "
                        "catalogue file '{0}'.".format( cat.catname ) )
         details = "\n"
         for warning in cat.warnings:
            details += "- {0}\n\n".format(warning)
         details += "\n"
         mb.setDetailedText( details )
         mb.exec_();


#  ---------------------------------------------------------------
#  Exit the application.
#  ---------------------------------------------------------------
   def exit(self, e ):
      doexit = True
      if self.cat.modified:
         ret = QMessageBox.warning(self, "Warning",
                '''The music catalogue has been modified.\nDo you want to save your changes?''',
                QMessageBox.Save, QMessageBox.Discard, QMessageBox.Cancel)
         if ret == QMessageBox.Save:
            self.cat.save()
         elif ret == QMessageBox.Cancel:
            doexit = False
      else:
         ret = QMessageBox.question(self, "Confirm Exit...",
				  "Are you sure you want to exit?",
				  QMessageBox.Yes| QMessageBox.No)
         if ret == QMessageBox.No:
            doexit = False

      if doexit:
         del self.player
         self.close()



#  ---------------------------------------------------------------
#  Save the catalogue.
#  ---------------------------------------------------------------
   def saveCatalogue(self, e ):
      result = QMessageBox.question(self, "Confirm Save...",
				  "Are you sure you want to save the catalogue?",
				  QMessageBox.Yes| QMessageBox.No)
      if result == QMessageBox.Yes:
         self.cat.save()

#  ---------------------------------------------------------------
#  Open a playlist or service.
#  ---------------------------------------------------------------
   def open(self, e ):
      print( "Opening...")


#  ---------------------------------------------------------------
#  Scan for uncatalogued MIDI files.
#  ---------------------------------------------------------------
   def scan(self, e ):
      QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
      self.statusBar().showMessage("Scanning music directory ({0}) for "
                                   "uncatalogued MIDI files...".
                                   format(self.cat.rootdir))
      newmidis = self.cat.searchForNew()
      QApplication.restoreOverrideCursor()
      self.statusBar().showMessage("")
      if newmidis:
         ed = ImportDialog(self,newmidis,self.cat)
         ed.exec_()
      else:
         showMessage("No uncatalogued MIDI files were found." )

#  ---------------------------------------------------------------
#  Main entry.
#  ---------------------------------------------------------------
def main():

    cat = cpmodel.Catalogue()
    cat.verify()
    player = cpmodel.Player()
    player.listener = PlayerListener()
    player.listener.start()
    app = QApplication(sys.argv)
    ex = ChurchPlayer( app, cat, player )
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
