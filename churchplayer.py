#!/usr/bin/python

import cpmodel
import sys
import time
import stat
import os

NSLOT = 12
SLOT_HEIGHT = 40
SLOT_PADDING = 25

from PyQt4.QtCore import *
from PyQt4.QtGui import *

#  Show a simple message in a modal dialog box with an "OK" button.
def showMessage( text ):
   mb = QMessageBox()
   mb.setText( text )
   mb.exec_();

#  Show a simple message in a modal dialog box with "Yes" and "No" buttons.
def showYesNoMessage( text, info=None ):
   mb = QMessageBox()
   mb.setText( text )
   if info:
      mb.setInformativeText(info)
   mb.setStandardButtons( QMessageBox.Yes | QMessageBox.No )
   mb.setDefaultButton(QMessageBox.Yes)
   return (mb.exec_() == QMessageBox.Yes )

#  Create a horizontal line widget.
def HLine( ):
    toto = QFrame()
    toto.setFrameShape(QFrame.HLine)
    toto.setFrameShadow(QFrame.Sunken)
    return toto

#  Add an item into a layout - either a widget or another layout.
def add( layout, widget, align=None ):
   if layout != None and widget != None:
      if isinstance( widget, QLayout ):
         layout.addLayout( widget )
      elif align:
         layout.addWidget( widget, alignment=align )
      else:
         layout.addWidget( widget )



# ----------------------------------------------------------------------
class MetreChooser(QWidget):
   def __init__( self, parent, player, store=False ):
      super(MetreChooser, self).__init__(parent)
      self.store = store
      self.ignore = False
      self.player = player

      layout = QVBoxLayout()
      self.setLayout( layout )
      self.cb = QComboBox(parent)

      self.cb.addItem('(unknown)')
      for metre in self.player.cat.metres:
         self.cb.addItem(metre)
      self.cb.setToolTip('Select the metre of the music')

      self.cb.currentIndexChanged.connect( self.metreChanged )
      layout.addWidget( self.cb )

   def metreChanged(self):
      if not self.ignore:
         newval = self.cb.currentText()
         if newval == "(unknown)":
            newval = None

         if self.store:
            if self.player.cat['METRE'][self.irow] != newval:
               self.player.cat['METRE'][self.irow] = newval
               self.player.modified = True

   def setFromRow( self, irow, map ):
      self.ignore = True
      self.irow = irow

      if irow in map:
         self.oldval = map[ irow ]
      else:
         self.oldval = self.player.cat['METRE'][irow]
      if not self.oldval:
         self.oldval = '(unknown)'
      self.cb.setCurrentIndex( self.cb.findText(self.oldval))

      self.ignore = False
      return self.oldval

   def saveToMap( self, mymap ):
      newval = self.cb.currentText()
      if newval == "(unknown)":
         newval = None
      if newval != self.oldval:
         mymap[self.irow] = newval

# ----------------------------------------------------------------------
class KeyboardChooser(QWidget):
   def __init__( self, parent, player, playerwidget=None, store=False ):
      super(KeyboardChooser, self).__init__(parent)
      self.store = store
      self.ignore = False
      self.player = player
      self.pw = playerwidget

      layout = QVBoxLayout()
      self.cb = QComboBox(parent)
      self.gminvmap = {}
      self.gmfwdmap = {}

      cbindex = 0
      for kbd in cpmodel.instrumentNames:
         self.cb.addItem( kbd )
         gm = cpmodel.instruments[kbd]
         if gm == cpmodel.DEFAULT_INSTRUMENT:
            self.defindex = cbindex
         self.gmfwdmap[gm] = cbindex
         self.gminvmap[cbindex] = gm
         cbindex += 1

      self.setEnabled( False )
      self.cb.setFixedWidth(230)
      self.cb.setFixedHeight(SLOT_HEIGHT )
      self.cb.currentIndexChanged.connect( self.kbdChanged )
      layout.addWidget( self.cb )
      self.setLayout( layout )

   def setpw(self,playerwidget):
      self.pw = playerwidget

   def setEnabled(self,enabled):
      if enabled:
         self.cb.setEnabled( True )
         self.cb.setToolTip("Choose the type of keyboard instrument to use")
         self.cb.setItemText( self.defindex, "Original" )
      else:
         self.cb.setItemText( self.defindex, "Band" )
         self.cb.setCurrentIndex( self.defindex )
         self.cb.setEnabled( False )
         self.cb.setToolTip("Band instruments cannot be changed")

   def kbdChanged(self):
      if not self.ignore:
         gm = self.gminvmap[ self.cb.currentIndex() ]
         if self.store:
            if self.player.cat['PROG0'][self.irow] != gm:
               self.player.cat['PROG0'][self.irow] = gm
               self.player.cat.modified = True
         self.player.player.sendProg0( gm )
         self.pw.setProg0( gm )

   def setFromRow( self, irow, map=None ):
      self.ignore = True
      self.irow = irow

      if self.player.cat['INSTR'][irow] == "KEYBD":
         if map and irow in map:
            self.oldval = map[ irow ]
         else:
            self.oldval =  int( self.player.cat['PROG0'][irow] )

         self.setEnabled( True )
         self.cb.setCurrentIndex( self.gmfwdmap[ self.oldval ] )

      else:
         self.setEnabled( False )
         self.oldval = cpmodel.DEFAULT_INSTRUMENT

      self.ignore = False
      return self.oldval

   def setFromPlayable( self, playable, map=None ):
      if playable:
         return self.setFromRow( playable.irow, map )
      else:
         self.setEnabled( False )
         self.oldval = cpmodel.DEFAULT_INSTRUMENT

   def setFromRecord( self, record, map ):
      self.ignore = True
      self.irow = None

      if self.player.cat['INSTR'][irow] == "KEYBD":
         if irow in map:
            self.oldval = map[ irow ]
         else:
            self.oldval =  int( self.player.cat['PROG0'][irow] )

         self.setEnabled( True )
         self.cb.setCurrentIndex( self.gmfwdmap[ self.oldval ] )

      else:
         self.setEnabled( False )
         self.oldval = cpmodel.DEFAULT_INSTRUMENT

      self.ignore = False
      return self.oldval

   def saveToMap( self, mymap ):
      newval = self.gminvmap[ self.cb.currentIndex()]
      if newval != self.oldval:
         mymap[self.irow] = newval

# ----------------------------------------------------------------------
class SliderPanel(QWidget):
   def __init__( self, parent, player, playerwidget=None, store=False ):
      super(SliderPanel, self).__init__(parent)
      self.player = player

      sliders =  QHBoxLayout()
      sliders.addStretch()

      sl1 = QVBoxLayout()
      self.volumeslider = CPSlider( self, self.player, 'VOLUME', -99, 99, 1,
                                    playerwidget, store )
      self.volumeslider.setToolTip("Change the playback volume")
      sl1.addWidget( self.volumeslider )
      sl1.addWidget( QLabel("Volume" ) )
      sliders.addLayout( sl1 )

      sliders.addStretch()

      sl2 = QVBoxLayout()
      self.temposlider = CPSlider( self, self.player, 'SPEED', -99, 99, 1,
                                   playerwidget, store )
      self.temposlider.setToolTip("Change the playback speed")
      sl2.addWidget( self.temposlider )
      sl2.addWidget( QLabel("Tempo" ) )
      sliders.addLayout( sl2 )

      sliders.addStretch()

      sl3 = QVBoxLayout()
      self.pitchslider = CPSlider( self, self.player, 'TRANS', -7, 7, 1,
                                   playerwidget, store )
      self.pitchslider.setToolTip("Change the playback pitch")
      sl3.addWidget( self.pitchslider )
      sl3.addWidget( QLabel("Pitch" ) )
      sliders.addLayout( sl3 )

      sliders.addStretch()
      self.setLayout( sliders )

   def setFromPlayable( self, playable, map=None ):
      if playable:
         self.setFromRow( playable.irow, map )
      else:
         self.setFromRow( -1, map )

   def setFromRow( self, irow, map=None ):
      self.volumeslider.setFromRow( irow, map )
      self.temposlider.setFromRow( irow, map )
      self.pitchslider.setFromRow( irow, map )

   def setPlayerWidget( self, playerWidget ):
      self.volumeslider.pw = playerWidget
      self.temposlider.pw = playerWidget
      self.pitchslider.pw = playerWidget

# ----------------------------------------------------------------------
class ClassifyDialog(QDialog):

   def __init__( self, parent, player ):
      super(ClassifyDialog, self).__init__(parent)
      self.setWindowTitle('Music classifier')
      self.setMinimumWidth(800)
      self.setFocusPolicy( Qt.StrongFocus )
      self.cat = player.cat
      self.player = player
      self.irow = 1
      self.checks = {}
      self.changes = {}
      self.prog0 = {}
      self.trans = {}
      self.volume = {}
      self.tempo = {}
      self.metre = {}
      self.pw = PlayerWidget( self, player, self.irow-1 )
      hgt = 40

      layout = QVBoxLayout()
      layout.setSpacing(16)

      add( layout, QLabel("\nEnter or change the classification tags, etc, for "
           "each item of music in the catalogue.\n") )

      bar = QHBoxLayout()
      self.prev = QToolButton()
      self.prev.setIcon( QIcon('icons/Left.png') )
      self.prev.setToolTip("Move back to the previous item in the catalogue")
      self.prev.clicked.connect(self.prever)
      self.prev.setIconSize(QSize(hgt,hgt))
      self.prev.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
      self.prev.setEnabled( False )
      bar.addWidget( self.prev )

      self.spin = QSpinBox( self )
      self.spin.setMinimum( 1 )
      self.spin.setMaximum( self.cat.nrow )
      self.spin.setToolTip("Type the item number to jump to")
      self.spin.setFixedHeight( hgt )
      self.spin.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
      self.spin.setValue(self.irow)
      self.spin.valueChanged.connect( self.changeRow )

      bar.addWidget(self.spin)
      bar.addStretch()

      self.desc = QLabel( " " )
      self.desc.setFixedHeight( hgt )
      bar.addWidget( self.desc, Qt.AlignLeft )
      bar.addStretch()

      bar.addWidget( self.pw, Qt.AlignRight )

      self.next = QToolButton()
      self.next.setIcon( QIcon('icons/Right.png') )
      self.next.setToolTip("Move on to the next item in the catalogue")
      self.next.clicked.connect(self.nexter)
      self.next.setIconSize(QSize(hgt,hgt))
      self.next.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
      bar.addWidget( self.next, Qt.AlignRight )

      layout.addLayout( bar, Qt.AlignLeft )

      mainlayout = QHBoxLayout()
      mainlayout.addWidget(QLabel("  "))
      cblayout = QVBoxLayout()
      cblayout.setSpacing(0)
      for (name,desc) in zip(self.cat.tagnames,self.cat.tagdescs):
         cb = QCheckBox( desc, self )
         cb.setTristate( False )
         self.checks[name] = cb
         cblayout.addWidget( cb, Qt.AlignLeft )
      mainlayout.addLayout(cblayout)
      mainlayout.addStretch()

      ilayout = QVBoxLayout()
      self.kbdChooser = KeyboardChooser( self, player, playerwidget=self.pw )
      ilayout.addWidget(self.kbdChooser)
      self.metreChooser = MetreChooser( self, player )
      ilayout.addWidget(self.metreChooser)

      self.sliders = SliderPanel(self, player, playerwidget=self.pw )
      ilayout.addWidget(self.sliders)
      mainlayout.addLayout( ilayout )

      layout.addLayout(mainlayout)

      buttonbar = QHBoxLayout()
      cancel = QPushButton('Cancel', self)
      cancel.setToolTip("Close this window without saving any changes")
      cancel.clicked.connect(self.canceler)
      cancel.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
      buttonbar.addWidget( cancel, Qt.AlignLeft )

      ok = QPushButton('OK', self)
      ok.setToolTip("Save changes and close this window")
      ok.clicked.connect(self.oker)
      ok.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
      buttonbar.addWidget( ok, Qt.AlignRight )

      layout.addLayout( buttonbar )
      self.setLayout( layout )
      self.pw.setFocus()
      self.setDesc()

   def keyPressEvent(self, e):
      if e.key() == Qt.Key_Space or e.key() == Qt.Key_Right:
         self.nexter()
      elif e.key() == Qt.Key_Left:
         self.prever()

   def changeRow( self, newrow ):
      self.kbdChooser.saveToMap( self.prog0 )
      self.metreChooser.saveToMap( self.metre )
      self.sliders.pitchslider.saveToMap( self.trans )
      self.sliders.volumeslider.saveToMap( self.volume )
      self.sliders.temposlider.saveToMap( self.tempo )

      if newrow != self.irow and newrow >= 1 and newrow <= self.cat.nrow:
         self.storeTags()
         self.irow = newrow
         self.setDesc()
         self.spin.setValue(self.irow)
         if self.irow == 1:
            self.prev.setEnabled( False )
            self.next.setEnabled( True )
         elif self.irow == self.cat.nrow:
            self.prev.setEnabled( True )
            self.next.setEnabled( False )
         else:
            self.prev.setEnabled( True )
            self.next.setEnabled( True )

   def prever(self):
      self.changeRow( self.irow - 1 )

   def nexter(self):
      self.changeRow( self.irow + 1 )

   def oker(self):
      self.closer(True)

   def canceler(self):
      self.closer(False)

   def closer(self,save):
      self.pw.stop(None)
      self.storeTags()
      if self.saveChanges(save):
         self.pw.finish()
         self.close()

   def saveChanges(self,save):
      doexit = True
      if save:
         self.kbdChooser.saveToMap( self.prog0 )
         self.metreChooser.saveToMap( self.metre )
         self.sliders.pitchslider.saveToMap( self.trans )
         self.sliders.volumeslider.saveToMap( self.volume )
         self.sliders.temposlider.saveToMap( self.tempo )
         if len(self.changes) > 0 or len(self.prog0) or len(self.metre) > 0 or len(self.trans) or len(self.volume)  or len(self.tempo) > 0:
            ret = QMessageBox.warning(self, "Warning", '''Save changes?''',
                                      QMessageBox.Save, QMessageBox.Discard,
                                      QMessageBox.Cancel)
            if ret == QMessageBox.Save:
               for irow in self.changes:
                  self.cat['TAGS'][irow] = self.changes[irow]
               for irow in self.prog0:
                  self.cat['PROG0'][irow] = str(self.prog0[irow])
               for irow in self.metre:
                  self.cat['METRE'][irow] = str(self.metre[irow])
                  if self.cat['METRE'][irow] == '(unknown)':
                     self.cat['METRE'][irow] = None
               for irow in self.trans:
                  self.cat['TRANS'][irow] = str(self.trans[irow])
               for irow in self.volume:
                  self.cat['VOLUME'][irow] = str(self.volume[irow])
               for irow in self.tempo:
                  self.cat['SPEED'][irow] = str(self.tempo[irow])
               self.cat.modified = True
            elif ret == QMessageBox.Cancel:
               doexit = False
      else:
         if len(self.changes) > 0:
            ret = QMessageBox.warning(self, "Warning", '''Discard changes?''',
                                      QMessageBox.Discard, QMessageBox.Cancel)
            if ret == QMessageBox.Cancel:
               doexit = False
      return doexit

   def storeTags(self):
      store = False

      newtags = ""
      for name in self.cat.tagnames:
         cb =  self.checks[name]
         if cb.isChecked():
            newtags += name

      newtags = ''.join(sorted(newtags))

      oldtags = self.cat['TAGS'][self.irow-1]
      if oldtags:
         oldtags = ''.join(sorted(oldtags))
         if newtags != oldtags:
            store = True
      elif newtags != "":
         store = True

      if store:
         self.changes[self.irow-1] = newtags

   def setDesc(self):
      self.pw.stop(None)
      gm = self.kbdChooser.setFromRow( self.irow-1, self.prog0 )
      metre = self.metreChooser.setFromRow( self.irow-1, self.metre )
      trans = self.sliders.pitchslider.setFromRow( self.irow-1, self.trans )
      volume = self.sliders.volumeslider.setFromRow( self.irow-1, self.volume )
      tempo = self.sliders.temposlider.setFromRow( self.irow-1, self.tempo )

      self.pw.setPlayable( self.irow-1, prog0=gm, trans=trans,
                           volume=volume, tempo=tempo )

      tags = self.cat['TAGS'][self.irow-1]
      for name in self.cat.tagnames:
         cb =  self.checks[name]
         if tags and name in tags:
            cb.setChecked( True )
         else:
            cb.setChecked( False )

      book = self.cat['BOOK'][self.irow-1]
      number = self.cat['NUMBER'][self.irow-1]
      title = self.cat['TITLE'][self.irow-1]
      tune = self.cat['TUNE'][self.irow-1]
      if tune and tune.strip() != "":
         self.desc.setText( "{0}  {1}  '{2}'  ({3})".format(book,number,title,tune) )
      else:
         self.desc.setText( "{0}  {1}  '{2}'".format(book,number,title) )




# ----------------------------------------------------------------------
class SearchDialog(QDialog):

   def __init__( self, parent, player, target ):
      super(SearchDialog, self).__init__(parent)
      self.pwlist = []
      self.cblist = {}
      self.target = target
      self.player = player
      self.setWindowTitle('Search for music')
      self.matchingRows = []
      layout = QVBoxLayout()
      add( layout, QLabel("\nEnter values into one or more of the following "
                          "boxes and then press 'Search' to find matching "
                          "music.\nClick on the check box at the left end "
                          "of the required matching items and press 'OK' "
                          "to store it as an item in the service.\n") )
      add( layout, self.makeUpper() )
      add( layout, self.makeMiddle() )
      add( layout, self.makeLower() )
      self.setLayout( layout )

   def makeUpper(self):
      layout = QHBoxLayout()
      self.searchItems = []
      icol = -1
      self.istf = -1
      self.bookitem = None

      for colname in self.player.cat.colnames:
         icol += 1
         if self.player.cat.colsearchable[icol]:
            collabel = QLabel( colname[:1].upper() + colname[1:].lower() + ":" )
            collabel.setToolTip( self.player.cat.coldescs[icol] )
            colitem = CatItem.create(self, self.player.cat, None, icol,
                                     editable=True )
            if colname.lower() == "book":
               self.bookitem = colitem
               self.istf = colitem.findText("STF")
               if self.istf >= 0:
                  colitem.setCurrentIndex( self.istf )

            self.searchItems.append( colitem )
            add( layout, collabel )
            add( layout, colitem )
            layout.addStretch( )

      spacer = QWidget()
      spacer.setFixedWidth(50)
      layout.addWidget( spacer )

      clear = QPushButton('Clear', self)
      clear.setToolTip("Reset the search parameters")
      clear.clicked.connect(self.clearer)
      clear.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
      clear.setAutoDefault(False)
      layout.addWidget( clear, Qt.AlignRight )

      search = QPushButton('Search', self)
      search.setToolTip("Search for music matching the properties selected above")
      search.clicked.connect(self.searcher)
      search.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
      search.setAutoDefault(True)
      layout.addWidget( search, Qt.AlignRight )

#      for item in self.searchItems:
#         if hasattr( item, 'returnPressed'):
#            item.returnPressed.connect( search.click )

      return layout

   def makeMiddle(self):
      self.scarea = QScrollArea()
      self.scarea.setMinimumSize(800,400)
      return self.scarea

   def makeLower(self):
      layout = QHBoxLayout()

      cancel = QPushButton('Cancel', self)
      cancel.setToolTip("Close this window without selecting any music")
      cancel.clicked.connect(self.closer)
      cancel.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
      layout.addWidget( cancel, Qt.AlignRight )

      ok = QPushButton('OK', self)
      ok.setToolTip("Close this window accepting the currently selected music")
      ok.clicked.connect(self.oker)
      ok.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
      layout.addWidget( ok, Qt.AlignRight )

      return layout

   def closer(self):
      self.player.stopper(None)
      self.close()

   def oker(self):
      nmatch = len(self.matchingRows)
      if nmatch > 0:
         rows = []
         for cb in self.cblist:
            if cb.isChecked():
               rows.append( self.cblist[cb] )
         if len(rows) == 0:
            if showYesNoMessage( "No music has been selected.", "Select all "
                                 "display music before closing?" ):
               for cb in self.cblist:
                  rows.append( self.cblist[cb] )
         if len(rows) > 0:
            self.target.setPlaylist( self.player.cat.makePlaylist( rows ) )

      self.closer()

   def clearer(self):
      self.clearResults()
      for item in self.searchItems:
         item.clear()
      if self.istf >= 0:
         self.bookitem.setCurrentIndex( self.istf )

   def searcher(self):
      right = QWidget()
      results = QGridLayout()
      results.setSpacing(15)
      right.setLayout( results )

      searchVals = []
      searchCols = []
      for item in self.searchItems:
         searchVals.append( item.value )
         searchCols.append( item.icol )

      self.matchingRows = []
      for cb in self.cblist:
         if cb.isChecked():
            self.matchingRows.append( self.cblist[cb] )
      nold = len( self.matchingRows )

      self.clearResults()

      newrows = self.player.cat.search( searchVals, searchCols )
      if len( newrows ) == 0:
         showMessage("No matching music found !")
      else:
         self.matchingRows.extend(newrows)

      if len( self.matchingRows ) > 0:
         self.checkbox = []
         j = 0
         icheck = 0;
         for irow in self.matchingRows:
            cb = QCheckBox()
            cb.setToolTip("Click to include this row in the service slot")
            if icheck < nold:
               cb.setChecked(True)
            icheck += 1

            self.cblist[cb] = irow
            self.checkbox.append( cb )
            results.addWidget(cb, j, 0 )
            i = 1
            for (val,tip) in self.player.cat.getUserValues( irow ):
               lab = QLabel(val)
               if tip:
                  lab.setToolTip(tip)
               results.addWidget(lab, j, i )
               i += 1

            pw = PlayerWidget( self, self.player, irow, size=28 )
            results.addWidget( pw, j, i )
            self.pwlist.append(pw)
            i += 1

            lab = QLabel('({0})'.format(irow+1))
            lab.setToolTip("Index within music catalogue" )
            results.addWidget(lab, j, i )
            j += 1


      self.scarea.setWidget( right )

   def clearResults(self):

      for pw in self.pwlist:
         pw.finish()
      self.pwlist = []
      self.cblist = {}

      oldwidget = self.scarea.takeWidget()
      if oldwidget:
         oldwidget.deleteLater()



# ----------------------------------------------------------------------
class Service(QFrame):
   def __init__(self,parent,player,sliderpanel):
      QFrame.__init__(self,parent)
      self.setFrameStyle( QFrame.Box )
      self.player = player
      self.sliderpanel = sliderpanel
      self.tempfile = "tempService"
      self.items = []
      self.changed = False
      self.path = None

      self.grid = QVBoxLayout()
      for i in range(NSLOT):
         item = ServiceItem( self, player, sliderpanel )
         self.grid.addWidget( item )

      self.grid.addStretch( 10 )
      self.setLayout( self.grid )
      self.setStyleSheet("background-color:#eeeeee;")
      self.setFixedHeight( NSLOT*(SLOT_HEIGHT+SLOT_PADDING) )

   def uper(self, item ):
      self.changed = True
      print("up ",item)

   def downer(self, item ):
      self.changed = True
      print("down ",item)

   def remover(self, item ):
      if self.grid.count() == 1:
         showMessage("You are not allowed to remove the last slot")
      else:
         sindex = self.grid.indexOf( item )
         if sindex >= 0:
            self.changed = True
            self.grid.takeAt( sindex )
            self.grid.invalidate()
            self.grid.repaint()
            self.grid.update()
         else:
            print("!!!!  service.remover: serviceitem not found")

   def adder(self, item ):
      if self.grid.count() >= NSLOT:
         showMessage("No room for any more slots")
      else:
         sindex = self.grid.indexOf( item )
         if sindex >= 0:
            self.addItemAt( sindex )
         else:
            print("!!!!  service.adder: serviceitem not found")

   def addItemAt(self, sindex ):
      if sindex < 0:
         sindex = self.grid.count()
      self.changed = True
      item = ServiceItem( self, self.player, self.sliderpanel )
      self.grid.insertWidget( sindex, item )
      self.grid.invalidate()
      self.grid.repaint()
      self.grid.update()
      return item

   def saveTemp(self):
      print("Service.saveTemp() not yet implemented!!")

   def save(self):
      if self.path:
         defpath = self.path
      else:
         defpath = "services/"
      self.path = QFileDialog.getSaveFileName(self, "Save service",
                        defpath, "Images (*.srv)");

      if self.path:
         self.path = str( self. path )
         if not self.path.endswith(".srv"):
            self.path += ".srv"
         self.saveAs(self.path)

   def saveAs( self, path ):
      fd = open( path, "w" );
      for sindex in range(self.grid.count()):
         item = self.grid.itemAt( sindex ).widget()
         if item and isinstance( item, ServiceItem ):
            fd.write(str(item)+"\n")
      fd.close()

   def loadFrom( self, path ):
      fd = open( path, "r" );
      sindex = 0
      for line in fd:
         line = line.strip()

         item = None
         while not item or not isinstance( item, ServiceItem ):
            if sindex < self.grid.count():
               item = self.grid.itemAt( sindex ).widget()
            else:
               item = addItemAt( -1 )
            sindex += 1

         if line:
            rows = []
            for srow in line.split(","):
               rows.append( int( srow ) )
            item.setPlaylist( self.player.cat.makePlaylist( rows ) )

      fd.close()

# ----------------------------------------------------------------------
class PanicButton(QPushButton):
   def __init__(self,parent,player,service):
      QPushButton.__init__( self, "Don't PANIC !!", parent )
      self.setToolTip("Click to restart churchplayer if things go wrong")
      self.clicked.connect( self.panic )
      self.service = service

   def panic(self):
      self.service.saveTemp()
      os.execl( "/bin/sh", "-c", "./run_churchplayer", self.service.tempfile )


# ----------------------------------------------------------------------
class CPSlider(QWidget):
   def __init__(self, parent, player, colname, vmin, vmax, vstep, playerwidget=None, store=False ):
      QWidget.__init__(self,parent)

      self.slider = QSlider(Qt.Vertical,parent)
      self.slider.setMinimum(vmin)
      self.slider.setMaximum(vmax)
      self.slider.setValue(vmin)
      self.slider.setSingleStep(vstep)
      self.slider.setPageStep(vstep)
      self.slider.valueChanged.connect( self.changeSlide )

      self.spin = QSpinBox( self )
      self.spin.setMinimum( vmin )
      self.spin.setMaximum( vmax )
      self.spin.setFixedHeight( 30 )
      self.spin.setFixedWidth( 55 )
      self.spin.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
      self.spin.setValue( vmin )
      self.spin.valueChanged.connect( self.changeSpin )

      layout = QVBoxLayout()
      layout.addWidget( self.slider )
      layout.addWidget( self.spin )
      self.setLayout( layout )

      self.colname = colname
      self.player = player
      self.store = store
      self.pw = playerwidget
      self.ignore = False
      self.irow = None
      self.oldval = None

   def changeSlide(self):
      if not self.ignore:
         newval = self.slider.value()
         self.spin.setValue(newval)
         self.changer(newval)

   def changeSpin(self):
      if not self.ignore:
         newval = self.spin.value()
         self.slider.setValue(newval)
         self.changer(newval)

   def changer(self,newval):
         if self.store:
            if self.player.cat[self.colname][self.irow] != newval:
               self.player.cat[self.colname][self.irow] = newval
               self.player.modified = True
         self.player.player.sendRT( self.colname, newval )
         self.pw.setRT( self.colname, newval )

   def setFromRow( self, irow, map=None ):
      self.ignore = True
      self.irow = irow
      if irow < 0:
         self.oldval = 0
      elif map and irow in map:
         self.oldval = map[ irow ]
      else:
         self.oldval =  int( self.player.cat[self.colname][irow] )

      self.slider.setValue( self.oldval )
      self.spin.setValue( self.oldval )
      self.ignore = False
      return self.oldval

   def saveToMap( self, mymap ):
      newval = self.slider.value()
      if self.irow >= 0 and newval != self.oldval:
         mymap[self.irow] = newval


# ----------------------------------------------------------------------
class ServiceItem(QWidget):
   def __init__(self,parent,player,sliderpanel):
      QWidget.__init__(self,parent)

      self.service = parent
      self.player = player
      self.sliderpanel = sliderpanel
      self.kbdChooser = KeyboardChooser( self, player, store=True  )
      self.playlist = None
      self.clear = PlayerButton( self, True, True, 'icons/empty.png',
                                 None, self.clearer, 20, "Empty this slot" )
      self.up = PlayerButton( self, True, True, 'icons/arrow-up.png',
                              None, self.uper, 20, "Move this slot up"  )
      self.down = PlayerButton( self, True, True, 'icons/arrow-down.png',
                                None, self.downer, 20, "Move this slot down"  )
      self.remove = PlayerButton( self, True, True, 'icons/cross.png',
                                  None, self.remover, 20, "Delete this slot"  )
      self.add = PlayerButton( self, True, True, 'icons/Plus.png',
                               None, self.adder, 20, "Add a new slot before this slot"  )
      self.pw = PlayerWidget(self,player,stop=False,sliders=sliderpanel,
                             kbdChooser=self.kbdChooser)
      self.kbdChooser.setpw( self.pw )


      self.desc = QLabel("Click here to choose music", self )
      self.desc.setFixedWidth(600)
      self.desc.setFixedHeight(SLOT_HEIGHT)
      self.desc.setToolTip("The music played when the play-button is clicked")
      self.desc.mouseReleaseEvent = self.musicChooser
      self.desc.setFrameStyle( QFrame.Panel | QFrame.Sunken )

      layout = QHBoxLayout()
      layout.addWidget( self.pw, 1, Qt.AlignLeft )
      layout.addWidget( self.desc, 10, Qt.AlignLeft )
      layout.addWidget( self.kbdChooser, 1 )
      layout.addWidget( self.clear, 1, Qt.AlignRight )
      layout.addWidget( self.up, 1, Qt.AlignRight )
      layout.addWidget( self.down, 1, Qt.AlignRight )
      layout.addWidget( self.remove, 1, Qt.AlignRight )
      layout.addWidget( self.add, 1, Qt.AlignRight )
      self.setLayout( layout )

   def clearer(self, event ):
      self.service.changed = True
      self.setPlaylist( None )

   def uper(self, event ):
      self.service.changed = True
      self.service.uper( self )

   def downer(self, event ):
      self.service.changed = True
      self.service.downer( self )

   def remover(self, event ):
      self.service.changed = True
      self.pw.finish()
      self.service.remover( self )

   def adder(self, event ):
      self.service.changed = True
      self.service.adder( self )

   def musicChooser(self, event):
      if not self.playlist:
         ed = SearchDialog(self,self.player,self)
         ed.exec_()
      else:
         self.kbdChooser.setFromPlayable( self.playlist )
         self.sliderpanel.setFromPlayable( self.playlist )

   def setPlaylist( self, playlist ):
      self.playlist = playlist
      self.pw.setPlayable( playlist )
      if playlist != None:
         self.desc.setText( self.playlist.desc() )
         self.kbdChooser.setFromPlayable( playlist )
         self.sliderpanel.setFromPlayable( playlist )
      else:
         self.desc.setText("Click here to choose music" )
         self.kbdChooser.setFromPlayable( None )
         self.sliderpanel.setFromPlayable( None )
      self.service.changed = True

   def __str__(self):
      result = None
      if self.playlist:
         for record in self.playlist:
            if result:
               result = "{0},{1}".format(result,record.irow)
            else:
               result = "{0}".format(record.irow)
      else:
         result = ""
      return result

# ----------------------------------------------------------------------
class PlayController(QWidget):
   def __init__(self,parent,player,cat):
      QWidget.__init__(self,parent)
      self.player = player
      self.cat = cat
      self.playing = False
      self.playQueue = []
      player.listener.stopped.connect(self.ended)
      self.playButtons = []
      self.stopButtons = []
      self.fadeButtons = []
      self.sliderPanels = []
      self.kbdChooser = None

      layout = QHBoxLayout()

      self.stop = PlayerButton( self, True, False, 'icons/Stop.png',
                                'icons/Stop-disabled.png', self.stopper )
      self.stop.setToolTip("Stop the currently playing music abruptly")
      layout.addWidget( self.stop )

      self.fade = PlayerButton( self, True, False, 'icons/Fade.png',
                                'icons/Fade-disabled.png', self.fader )
      self.fade.setToolTip("Fade out the currently playing music slowly")
      layout.addWidget( self.fade )

      self.setLayout( layout )

   def addClient(self,client):
      if isinstance(client,PlayerWidget):
         self.playButtons.append( client.playButton )
         if client.stopButton:
            self.stopButtons.append( client.stopButton )
         if client.fadeButton:
            self.fadeButtons.append( client.fadeButton )
      elif isinstance(client,SliderPanel):
         self.sliderPanels.append( client )

   def setKbdChooser( self, chooser ):
      self.kbdChooser = chooser

   def removeClient(self,client):
      if isinstance(client,PlayerWidget):
         self.playButtons.remove( client.playButton )
         if client.stopButton:
            self.stopButtons.remove( client.stopButton )
         if client.fadeButton:
            self.fadeButtons.remove( client.fadeButton )
      elif isinstance(client,SliderPanel):
         self.sliderPanels.remove( client )

   def playMusic(self, playwid ):
      if not self.playing and playwid.playable:
         for playbutton in self.playButtons:
            playbutton.disable()

         for stopbutton in self.stopButtons:
            if stopbutton != playwid.stopButton:
               stopbutton.disable()
         if playwid.stopButton:
            playwid.stopButton.enable()

         for fadebutton in self.fadeButtons:
            if fadebutton != playwid.fadeButton:
               fadebutton.disable()
         if playwid.fadeButton:
            playwid.fadeButton.enable()

         self.stop.enable()
         self.fade.enable()

         if isinstance(playwid.playable,cpmodel.Record):
            self.playQueue.append( playwid.playable )
         elif isinstance(playwid.playable,cpmodel.Playlist):
            for record in playwid.playable:
               self.playQueue.append( record )
         else:
            raise ChurchPlayerError("\n\nPlayController.playMusic: "
                        "playable is neither a Record nor a PlayList")

         self.playNextRecord()

   def playNextRecord(self ):
      if self.playQueue:
         record = self.playQueue.pop(0)
         if self.sliderPanels:
            for span in self.sliderPanels:
               span.setFromRow( record.irow )
         if  self.kbdChooser:
            self.kbdChooser.setFromRow( record.irow )
         self.player.play( record )
         self.playing = True

   def stopMusic(self):
      self.playQueue = []
      if self.playing:
         self.player.stop( cpmodel.STOP )

   def fadeMusic(self):
      self.playQueue = []
      if self.playing:
         self.player.stop( cpmodel.FADE )


   @pyqtSlot()
   def ended(self):
      if self.playing:
         if self.playQueue:
            self.playNextRecord()
         else:
            for playbutton in self.playButtons:
               playbutton.enable()

            for stopbutton in self.stopButtons:
               stopbutton.disable()

            for fadebutton in self.fadeButtons:
               fadebutton.disable()

            self.stop.disable()
            self.fade.disable()

            self.playing = False

   def stopper(self, event ):
      self.stopMusic()

   def fader(self, event ):
      self.fadeMusic()


# ----------------------------------------------------------------------
class MainWidget(QWidget):
   def __init__( self, parent, player, cat ):
      QWidget.__init__( self, parent )
      self.player = player
      sliders = SliderPanel( self, player, store=True )

      layout = QHBoxLayout()

      leftpanel = QVBoxLayout()
      leftpanel.setContentsMargins( 30, 10, 30, 10 )
      self.service = Service( self, self.player, sliders )
      leftpanel.addWidget( self.service )

      stopetc = QHBoxLayout()
      stopetc.addWidget( self.player )
      stopetc.addStretch()
      stopetc.addWidget( PanicButton( self, self.player, self.service ) )
      leftpanel.addLayout( stopetc )
      leftpanel.addStretch()

      layout.addLayout( leftpanel )

      rightpanel = QVBoxLayout()

      player.addClient( sliders )
      rightpanel.addWidget( sliders )
      layout.addLayout( rightpanel )

      self.setLayout( layout )


# ----------------------------------------------------------------------
class RecordForm(QWidget):
   def __init__(self,parent,dialog,player,cat,irow,editable=False,header=None,rowlist=None):
      QWidget.__init__(self,parent)
      self.player = player
      self.cat = cat
      self.rowlist = rowlist
      self.header = header
      self.editable = editable
      self.dialog = dialog
      self.setIrow( irow )

      vbox = QVBoxLayout()
      add( vbox, self.makeHead() )
      add( vbox, HLine() )
      add( vbox, self.makeBody() )
      add( vbox, self.makeControls() )
      add( vbox, HLine() )
      add( vbox, self.makeFoot() )
      self.setLayout( vbox )
      self.setSizePolicy( QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding )

   def setIrow( self, irow ):
      self.irow = irow
      self.record = self.cat.getRecord( irow )

   def makeHead(self):
      if self.header:
         return QLabel( self.header )
      else:
         return None

   def makeBody(self):
     self.form = QFormLayout()
     self.fillForm()
     return self.form

   def makeControls(self):
      hbox = QHBoxLayout()
      self.playWidget = PlayerWidget(self,self.player,self.record)
      add( hbox, self.playWidget, align=Qt.AlignLeft )
      return hbox

   def makeFoot(self):
      buttonbox = QHBoxLayout()

      closeButton = QPushButton('Close', self)
      closeButton.setToolTip("Close this window")
      closeButton.clicked.connect(self.closer)
      buttonbox.addWidget( closeButton, alignment=Qt.AlignRight )

      return buttonbox

   def closer(self):
      self.playWidget.stop(None)
      self.dialog.close()

   def emptyForm(self):
      while self.form.count():
         child = self.form.takeAt(0)
         child.widget().deleteLater()

   def fillForm(self):
     icol = -1
     for colname in self.cat.colnames:
        icol += 1
        collabel = QLabel( colname[:1].upper() + colname[1:].lower() + ":" )
        collabel.setToolTip( self.cat.coldescs[icol] )
        print(colname[:1].upper() + colname[1:].lower() + ":")
        colitem = CatItem.create(self, self.cat, self.irow, icol,
                                 editable=self.editable )
        self.form.addRow( collabel, colitem )

   def updateBody(self):
     self.emptyForm()
     self.fillForm()


# ----------------------------------------------------------------------
class ImportForm(RecordForm):
   def __init__(self,parent,dialog,player,fromcat,tocat):
      self.tocat = tocat
      self.fromcat = fromcat
      RecordForm.__init__(self,parent,dialog,player,fromcat,0,editable=True)

   def makeHead(self):
      self.headLabel = QLabel( " " )
      self.setHeadText()
      return self.headLabel

   def setHeadText(self):
      self.headLabel.setText( "Uncatalogued MIDI files found in {0}.\n"
                              "Assign suitable values to the fields shown "
                              "below and then press\n'Import', or press "
                              "'Skip' to ignore the MIDI file.\n\n"
                              "Displaying item {1} of {2}...".
                              format( self.tocat.rootdir, self.irow+1,
                                      self.fromcat.nrow ) )

   def makeFoot(self):
      buttonbox = QHBoxLayout()

      self.importButton = QPushButton('Import', self)
      self.importButton.clicked.connect(self.importer)
      buttonbox.addWidget( self.importButton, alignment=Qt.AlignLeft )

      self.skipButton = QPushButton('Skip', self)
      self.skipButton.clicked.connect(self.skiper)
      buttonbox.addWidget( self.skipButton, alignment=Qt.AlignLeft )

      self.closeButton = QPushButton('Close', self)
      self.closeButton.clicked.connect(self.closer)
      buttonbox.addWidget( self.closeButton, alignment=Qt.AlignRight )

      self.setMyTitle()
      return buttonbox

   def setMyTitle(self):
      if self.record:
         self.importButton.setToolTip("Import {0} into the music catalogue".format(self.record.title))
         self.skipButton.setToolTip("Skip {0} and move onto the next item to import".format(self.record.title))
         self.closeButton.setToolTip("Ignore {0} and close this window".format(self.record.title))
      else:
         self.importButton.setToolTip("")
         self.skipButton.setToolTip("")
         self.closeButton.setToolTip("")

   def importer(self):
      newrow = []
      for colname in self.fromcat.colnames:
         newrow.append( self.fromcat[colname][self.irow] )
      self.tocat.addrow( newrow )
      self.next()

   def skiper(self):
      self.next()

   def next(self):
      if self.irow == self.fromcat.nrow - 1:
         self.closer()
      else:
         self.setIrow( self.irow + 1 )
         self.setHeadText()
         self.updateBody()
         if self.irow == self.fromcat.nrow - 1:
            self.skipButton.setEnabled(False)
         self.playWidget.setPlayable(self.record)
         self.setMyTitle()

# ----------------------------------------------------------------------
class PlayerListener(QThread):
   stopped = pyqtSignal()
   started = pyqtSignal('QString')

   def __init__(self):
      QThread.__init__(self)

   def run(self):
      waited = 0
      while waited < 60:
         try:
            if stat.S_ISFIFO(os.stat(cpmodel.WFIFO).st_mode):
               break
         except OSError:
            pass
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
   def __init__(self,parent,alive,enabled,enabledFile,disabledFile,onClick,size=35,tip=None):
      QLabel.__init__(self,parent)
      self.enabledPixmap = QPixmap(enabledFile).scaledToHeight( size, Qt.SmoothTransformation )
      if disabledFile:
         self.disabledPixmap = QPixmap(disabledFile).scaledToHeight( size, Qt.SmoothTransformation )
      else:
         self.disabledPixmap = self.enabledPixmap
      if tip:
         self.setToolTip( tip )
      self.setAlignment(Qt.AlignHCenter)
      self.setFixedSize( size*1.1, size*1.1 )
      self.mouseReleaseEvent = onClick
      self.alive = alive
      if alive:
         if enabled:
            self.enable()
         else:
            self.disable()
      else:
         self.disable()

   def setAlive(self,alive):
      self.alive = alive
      if not alive:
         self.disable()

   def enable(self):
      if self.alive:
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
   def __init__(self,parent,player,playable=None,stop=True,fade=False,size=35,cat=None,sliders=None,kbdChooser=None):
      QWidget.__init__(self,parent)
      self.player = player
      if cat:
         self.cat = cat
      else:
         self.cat = player.cat
      self.playable = None
      self.layout = QHBoxLayout()
      self.layout.setSpacing(0)
      self.layout.addStretch()
      self.sliderpanel = sliders
      self.kbdChooser = kbdChooser

      self.playButton = PlayerButton( self, False, False, 'icons/Play.png',
                                      'icons/Play-disabled.png', self.play,
                                      size )
      self.layout.addWidget(self.playButton)

      if stop:
         self.stopButton = PlayerButton( self, False, False, 'icons/Stop.png',
                                         'icons/Stop-disabled.png',
                                         self.stop, size )
         self.layout.addWidget(self.stopButton)
      else:
         self.stopButton = None

      if fade:
         self.fadeButton = PlayerButton( self, False, False, 'icons/Fade.png',
                                         'icons/Fade-disabled.png',
                                         self.fade, size )
         self.layout.addWidget(self.fadeButton)
      else:
         self.fadeButton = None

      self.layout.addStretch()
      self.setLayout( self.layout )

      self.setPlayable( playable )
      player.addClient( self )

   def setProg0(self,prog0):
      if self.playable:
         self.playable.instrument = prog0

   def setRT(self,colname,value):
      if self.playable:
         if colname == "TRANS":
            self.playable.transpose = value
         elif colname == "PROG0":
            self.playable.instrument = value
         elif colname == "VOLUME":
            self.playable.volume = value
         elif colname == "SPEED":
            self.playable.tempo = value
         else:
            raise ChurchPlayerError("\n\nPlayerWidget.setRT does not yet "
                                    "support column '{0}'.".format(colname) )

   def setPlayable(self,playable,prog0=None,trans=None,volume=None,tempo=None):
      if playable != None:
         if not isinstance(playable,cpmodel.Record) and not isinstance(playable,cpmodel.Playlist):
            playable = self.cat.getRecord(int(playable),prog0,trans,
                                          volume,tempo)

      if not self.playable and playable:
         self.playButton.setAlive(True)
         if self.stopButton:
            self.stopButton.setAlive(True)
         if self.fadeButton:
            self.fadeButton.setAlive(True)
         if not self.player.playing:
            self.playButton.enable()

      elif self.playable and not playable:
         self.playButton.setAlive(False)
         if self.stopButton:
            self.stopButton.setAlive(False)
         if self.fadeButton:
            self.fadeButton.setAlive(False)
         self.playButton.disable()

      self.playable = playable

      if playable:
         self.playButton.setToolTip("Click to play {0}".format(playable.desc()))
         if self.stopButton:
            self.stopButton.setToolTip("Click to stop {0}".format(playable.desc()))
         if self.fadeButton:
            self.fadeButton.setToolTip("Click to fade {0} gradually".format(playable.desc()))
      else:
         self.playButton.setToolTip("")
         if self.stopButton:
            self.stopButton.setToolTip("")
         if self.fadeButton:
            self.fadeButton.setToolTip("")

   def play(self, event ):
      if self.playButton and self.playButton.enabled:
         if self.sliderpanel:
            self.sliderpanel.setPlayerWidget( self )
         if self.kbdChooser:
            self.player.setKbdChooser( self.kbdChooser )
         self.player.playMusic( self )

   def stop(self, event):
      if self.stopButton and self.stopButton.enabled:
         self.player.stopMusic()

   def fade(self, event):
      if self.fadeButton and self.fadeButton.enabled:
         self.player.fadeMusic()

   def finish(self):
      self.stop(None)
      self.player.removeClient( self )
      self.player.setKbdChooser( None )

   def __del__(self):
      print("!!!!!!!!  PlayerWidget.__del__ called")

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
      self.setToolTip(cat.coldescs[icol] )
      self.value = None

   @staticmethod
   def create(parent,cat,irow,icol,editable=False):
      (t,opts,descs) = cat.getOptions(icol)

      if not editable:
         return CatLabel(parent,cat,irow,icol,opts,descs,t)

      elif t == 't':
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
      if text:
         self.value = text.strip()
         if self.value == "":
            self.value = None
      else:
         self.value = None

      if self.irow != None:
         self.col[ self.irow ] = text

class CatSpinBox(QSpinBox,CatItem):
   def __init__(self,parent,cat,irow,icol,opts,descs,t):
      QSpinBox.__init__(self,parent)
      self.setMaximum( 5000 )
      self.setMinimum( 0 )
      self.setSpecialValueText( " " )
      CatItem.__init__(self,parent,cat,irow,icol,opts,descs,t)
      self.valueChanged.connect(self.valueHasChanged)
      if irow != None:
         text = cat[ cat.colnames[icol] ][irow]
         if text:
            self.setValue( int(text) )
      else:
         self.setValue( 0 )
      self.setFixedWidth(1.5*self.minimumSizeHint().width())

   def valueHasChanged(self, value ):
      if value == 0:
         self.catStore( None )
      else:
         self.catStore( str(value) )

   def clear(self):
      self.setValue( 0 )

class CatComboBoxS(QComboBox,CatItem):
   def __init__(self,parent,cat,irow,icol,opts,descs,t):
      QComboBox.__init__(self,parent)
      CatItem.__init__(self,parent,cat,irow,icol,opts,descs,t)

      if irow != None:
         curval = cat[ cat.colnames[icol] ][irow]
      else:
         curval = " "

      self.clearTo = -1
      i = 0
      for opt in opts:
         self.addItem(opt)
         if descs and len(descs) > i:
            self.setItemData( i, descs[i], Qt.ToolTipRole )
         if opt == curval:
            self.clearTo = i
         i += 1

      if irow != None:
         if self.clearTo == -1:
            self.addItem(curval)
            self.clearTo = i
      else:
         self.addItem(curval)
         self.clearTo = i

      self.setCurrentIndex( self.clearTo )
      self.setFixedWidth(1.5*self.minimumSizeHint().width())
      self.currentIndexChanged.connect(self.indexHasChanged)

   def indexHasChanged(self, item ):
      self.catStore( str(self.itemText(item)) )

   def clear(self):
      self.setCurrentIndex( self.clearTo )

class CatComboBoxM(QComboBox,CatItem):
   def __init__(self,parent,cat,irow,icol,opts,descs,t):
      QComboBox.__init__(self,parent)
      CatItem.__init__(self,parent,cat,irow,icol,opts,descs,t)

      if irow != None:
         self.curval = cat[ cat.colnames[icol] ][irow]
      else:
         self.curval = " "

      self.addItem(" ")
      self.setItemData( 0, "Clear the currrent selection of tags", Qt.ToolTipRole )
      i = 0
      for opt in opts:
         self.addItem(opt)
         if descs:
            self.setItemData( i+1, descs[i], Qt.ToolTipRole )
         i += 1

      self.setCurrentIndex( 0 )
      self.setEditable( True )
      self.lineEdit().setReadOnly(True)
      self.setFixedWidth(1.5*self.minimumSizeHint().width())
      self.currentIndexChanged.connect(self.indexHasChanged)

   def indexHasChanged(self, item ):
      text = self.itemText(item)
      if text == " ":
         self.curval = ""
      elif item != "":
         self.curval = self.curval + text
      self.catStore( str(self.curval) )
      self.setEditText(self.curval)

   def clear(self):
      self.curval = ""
      self.setCurrentIndex( 0 )


class CatLineEdit(QLineEdit,CatItem):

   def __init__(self,parent,cat,irow,icol,opts,descs,t):
      QLineEdit.__init__(self,parent)
      CatItem.__init__(self,parent,cat,irow,icol,opts,descs,t)
      if irow != None:
         text = cat[ cat.colnames[icol] ][irow]
         self.setText( text )
         width = self.fontMetrics().boundingRect(text).width()
         self.setMinimumWidth(width)
      else:
         self.setMinimumWidth(300)
      self.setFrame(True)
      self.textChanged.connect(self.textHasChanged)

   def textHasChanged(self, text ):
      self.catStore( str(text) )

   def widthHint(self):
      return self.minimumWidth()

   def clear(self):
      self.setText("")


class CatLabel(QLabel,CatItem):

   def __init__(self,parent,cat,irow,icol,opts,descs,t):
      QLabel.__init__(self,parent)
      CatItem.__init__(self,parent,cat,irow,icol,opts,descs,t)
      if irow != None:
         text = cat[ cat.colnames[icol] ][irow]
         self.setText( text )
         width = self.fontMetrics().boundingRect(text).width()
         self.setMinimumWidth(width)
      else:
         self.setMinimumWidth(100)

   def widthHint(self):
      return self.minimumWidth()

   def clear(self):
      pass



class ImportDialog(QDialog):

   def __init__( self, parent, fromcat, tocat ):
      super(ImportDialog, self).__init__(parent)
      self.setWindowTitle('Music importer')
      layout = QVBoxLayout()
      add( layout, ImportForm( self, self, parent.player, fromcat, tocat ) )
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
      self.player = PlayController( self, player, cat )

#  Set up tool tips
      QToolTip.setFont(QFont('SansSerif', 10))

#  Actions...
      exitAction = QAction(QIcon('icons/Exit.png'), '&Exit', self)
      exitAction.setStatusTip('Exit application')
      exitAction.triggered.connect(self.exit)

      saveAction = QAction(QIcon('icons/Save.png'), '&Save', self)
      saveAction.setStatusTip('Save the current service')
      saveAction.triggered.connect(self.save)

      openAction = QAction(QIcon('icons/Open.png'), '&Open', self)
      openAction.setStatusTip('Open an existing service or playlist')
      openAction.triggered.connect(self.open)

      scanAction = QAction( '&Scan', self)
      scanAction.setShortcut('Ctrl+I')
      scanAction.setStatusTip('Scan the music directory for uncatalogued MIDI files')
      scanAction.triggered.connect(self.scan)

      classifyAction = QAction(QIcon('icons/Tick.png'), '&Classify', self)
      classifyAction.setStatusTip('Classify music')
      classifyAction.triggered.connect(self.classify)
      classifyAction.setShortcut('Ctrl+L')

      saveCatAction = QAction(QIcon('icons/SaveCat.png'), '&Save Catalogue', self)
      saveCatAction.setStatusTip('Save the music catalogue to disk')
      saveCatAction.triggered.connect(self.saveCatalogue)

#  Set up status bar
      self.statusBar()

#  Set up menu bar
      menubar = self.menuBar()
      fileMenu = menubar.addMenu('&File')
      fileMenu.addAction(saveAction)
      fileMenu.addAction(openAction)
      fileMenu.addAction(exitAction)

      catMenu = menubar.addMenu('&Catalogue')
      catMenu.addAction(classifyAction)
      catMenu.addAction(scanAction)
      catMenu.addAction(saveCatAction)

#  Set up the toolbar.
      toolbar = self.addToolBar('tools')
      toolbar.addAction(exitAction)
      toolbar.addAction(classifyAction)
      toolbar.addAction(saveAction)
      toolbar.addAction(openAction)

#  The central widget
      self.mw = MainWidget( self, self.player, cat )
      self.setCentralWidget( self.mw )

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

      if self.mw.service.changed:
         ret = QMessageBox.warning(self, "Warning",
                '''The service details have been modified.\nDo you want to save your changes?''',
                QMessageBox.Save, QMessageBox.Discard, QMessageBox.Cancel)
         if ret == QMessageBox.Save:
            self.mw.service.save()
         elif ret == QMessageBox.Cancel:
            doexit = False

      if doexit:
         ret = QMessageBox.question(self, "Confirm Exit...",
				  "Are you sure you want to exit?",
				  QMessageBox.Yes| QMessageBox.No)
         if ret == QMessageBox.No:
            doexit = False

      if doexit:
         del self.player.player
         self.close()



#  ---------------------------------------------------------------
#  Save the catalogue.
#  ---------------------------------------------------------------
   def saveCatalogue(self, e ):
      self.cat.save()

#  ---------------------------------------------------------------
#  Open service.
#  ---------------------------------------------------------------
   def open(self, e ):
      path = QFileDialog.getOpenFileName( self, "Load existing service",
                         "services/", "Images (*.srv)")
      if path:
         self.mw.service.loadFrom( path )


#  ---------------------------------------------------------------
#  Save a service.
#  ---------------------------------------------------------------
   def save(self, e ):
      self.mw.service.save()


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
#  Classify music
#  ---------------------------------------------------------------
   def classify(self, e ):
      ed = ClassifyDialog(self,self.player)
      ed.exec_()

#  ---------------------------------------------------------------
#  Main entry.
#  ---------------------------------------------------------------
def main():

    app = QApplication(sys.argv)
    font = app.font()
    font.setPointSize(15)
    app.setFont( font )

# Create and display the splash screen
    splash_pix = QPixmap('icons/splash2-loading.png')
    splash = QSplashScreen(splash_pix)

    font = splash.font()
    font.setPixelSize(30)
    splash.setFont(font)

    splash.show()
    app.processEvents()

#  Set up the catalogue etc
    splash.showMessage( " Reading music catalogue...", Qt.AlignBottom, Qt.white )
    app.processEvents()
    cat = cpmodel.Catalogue()

    splash.showMessage( " Verifying music catalogue...", Qt.AlignBottom, Qt.white )
    app.processEvents()
    cat.verify()

    splash.showMessage( " Creating music player processes...", Qt.AlignBottom, Qt.white )
    app.processEvents()
    player = cpmodel.Player()

    splash.showMessage( " Creating music listener process...", Qt.AlignBottom, Qt.white )
    app.processEvents()
    player.listener = PlayerListener()
    app.processEvents()
    player.listener.start()
    app.processEvents()
    ex = ChurchPlayer( app, cat, player )
    ex.activateWindow()

    print("TO DO:")
    print("   BUTTONS FOR PLAYING RANDOM MUSIC")
    print("   ABILITY TO SAVE AND OPEN SERVICES" )
    print("   PANIC BUTTON NEEDS TO SAVE AND RESTORE THE CURRENT SERVICE")
    print("   MODIFY SOUNDFONT TO CONTAIN MORE NICE EPIANOS AND ORGANS")
    print("   CLASSIFY ALL MUSIC" )
    print("   WRITE BETTER MIDIS TO REPLACE STF MIDIS" )
    print("   IMPLEMENT HANDLERS FOR SERVICEITEM NAVIGATION BUTTONS" )
    print("   CLICKING ON A USED SERVICE ITEM SHOULD SET THE SLIDERS" )
    print("   CLOSING WINDOW VIA WINDOW MANAGER CROSS SHOULD SAVE MODS")

#  Ready to run...
    splash.finish(ex)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
