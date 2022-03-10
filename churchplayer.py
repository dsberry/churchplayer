#!/usr/bin/python3

import cpmodel
import sys
import time
import stat
import os
import re

NSLOT = 13
SLOT_HEIGHT = 30
SLOT_PADDING = 10
PANIC_SERVICE = "services/panic.srv"
BGCOLOUR = "#eeeeee"

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
class MyFrame(QFrame):
   def __init__( self, parent ):
      super(MyFrame, self).__init__(parent)
      self.setFrameShape( QFrame.Box )
      self.setLineWidth( 1 )
      self.setMidLineWidth( 1 )
      self.setObjectName("myFrame");
      self.setStyleSheet("#myFrame { background-color:"+BGCOLOUR+"; border: 1px solid #cccccc; }");

# ----------------------------------------------------------------------
class RandomPlayer(MyFrame):
   def __init__( self, parent, player, sliderpanel  ):
      super(RandomPlayer, self).__init__(parent)
      self.player = player
      self.count = QLabel( " " )
      self.pw = PlayerWidget(self,player,stop=False,sliders=sliderpanel)
      self.tagSelector = TagSelector( self, player.cat, True, self.count,
                                      self.pw, sliderpanel, True )
      layout = QVBoxLayout()
      topLayout = QHBoxLayout()
      topLayout.addWidget( QLabel( "<b>Play random music: </b>" ) )
      topLayout.addWidget( self.pw, Qt.AlignLeft )
      topLayout.addStretch(10)
      topLayout.addWidget( self.count )
      layout.addLayout( topLayout )
      layout.addWidget( self.tagSelector )
      self.setLayout( layout )

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
               self.player.cat.modified = True

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
      self.cb.setFixedWidth(150)
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
class SliderPanel(MyFrame):
   def __init__( self, parent, player, playerwidget=None, store=False,
                 playButtons=False, reset=False ):
      super(SliderPanel, self).__init__(parent)
      self.player = player

      vlay = QVBoxLayout()
      vlay.addWidget( QLabel( "<b>Control the currently playing musical item: </b>"
               "&nbsp; &nbsp; &nbsp;These sliders reset after each item<br>finishes. Use the "
               "<i>Master Volume</i> slider above to make a permanent volume change." ) )
      if playButtons:
         vlay.addWidget( player )
         vlay.addWidget( HLine() )
      sliders =  QHBoxLayout()

      if reset:
         ulay = QVBoxLayout()
         ulay.addStretch()
         resetButton = QPushButton('Reset', self)
         resetButton.setToolTip("Reset sliders to original positions")
         resetButton.clicked.connect(self.reseter)
         resetButton.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
         ulay.addWidget( resetButton )
         sliders.addLayout( ulay )

      sliders.addStretch()

      sl1 = QVBoxLayout()
      self.volumeslider = CPSlider( self, self.player, 'VOLUME', -99, 99, 1,
                                    playerwidget, store )
      self.volumeslider.setToolTip("Change the playback volume relative to the current master volume")
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

      vlay.addLayout( sliders )
      self.setLayout( vlay )

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

   def reseter( self ):
      self.volumeslider.reset()
      self.temposlider.reset()
      self.pitchslider.reset()

# ----------------------------------------------------------------------
class MasterVolume(MyFrame):
   def __init__( self, parent, player ):
      super(MasterVolume, self).__init__(parent)
      self.player = player

      vlay = QVBoxLayout()
      vlay.addWidget( QLabel( "<b>Master<br>Volume: </b>" ) )

      self.slider = CPSlider( self, self.player, "MASTER", 0, 100, 1 )
      self.slider.setToolTip("Change the master volume")
      vlay.addWidget( self.slider )

      self.setLayout( vlay )

# ----------------------------------------------------------------------
class TagSelector(QWidget):

   def __init__( self, parent, cat, clear=False, label=None, pw=None,
                 sliders=None, addGeneralTag=False ):
      super(TagSelector, self).__init__(parent)
      self.checks = {}
      self.cat = cat
      self.label = label
      self.pw = pw
      self.sliders=sliders

      layout = QVBoxLayout()
      layout.setSpacing(0)

      if addGeneralTag:
         cb = QCheckBox( "General", self )
         cb.setToolTip("Anything that is not specific to a single season (Easter,Advent,etc)" )
         cb.setTristate( False )
         cb.stateChanged.connect(self.stateHasChanged)
         self.checks["G"] = cb
         layout.addWidget( cb, Qt.AlignLeft )
         self.gcheck = cb
      else:
         self.gcheck = None

      for (name,desc) in zip(cat.tagnames,cat.tagdescs):
         cb = QCheckBox( desc, self )
         cb.setTristate( False )
         cb.stateChanged.connect(self.stateHasChanged)
         self.checks[name] = cb
         layout.addWidget( cb, Qt.AlignLeft )

      if clear:
         clearButton = QPushButton('Clear All', self)
         clearButton.setToolTip("Clear all the above check boxes")
         clearButton.clicked.connect(self.clearer)
         clearButton.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
         hlay  = QHBoxLayout()
         hlay.addStretch(1)
         hlay.addWidget(  clearButton, Qt.AlignRight )
         layout.addLayout( hlay )

      self.clearer()
      self.setLayout( layout )
      self.stateHasChanged(0)

   def clearer( self ):
      for name in self.checks:
         self.checks[name].setChecked( False )
      if self.gcheck:
         self.gcheck.setChecked( True )

   def setFromRow( self, irow ):
      if self.gcheck:
         self.gcheck.setChecked( False )

      tags = self.cat['TAGS'][ irow ]
      for name in self.cat.tagnames:
         cb =  self.checks[name]
         if tags and name in tags:
            cb.setChecked( True )
         else:
            cb.setChecked( False )

   def getTags(self):
      newtags = ""
      for name in self.checks:
         cb =  self.checks[name]
         if cb.isChecked():
            newtags += name

      return ''.join(sorted(newtags))

   def stateHasChanged(self, item ):
      if self.label or self.pw:
         tags = self.getTags()
         count = self.cat.countTagMatches( tags )
         if self.label:
            self.label.setText( "({0} matching items)".format( count ) )
         if count == 0:
            showMessage( "There are no hymns/songs that match your selected tags")
         if self.pw:
            if count > 0:
               playlist = cpmodel.RandomPlaylist( tags, self.cat )
            else:
               playlist = None
            self.pw.setPlayable( playlist )
            if self.sliders:
               self.sliders.setFromPlayable( playlist )


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
      self.tagSelector = TagSelector( self, self.cat )
      mainlayout.addWidget(self.tagSelector)
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
      newtags = self.tagSelector.getTags()
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

      self.tagSelector.setFromRow( self.irow-1 )
      book = self.cat['BOOK'][self.irow-1]
      number = self.cat['NUMBER'][self.irow-1]
      title = self.cat['TITLE'][self.irow-1]
      tune = self.cat['TUNE'][self.irow-1]
      if tune and tune.strip() != "":
         self.desc.setText( "{0}  {1}  '{2}'  ({3})".format(book,number,title,tune) )
      else:
         self.desc.setText( "{0}  {1}  '{2}'".format(book,number,title) )




# ----------------------------------------------------------------------
class SearchMatch(QWidget):

   def __init__( self, parent, irow, selected, player ):
      super(SearchMatch, self).__init__(parent)
      self.irow = irow
      self.player = player
      layout = QHBoxLayout()
      self.setLayout( layout )

      self.cb = QCheckBox()
      self.cb.setToolTip("Click to include this row in the service slot")
      if selected:
         self.cb.setChecked(True)
      layout.addWidget( self.cb )

      i = 1
      for (val,tip,width) in self.player.cat.getUserValues( irow ):
         lab = QLabel(val)
         lab.setFixedWidth(width)
         if tip:
            lab.setToolTip(tip)
         layout.addWidget(lab )
         i += 1

      self.pw = PlayerWidget( self, self.player, irow, size=20 )
      layout.addWidget( self.pw, Qt.AlignRight )
      i += 1

      lab = QLabel('({0})'.format(irow+1))
      lab.setToolTip("Index within music catalogue" )
      layout.addWidget(lab, Qt.AlignRight )

   def sizeHint( self ):
      hint = QWidget.sizeHint(self)
      hint.setHeight( int(1.5*SLOT_HEIGHT) )
      return hint

# ----------------------------------------------------------------------
class SearchDialog(QDialog):

   def __init__( self, parent, player, target ):
      super(SearchDialog, self).__init__(parent)
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

      if target.playlist:
         self.matchingRows = target.playlist.getIrows()
         for irow in self.matchingRows:
            matchWidget = SearchMatch( self, irow, True, self.player )
            self.scarea.addWidget( matchWidget )


   def makeUpper(self):
      layout = QHBoxLayout()
      self.searchItems = []
      icol = -1
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
      self.scarea = MyListWidget()
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
#      self.player.stopper(None)
      self.close()

   def oker(self):
      nmatch = len(self.matchingRows)
      if nmatch > 0:
         rows = []

         for sindex in range(self.scarea.count()):
            item = self.scarea.itemWidget( self.scarea.item( sindex ) )
            if item.cb.isChecked():
               rows.append( item.irow )

         if len(rows) == 0:
            if showYesNoMessage( "No music has been selected.", "Select all "
                                 "displayed music before closing this window?" ):
               for sindex in range(self.scarea.count()):
                  item = self.scarea.itemWidget( self.scarea.item( sindex ) )
                  rows.append( item.irow )

         if len(rows) > 0:
            self.target.setPlaylist( self.player.cat.makePlaylist( rows ) )
         else:
            self.target.setPlaylist( None )
      else:
         self.target.setPlaylist( None )

      self.closer()

   def clearer(self):
      for item in self.searchItems:
         item.clear()

   def searcher(self):
      searchVals = []
      searchCols = []
      ok = False
      for item in self.searchItems:
         if item.value:
            ok = True
         searchVals.append( item.value )
         searchCols.append( item.icol )

      if not ok:
         showMessage( "No selection criteria specified. Please give some indication of the music you are looking for. " )
      else:

         self.matchingRows = []
         for sindex in range(self.scarea.count()):
            item = self.scarea.itemWidget( self.scarea.item( sindex ) )
            if item.cb.isChecked():
               self.matchingRows.append( item.irow )
         nold = len( self.matchingRows )

         newrows = self.player.cat.search( searchVals, searchCols )
         if len( newrows ) == 0:
            showMessage("No matching music found !")
         else:
            self.matchingRows.extend(newrows)

         self.clearResults()

         if len( self.matchingRows ) > 0:
            icheck = 0;
            for irow in self.matchingRows:
               matchWidget = SearchMatch(self,irow,(icheck < nold), self.player )
               self.scarea.addWidget( matchWidget )
               icheck += 1
            self.clearer()

   def clearResults(self):
      for sindex in range(self.scarea.count()):
         item = self.scarea.itemWidget( self.scarea.item( sindex ) )
         item.pw.finish()
      self.scarea.clear()





# ----------------------------------------------------------------------
class MyListWidget(QListWidget):
   def __init__(self,service=None):
      super(MyListWidget, self).__init__()
      self.setDragDropMode( QAbstractItemView.InternalMove )
      self.setSelectionMode( QAbstractItemView.SingleSelection )
      self.service = service
      self.setObjectName("mylistwidget");
      self.setStyleSheet("#mylistwidget { background-color:"+BGCOLOUR+"; border-style: none; }");

   def dropEvent(self, e):
      super(MyListWidget,self).dropEvent( e )
      self.clearSelection()
      if self.service:
         self.service.changed = True

   def addWidget( self, widget ):
      litem = QListWidgetItem()
      litem.setSizeHint( widget.sizeHint() )
      self.addItem( litem )
      self.setItemWidget( litem, widget )

   def insertWidget( self, sindex, widget ):
      litem = QListWidgetItem()
      litem.setSizeHint( widget.sizeHint() )
      self.list.insertItem( sindex, litem )
      self.setItemWidget( litem, widget )


# ----------------------------------------------------------------------
class Service(MyFrame):
   def __init__(self,parent,player,sliderpanel):
      super(Service, self).__init__(parent)
      self.player = player
      self.sliderpanel = sliderpanel
      self.items = []
      self.path = None

      layout = QVBoxLayout()
      self.setLayout( layout )

      layout.addWidget( QLabel( "<b>Choose the hymns/songs to play during the service: </b>" ))
      self.list = MyListWidget(self)

      for i in range(NSLOT):
         sitem = ServiceItem( self, player, sliderpanel )
         self.list.addWidget( sitem )

      layout.addWidget( self.list )

#      self.setFixedHeight( (NSLOT+1)*(SLOT_HEIGHT+SLOT_PADDING) )
      self.setFixedWidth(800)
      self.changed = False

   def clearSelection(self):
      self.list.clearSelection()

   def addItemAt(self, sindex ):
      if sindex < 0:
         sindex = self.list.count()
      self.changed = True

      sitem = ServiceItem( self, self.player, self.sliderpanel )
      self.list.insertWidget( sindex, sitem )
      self.list.invalidate()
      self.list.repaint()
      self.list.update()
      return item

   def savePanic(self):
      self.saveAs( PANIC_SERVICE, True )

   def save(self):
      if self.path == None:
         defpath = "services/"
         self.path = QFileDialog.getSaveFileName(self, "Save service",
                           defpath, "Images (*.srv)");

      if self.path:
         self.path = str( self. path )
         if not self.path.endswith(".srv"):
            self.path += ".srv"
         self.saveAs(self.path)

   def saveAs( self, path, incPath=False ):
      fd = open( path, "w" );
      if incPath and self.path:
         fd.write( "path={0}".format(self.path) )
      for sindex in range(self.list.count()):
         item = self.list.itemWidget( self.list.item( sindex ) )
         if item and isinstance( item, ServiceItem ):
            fd.write(str(item)+"\n")
      fd.close()
      self.changed = False

   def loadPanic(self):
      if os.path.isfile( PANIC_SERVICE ):
         self.loadFrom( PANIC_SERVICE )
         os.remove( PANIC_SERVICE )

   def clear(self):
      if not self.saveif(QMessageBox.Close):
         for sindex in range(self.list.count()):
            item = self.list.itemWidget( self.list.item( sindex ) )
            if item and isinstance( item, ServiceItem ):
               item.clearer(None)
         self.changed = False
         self.path = None

   def loadFrom( self, path ):
      fd = open( path, "r" );
      first = True
      sindex = 0
      for line in fd:
         line = line.strip()
         if first:
            match = re.compile("path=(.*)").search(line)
            if match:
               self.path = match.group(1)
         else:
            match = None

         if not match:
            item = None
            while not item or not isinstance( item, ServiceItem ):
               if sindex < self.list.count():
                  item = self.list.itemWidget( self.list.item( sindex ) )
               else:
                  item = addItemAt( -1 )
               sindex += 1

            if line:
               rows = []
               for srow in line.split(","):
                  rows.append( int( srow ) )
               item.setPlaylist( self.player.cat.makePlaylist( rows ) )

      fd.close()
      self.changed = False

   def saveif( self, noSaveButton=QMessageBox.Discard ):
      cancelled = False
      if self.changed:
         if self.path == None:
            ret = QMessageBox.warning(self, "Warning",
                '''Do you want to save the service details?''',
                QMessageBox.Save, noSaveButton, QMessageBox.Cancel)
            if ret == QMessageBox.Save:
               self.save()
            elif ret == QMessageBox.Cancel:
               cancelled = True
         else:
            self.save()
      return cancelled

# ----------------------------------------------------------------------
class PanicButton(QPushButton):
   def __init__(self,parent,player,service):
      super(PanicButton, self).__init__("Don't PANIC !!", parent)
      self.setToolTip("Click to restart churchplayer if things go wrong")
      self.clicked.connect( self.panic )
      self.service = service
      self.player = player

   def panic(self):
      self.player.cat.save()
      self.service.savePanic()
      os.execl( "/bin/sh", "-c", "./run_churchplayer" )


# ----------------------------------------------------------------------
class CPSlider(QWidget):
   def __init__(self, parent, player, colname, vmin, vmax, vstep,
                playerwidget=None, store=False ):
      super(CPSlider, self).__init__(parent)

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
      self.oldval = 0
      self.maxv = float(vmax)

      if colname == "MASTER":
         self.setValue( self.player.player.getMasterVolume()*self.maxv )

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
      if self.colname == "MASTER":
         self.player.player.setMasterVolume( newval/self.maxv )
      else:
         if self.store:
            if self.player.cat[self.colname][self.irow] != newval:
               self.player.cat[self.colname][self.irow] = newval
               self.player.cat.modified = True

         self.player.player.sendRT( self.colname, newval )
         if self.pw:
            self.pw.setRT( self.colname, newval )

   def reset( self ):
      self.spin.setValue(self.oldval)
      self.slider.setValue(self.oldval)
      self.changer(self.oldval)

   def setFromRow( self, irow, map=None ):
      self.ignore = True
      self.irow = irow
      if irow < 0:
         self.oldval = 0
      elif map and irow in map:
         self.oldval = map[ irow ]
      else:
         self.oldval =  int( self.player.cat[self.colname][irow] )

      self.setValue( self.oldval )
      self.ignore = False
      return self.oldval

   def saveToMap( self, mymap ):
      newval = self.slider.value()
      if self.irow >= 0 and newval != self.oldval:
         mymap[self.irow] = newval

   def setValue( self, value ):
      self.slider.setValue( int(value) )
      self.spin.setValue( int(value) )


# ----------------------------------------------------------------------
class ServiceItem(QWidget):
   def __init__(self,parent,player,sliderpanel,label=None):
      super(ServiceItem, self).__init__(parent)

      self.service = parent
      self.player = player
      self.sliderpanel = sliderpanel
      self.kbdChooser = KeyboardChooser( self, player, store=True  )
      self.playlist = None
      self.clear = PlayerButton( self, True, True, 'icons/empty.png',
                                 'icons/null.png', self.clearer, 20, "Empty this slot" )
      self.pw = PlayerWidget(self,player,stop=False,sliders=sliderpanel,
                             kbdChooser=self.kbdChooser)
      self.kbdChooser.setpw( self.pw )


      if not label:
         label = "Click here to choose music"
      self.desc = QLineEdit(label,self)
      self.desc.setReadOnly(True)
      self.desc.setFixedWidth(450)
      self.desc.setFixedHeight(SLOT_HEIGHT)
      self.desc.setToolTip(label)
      self.desc.mouseReleaseEvent = self.musicChooser

      layout = QHBoxLayout()
      layout.addWidget( self.pw, 1, Qt.AlignLeft )
      layout.addWidget( self.desc, 5, Qt.AlignLeft )
      layout.addWidget( self.kbdChooser, 1 )
      layout.addWidget( self.clear, 1, Qt.AlignRight )
      layout.setSizeConstraint( QLayout.SetFixedSize )
      self.setLayout( layout )

   def sizeHint( self ):
      hint = QWidget.sizeHint(self)
      hint.setHeight( int(1.4*SLOT_HEIGHT) )
      return hint

   def clearer(self, event ):
      self.service.changed = True
      self.setPlaylist( None )

   def musicChooser(self, event):
      if self.playlist:
         self.kbdChooser.setFromPlayable( self.playlist )
         self.sliderpanel.setFromPlayable( self.playlist )
      ed = SearchDialog(self,self.player,self)
      ed.exec_()

   def setPlaylist( self, playlist ):
      oldpl = self.playlist
      self.playlist = playlist
      self.pw.setPlayable( playlist )
      if playlist != None:
         self.desc.setText( self.playlist.desc() )
         self.desc.setToolTip( self.playlist.desc() )
         self.kbdChooser.setFromPlayable( playlist )
         self.sliderpanel.setFromPlayable( playlist )
         self.service.changed = True
      else:
         self.desc.setText("Click here to choose music" )
         self.desc.setToolTip("Click here to choose music" )
         self.kbdChooser.setFromPlayable( None )
         self.sliderpanel.setFromPlayable( None )
         if oldpl:
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
      super(PlayController, self).__init__(parent)
      self.player = player
      self.cat = cat
      self.playing = False
      self.playQueue = []
      player.listener.stopped.connect(self.ended)
      player.listener.started.connect(self.playingNew)
      player.listener.remaining.connect(self.timeLeft)
      self.playButtons = []
      self.stopButtons = []
      self.fadeButtons = []
      self.nextButtons = []
      self.sliderPanels = []
      self.service = None
      self.kbdChooser = None
      self.prefix = "<b>Now playing: </b>"
      self.title = "(nothing)"
      self.label = QLabel( " " )
      self.label.setFixedHeight( 60 )
      self.setLabel(None)

      layout = QHBoxLayout()

      self.stop = PlayerButton( self, True, False, 'icons/Stop.png',
                                'icons/Stop-disabled.png', self.stopper )
      self.stop.setToolTip("Stop the currently playing music abruptly")
      layout.addStretch(5)
      layout.addWidget( QLabel("Stop:"), Qt.AlignRight)
      layout.addWidget( self.stop , Qt.AlignLeft)

      self.fade = PlayerButton( self, True, False, 'icons/Fade.png',
                                'icons/Fade-disabled.png', self.fader )
      self.fade.setToolTip("Fade out the currently playing music slowly")
      layout.addStretch(10)
      layout.addWidget( QLabel("Fade out:"), Qt.AlignRight)
      layout.addWidget( self.fade, Qt.AlignLeft)

      self.next = PlayerButton( self, True, False, 'icons/Next.png',
                                'icons/Next-disabled.png', self.nexter )
      self.fade.setToolTip("Move to the next track in the playlist")
      layout.addStretch(10)
      layout.addWidget( QLabel("Next track:"), Qt.AlignRight)
      layout.addWidget( self.next, Qt.AlignLeft)
      layout.addStretch(10)

      self.setLayout( layout )

   def addClient(self,client):
      if isinstance(client,PlayerWidget):
         self.playButtons.append( client.playButton )
         if client.stopButton:
            self.stopButtons.append( client.stopButton )
         if client.fadeButton:
            self.fadeButtons.append( client.fadeButton )
         if client.nextButton:
            self.nextButtons.append( client.nextButton )
      elif isinstance(client,SliderPanel):
         self.sliderPanels.append( client )
      elif isinstance(client,Service):
         self.service = client

   def setKbdChooser( self, chooser ):
      self.kbdChooser = chooser

   def removeClient(self,client):
      if isinstance(client,PlayerWidget):
         self.playButtons.remove( client.playButton )
         if client.stopButton:
            self.stopButtons.remove( client.stopButton )
         if client.fadeButton:
            self.fadeButtons.remove( client.fadeButton )
         if client.nextButton:
            self.nextButtons.remove( client.nextButton )
      elif isinstance(client,SliderPanel):
         self.sliderPanels.remove( client )
      elif isinstance(client,Service):
         self.service = None

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

         for nextbutton in self.nextButtons:
            if nextbutton != playwid.nextButton:
               nextbutton.disable()
         if playwid.nextButton:
            playwid.nextButton.enable()

         self.stop.enable()
         self.fade.enable()
         self.next.enable()

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

   def nextTrack(self):
      if self.playing:
         self.player.stop( cpmodel.FADE )

   def setLabel(self,timeleft):
      if timeleft == None:
         self.label.setText( "{0} {1}".format(self.prefix, self.title ) )
      else:
         self.label.setText( "{0} {1} ({2} sec. remaining)".
                             format(self.prefix, self.title, timeleft ) )

   @pyqtSlot()
   def ended(self):
      self.title = "(nothing)"
      self.setLabel(None)

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

            for nextbutton in self.nextButtons:
               nextbutton.disable()

            self.stop.disable()
            self.fade.disable()
            self.next.disable()

            self.playing = False
            if self.service:
               self.service.clearSelection()

   @pyqtSlot(str)
   def playingNew(self,path):
      irow = self.cat.findPath(path)
      if irow >= 0:
         title = self.cat['TITLE'][ irow ]
         book = self.cat['BOOK'][ irow ]
         if book:
            number = self.cat['NUMBER'][ irow ]
            self.title = "{0} {1}: {2}".format(book, number, title )
         else:
            self.title = title
      else:
         self.title = "(unknown)"
      self.setLabel(None)

   @pyqtSlot(int)
   def timeLeft(self,timeleft):
      self.setLabel(timeleft)

   def stopper(self, event ):
      self.stopMusic()

   def fader(self, event ):
      self.fadeMusic()

   def nexter(self, event ):
      self.nextTrack()


# ----------------------------------------------------------------------
class MainWidget(QWidget):
   def __init__( self, parent, player, cat ):
      super(MainWidget, self).__init__(parent)
      self.player = player
      sliders = SliderPanel( self, player, store=True, playButtons=True,
                             reset=True )

      layout = QHBoxLayout()

      leftpanel = QVBoxLayout()
      leftpanel.setContentsMargins( 20, 0, 20, 0 )
      self.service = Service( self, self.player, sliders )
      leftpanel.addWidget( self.service )
      leftpanel.addWidget( player.label )
      layout.addLayout( leftpanel )

      rightpanel = QVBoxLayout()

      rightsubpanel = QHBoxLayout()
      rightsubpanel.addWidget( MasterVolume( self, self.player ) )
      rightsubpanel.addSpacing( 30 )
      rightsubpanel.addWidget( RandomPlayer( self, self.player, sliders ) )
      rightpanel.addLayout( rightsubpanel )

      rightpanel.addSpacing( 30 )
      player.addClient( sliders )
      player.addClient( self.service )
      rightpanel.addWidget( sliders )
      layout.addLayout( rightpanel )

      self.setLayout( layout )
      self.service.loadPanic()

# ----------------------------------------------------------------------
class RecordForm(QWidget):
   def __init__(self,parent,dialog,player,cat,irow,editable=False,header=None,rowlist=None):
      super(RecordForm, self).__init__(parent)
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
      self.playWidget.finish()
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
      super(ImportForm, self).__init__(parent,dialog,player,fromcat,0,editable=True)

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
      self.tocat.addrow( newrow, self.record.path )
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

   def closer(self):
      self.tocat.verify()
      return super(ImportForm,self).closer()

# ----------------------------------------------------------------------
class PlayerListener(QThread):
   stopped = pyqtSignal()
   started = pyqtSignal('QString')
   remaining = pyqtSignal('int')

   def __init__(self):
      super(PlayerListener, self).__init__()

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
               code = os.read(fd,1).decode("UTF-8")

               if code == cpmodel.PLAYING_CODE:
                  path = os.read(fd,1000).decode("UTF-8")

                  parts = path.split(".mid",1)
                  path = parts[0]+".mid"
                  self.started.emit( path )

               elif code == cpmodel.REMAINING_CODE:
                  time_left = int( os.read(fd,1000).decode("UTF-8").strip('\0') )
                  self.remaining.emit( time_left )

               elif code == cpmodel.STOPPED_CODE:
                  self.stopped.emit()

            except OSError:
               pass


         os.close(fd)


# ----------------------------------------------------------------------
class PlayerButton(QLabel):
   def __init__(self,parent,alive,enabled,enabledFile,disabledFile,onClick,size=35,tip=None):
      super(PlayerButton, self).__init__(parent)
      self.enabledPixmap = QPixmap(enabledFile).scaledToHeight( size, Qt.SmoothTransformation )
      if disabledFile:
         self.disabledPixmap = QPixmap(disabledFile).scaledToHeight( size, Qt.SmoothTransformation )
      else:
         self.disabledPixmap = self.enabledPixmap
      if tip:
         self.setToolTip( tip )
      self.setAlignment(Qt.AlignHCenter)
      self.setFixedSize( int(size*1.1), int(size*1.1) )
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
   def __init__(self,parent,player,playable=None,stop=True,fade=False,next=False,size=35,cat=None,sliders=None,kbdChooser=None):
      super(PlayerWidget, self).__init__(parent)
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
      self.layout.addWidget(self.playButton, Qt.AlignTop )

      if stop:
         self.stopButton = PlayerButton( self, False, False, 'icons/Stop.png',
                                         'icons/Stop-disabled.png',
                                         self.stop, size )
         self.layout.addWidget(self.stopButton, Qt.AlignTop )
      else:
         self.stopButton = None

      if fade:
         self.fadeButton = PlayerButton( self, False, False, 'icons/Fade.png',
                                         'icons/Fade-disabled.png',
                                         self.fade, size )
         self.layout.addWidget(self.fadeButton, Qt.AlignTop )
      else:
         self.fadeButton = None

      if next:
         self.nextButton = PlayerButton( self, False, False, 'icons/Next.png',
                                         'icons/Next-disabled.png',
                                         self.next, size )
         self.layout.addWidget(self.nextButton, Qt.AlignTop )
      else:
         self.nextButton = None

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
         if self.nextButton:
            self.nextButton.setAlive(True)
         if not self.player.playing:
            self.playButton.enable()

      elif self.playable and not playable:
         self.playButton.setAlive(False)
         if self.stopButton:
            self.stopButton.setAlive(False)
         if self.fadeButton:
            self.fadeButton.setAlive(False)
         if self.nextButton:
            self.nextButton.setAlive(False)
         self.playButton.disable()

      self.playable = playable

      if playable:
         self.playButton.setToolTip("Click to play {0}".format(playable.desc()))
         if self.stopButton:
            self.stopButton.setToolTip("Click to stop {0}".format(playable.desc()))
         if self.fadeButton:
            self.fadeButton.setToolTip("Click to fade {0} gradually".format(playable.desc()))
         if self.nextButton:
            self.nextButton.setToolTip("Click to move to the next track in the playlist")
      else:
         self.playButton.setToolTip("")
         if self.stopButton:
            self.stopButton.setToolTip("")
         if self.fadeButton:
            self.fadeButton.setToolTip("")
         if self.nextButton:
            self.nextButton.setToolTip("")

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

   def next(self, event):
      if self.nextButton and self.nextButton.enabled:
         self.player.nextTrack()

   def finish(self):
      self.stop(None)
      self.player.removeClient( self )
      self.player.setKbdChooser( None )

   def __del__(self):
      pass

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
      self.setFixedWidth(int(1.5*self.minimumSizeHint().width()))

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
      self.setFixedWidth(int(1.5*self.minimumSizeHint().width()))
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
      self.setFixedWidth(int(1.5*self.minimumSizeHint().width()))
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

#  Continue...
      self.cat = cat
      self.app = app
      self.closed = False
      self.player = PlayController( self, player, cat )

#  Set up tool tips
      QToolTip.setFont(QFont('SansSerif', 10))

#  Actions...
      exitAction = QAction(QIcon('icons/Exit.png'), '&Exit', self)
      exitAction.setToolTip('Exit application')
      exitAction.triggered.connect(self.exit)

      panicAction = QAction( "&Don't Panic!", self)
      panicAction.setToolTip('Re-start the application')
      panicAction.triggered.connect(self.panic)

      saveAction = QAction(QIcon('icons/Save.png'), '&Save', self)
      saveAction.setToolTip('Save the current service')
      saveAction.triggered.connect(self.save)

      openAction = QAction(QIcon('icons/Open.png'), '&Open', self)
      openAction.setToolTip('Open an existing service or playlist')
      openAction.triggered.connect(self.open)

      newAction = QAction( '&New', self)
      newAction.setToolTip('Clear the existing service details')
      newAction.triggered.connect(self.new)

      scanAction = QAction( '&Scan', self)
      scanAction.setShortcut('Ctrl+I')
      scanAction.setToolTip('Scan the music directory for uncatalogued MIDI files')
      scanAction.triggered.connect(self.scan)

      classifyAction = QAction(QIcon('icons/Tick.png'), '&Classify', self)
      classifyAction.setToolTip('Classify music')
      classifyAction.triggered.connect(self.classify)
      classifyAction.setShortcut('Ctrl+L')

      saveCatAction = QAction(QIcon('icons/SaveCat.png'), '&Save Catalogue', self)
      saveCatAction.setToolTip('Save the music catalogue to disk')
      saveCatAction.triggered.connect(self.saveCatalogue)

#  Set up status bar
#      self.statusBar()

#  Set up menu bar
      menubar = self.menuBar()

      fileMenu = menubar.addMenu('&File')
      fileMenu.addAction(newAction)
      fileMenu.addAction(openAction)
      fileMenu.addAction(saveAction)
      fileMenu.addAction(panicAction)
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

#  Now we have a Service object, append the panic button to the toolbar.
      toolbar.addSeparator()
      toolbar.addWidget( QLabel( "    " ) )
      toolbar.addWidget( PanicButton( self, self.player, self.mw.service ) )
      toolbar.addWidget( QLabel( "    " ) )

#  Set up the main window.
      self.setWindowTitle('Church Player')
      qr = app.desktop().screenGeometry()
      wid =  qr.width()
      hgt =  qr.height()
      self.setMinimumSize( wid, hgt )
      self.setMaximumSize( wid, hgt )
      self.setGeometry( 0, 0, wid, hgt )
      self.showFullScreen()


#  ---------------------------------------------------------------
#  Exit the application.
#  ---------------------------------------------------------------
   def closeEvent(self,event):
      if not self.closed:
         self.exit( event )

   def exit(self, e ):
      doexit = True
      shutit = False
      ret = QMessageBox.warning(self, "Warning", '''Shut down the computer after closing ChurchPlayer?''',
                                      QMessageBox.Yes, QMessageBox.No,
                                      QMessageBox.Cancel)
      if ret == QMessageBox.Yes:
         shutit = True
      elif ret == QMessageBox.Cancel:
         doexit = False

      if self.cat.modified:
         self.cat.save()

      if self.mw.service.saveif():
         doexit = False

      if doexit:
         if self.player:
            try:
               del self.player.player
            except:
               pass
         if shutit:
            print( "SHUTDOWN" )
         self.closed = True
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
#  Clear service.
#  ---------------------------------------------------------------
   def new(self, e ):
      self.mw.service.clear()


#  ---------------------------------------------------------------
#  Save a service.
#  ---------------------------------------------------------------
   def save(self, e ):
      self.mw.service.save()

#  ---------------------------------------------------------------
#  Re-start the application.
#  ---------------------------------------------------------------
   def panic(self, e ):
      print( "Dont panic")

#  ---------------------------------------------------------------
#  Scan for uncatalogued MIDI files.
#  ---------------------------------------------------------------
   def scan(self, e ):
      QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
#      self.statusBar().showMessage("Scanning music directory ({0}) for "
#                                   "uncatalogued MIDI files...".
#                                   format(self.cat.rootdir))
      newmidis = self.cat.searchForNew()
      QApplication.restoreOverrideCursor()
#      self.statusBar().showMessage("")

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
    font.setPointSize(10)
    app.setFont( font )

# Create and display the splash screen
    splash_pix = QPixmap('icons/splash2-loading.png')
    splash = QSplashScreen(splash_pix)

    font = splash.font()
    font.setPixelSize(30)
    splash.setFont(font)

    splash.show()
    app.processEvents()

#  Ensure the services directory exists.
    if not os.path.isdir("services"):
       os.mkdir( "services")

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
    print("   CLASSIFY ALL MUSIC" )
    print("   WRITE BETTER MIDIS TO REPLACE STF MIDIS" )

#  Ready to run...
    splash.finish(ex)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
