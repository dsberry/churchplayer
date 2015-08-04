#!/usr/bin/python

import cpmodel
import sys
import time
import stat
import os

NSLOT = 12

from PyQt4.QtCore import *
from PyQt4.QtGui import *

#  Show a simple message in a modal dialog box with an "OK" button.
def showMessage( text ):
   mb = QMessageBox()
   mb.setText( text )
   mb.exec_();

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
class KeyboardChooser(QWidget):
   def __init__( self, parent, player, playerwidget=None, store=False ):
      super(KeyboardChooser, self).__init__(parent)
      self.store = store
      self.ignore = False
      self.player = player
      self.pw = playerwidget

      layout = QVBoxLayout()
      self.setLayout( layout )
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
      self.cb.currentIndexChanged.connect( self.kbdChanged )
      layout.addWidget( self.cb )

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
               self.player.modified = True
         self.player.player.sendProg0( gm )
         self.pw.setProg0( gm )

   def setFromRow( self, irow, map ):
      self.ignore = True
      self.irow = irow

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
      self.volumeslider = CPSlider( self, self.player, 'VOLUME', -127, 127, 1,
                                   playerwidget, store )
      self.volumeslider.setToolTip("Change the playback volume")
      sl1.addWidget( self.volumeslider )
      sl1.addWidget( QLabel("Volume" ) )
      sliders.addLayout( sl1 )

      sliders.addStretch()

      sl2 = QVBoxLayout()
      self.temposlider = CPSlider( self, self.player, 'SPEED', -127, 127, 1,
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
      self.pw = PlayerWidget(self,player,self.irow-1)
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
      if e.key() == Qt.Key_Space:
         self.nexter()

   def changeRow( self, newrow ):
      self.kbdChooser.saveToMap( self.prog0 )
      self.sliders.pitchslider.saveToMap( self.trans )

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
         self.sliders.pitchslider.saveToMap( self.trans )
         if len(self.changes) > 0 or len(self.prog0) > 0 or len(self.trans) > 0:
            ret = QMessageBox.warning(self, "Warning", '''Save changes?''',
                                      QMessageBox.Save, QMessageBox.Discard,
                                      QMessageBox.Cancel)
            if ret == QMessageBox.Save:
               for irow in self.changes:
                  self.cat['TAGS'][irow] = self.changes[irow]
               for irow in self.prog0:
                  self.cat['PROG0'][irow] = str(self.prog0[irow])
               for irow in self.trans:
                  self.cat['TRANS'][irow] = str(self.trans[irow])
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
      trans = self.sliders.pitchslider.setFromRow( self.irow-1, self.trans )
      self.pw.setPlayable( self.irow-1, prog0=gm, trans=trans )

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

   def __init__( self, parent, player ):
      super(SearchDialog, self).__init__(parent)
      self.player = player
      self.setWindowTitle('Search for music')
      layout = QVBoxLayout()
      add( layout, QLabel("\nEnter values into one or more of the following "
                          "boxes and then press 'Search' to find matching music.\n") )
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

      self.matchingRows = self.player.cat.search( searchVals, searchCols )

      if len( self.matchingRows ) == 0 :
         lab = QLabel("No matching music found !")
         results.addWidget(lab, 0, 0, Qt.AlignTop | Qt.AlignLeft )
      else:
         self.checkbox = []
         j = 0
         for irow in self.matchingRows:
            cb = QCheckBox()
            cb.setToolTip("Click to include this row in the service slot")
            self.checkbox.append( cb )
            results.addWidget(cb, j, 0 )
            i = 1
            for (val,tip) in self.player.cat.getUserValues( irow ):
               lab = QLabel(val)
               if tip:
                  lab.setToolTip(tip)
               results.addWidget(lab, j, i )
               i += 1
            j += 1

      self.clearResults()
      self.scarea.setWidget( right )

   def clearResults(self):
      oldwidget = self.scarea.takeWidget()
      if oldwidget:
         oldwidget.deleteLater()



# ----------------------------------------------------------------------
class Service(QFrame):
   def __init__(self,parent,player):
      QFrame.__init__(self,parent)
      self.setFrameStyle( QFrame.Box )
      self.player = player

      grid = QGridLayout()
      grid.setContentsMargins( 5,5,5,5 )
      grid.setSpacing( 1 )

      j = 0
      for i in range(NSLOT):
         item = ServiceItem( self, player )
         grid.addWidget( item.playButton, j, 0, Qt.AlignLeft )
         grid.addWidget( item.desc, j, 1, Qt.AlignLeft )
         grid.addWidget( item.kbdChooser, j, 2, Qt.AlignRight | Qt.AlignTop )
         j += 1

      grid.setColumnMinimumWidth( 0, 0 )
      grid.setColumnStretch( 1, 10 )
      self.setLayout( grid )
      self.setStyleSheet("background-color:#eeeeee;")

# ----------------------------------------------------------------------
class PanicButton(QPushButton):
   def __init__(self,parent,player):
      QPushButton.__init__( self, "Don't PANIC !!", parent )

      self.setToolTip("Click to kill and restart the music player")
      self.clicked.connect( self.panic )

   def panic(self):
      print( "PANIC !!!")


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
      self.spin.setFixedWidth( 70 )
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

   def setFromRow( self, irow, map ):
      self.ignore = True
      self.irow = irow
      if irow in map:
         self.oldval = map[ irow ]
      else:
         self.oldval =  int( self.player.cat[self.colname][irow] )
      self.slider.setValue( self.oldval )
      self.spin.setValue( self.oldval )
      self.ignore = False
      return self.oldval

   def saveToMap( self, mymap ):
      newval = self.slider.value()
      if newval != self.oldval:
         mymap[self.irow] = newval


# ----------------------------------------------------------------------
class ServiceItem(QWidget):
   def __init__(self,parent,player):
      QWidget.__init__(self,parent)
      self.player = player

      self.playButton = PlayerWidget(self,player,stop=False)

      self.desc = QLabel("Click here to choose music", self )
      self.desc.setFixedWidth(600)
      self.desc.setToolTip("The music played when the play-button is clicked")
      self.desc.mouseReleaseEvent = self.musicChooser
      self.desc.setFrameStyle( QFrame.Panel | QFrame.Sunken )

      self.kbdChooser = KeyboardChooser( self, player, store=True )

   def playit(self, event):
      print( "PLAY clicked!!!")

   def musicChooser(self, event):
      ed = SearchDialog(self,self.player)
      ed.exec_()



# ----------------------------------------------------------------------
class PlayController(QWidget):
   def __init__(self,parent,player,cat):
      QWidget.__init__(self,parent)
      self.player = player
      self.cat = cat
      self.playing = False
      player.listener.stopped.connect(self.ended)
      self.playButtons = []
      self.stopButtons = []
      self.fadeButtons = []

      layout = QHBoxLayout()

      self.stop = PlayerButton( self, True, False, 'icons/Stop.png',
                                'icons/Stop-disabled.png' )
      self.stop.setToolTip("Stop the currently playing music abruptly")
      self.stop.mouseReleaseEvent = self.stopper
      layout.addWidget( self.stop )

      self.fade = PlayerButton( self, True, False, 'icons/Fade.png',
                                'icons/Fade-disabled.png' )
      self.fade.mouseReleaseEvent = self.fader
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

   def removeClient(self,client):
      if isinstance(client,PlayerWidget):
         self.playButtons.remove( client.playButton )
         if client.stopButton:
            self.stopButtons.remove( client.stopButton )
         if client.fadeButton:
            self.fadeButtons.remove( client.fadeButton )

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

         self.playing = True
         self.player.play( playwid.playable, cpmodel.STOP )

   def stopMusic(self):
      if self.playing:
         self.player.stop( cpmodel.STOP )

   def fadeMusic(self):
      if self.playing:
         self.player.stop( cpmodel.FADE )

   def changeKeyboard(self,prog0):
      if self.playing:
         self.player.setProg0( prog0 )

   def changeTrans(self,trans):
      if self.playing:
         self.player.setTrans( trans )


   @pyqtSlot()
   def ended(self):
      if self.playing:
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

      layout = QHBoxLayout()

      leftpanel = QVBoxLayout()
      leftpanel.setContentsMargins( 30, 10, 30, 10 )
      self.service = Service( self, self.player )
      leftpanel.addWidget( self.service )

      stopetc = QHBoxLayout()
      stopetc.addWidget( self.player )
      stopetc.addStretch()
      stopetc.addWidget( PanicButton( self, self.player ) )
      leftpanel.addLayout( stopetc )
      leftpanel.addStretch()

      layout.addLayout( leftpanel )

      rightpanel = QVBoxLayout()

      sliders = SliderPanel( self, player )
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
      self.playWidget = PlayerWidget(self,self.player,self.record,inst=True)
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
   size = 35
   def __init__(self,parent,alive,enabled,enabledFile,disabledFile):
      QLabel.__init__(self,parent)
      self.enabledPixmap = QPixmap(enabledFile).scaledToHeight( PlayerButton.size, Qt.SmoothTransformation )
      self.disabledPixmap = QPixmap(disabledFile).scaledToHeight( PlayerButton.size, Qt.SmoothTransformation )
      self.setAlignment(Qt.AlignHCenter)
      self.setFixedSize( PlayerButton.size*1.1, PlayerButton.size*1.1 )
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
   def __init__(self,parent,player,playable=None,stop=True,fade=False):
      QWidget.__init__(self,parent)
      self.player = player
      self.playable = None
      self.layout = QHBoxLayout()
      self.layout.setSpacing(0)
      self.layout.addStretch()

      self.playButton = PlayerButton( self, False, False, 'icons/Play.png',
                                      'icons/Play-disabled.png' )
      self.playButton.mouseReleaseEvent = self.play
      self.layout.addWidget(self.playButton)

      if stop:
         self.stopButton = PlayerButton( self, False, False, 'icons/Stop.png',
                                         'icons/Stop-disabled.png' )
         self.stopButton.mouseReleaseEvent = self.stop
         self.layout.addWidget(self.stopButton)
      else:
         self.stopButton = None

      if fade:
         self.fadeButton = PlayerButton( self, False, False, 'icons/Fade.png',
                                         'icons/Fade-disabled.png' )
         self.fadeButton.mouseReleaseEvent = self.fade
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

   def setTrans(self,trans):
      if self.playable:
         self.playable.transpose = trans

   def setRT(self,colname,value):
      if self.playable:
         if colname == "TRANS":
            self.playable.transpose = value
         elif colname == "PROG0":
            self.playable.instrument = value
         else:
            raise ChurchPlayerError("\n\nPlayerWidget.setRT does not yet "
                                    "support column '{0}'.".format(colname) )

   def setPlayable(self,playable,prog0=None,trans=None):
      if playable != None:
         if not isinstance(playable,cpmodel.Record) and not isinstance(playable,cpmodel.Playlist):
            playable = self.player.cat.getRecord(int(playable),prog0,trans)

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
      if self.playButton.enabled:
         self.player.playMusic( self )

   def stop(self, event):
      if self.stopButton.enabled:
         self.player.stopMusic()

   def fade(self, event):
      if self.fadeButton.enabled:
         self.player.fadeMusic()

   def finish(self):
      self.stop(None)
      self.player.removeClient( self )


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

      if self.irow:
         self.col[ self.irow ] = text

class CatSpinBox(QSpinBox,CatItem):
   def __init__(self,parent,cat,irow,icol,opts,descs,t):
      QSpinBox.__init__(self,parent)
      self.setMaximum( 5000 )
      self.setMinimum( 0 )
      self.setSpecialValueText( " " )
      CatItem.__init__(self,parent,cat,irow,icol,opts,descs,t)
      self.valueChanged.connect(self.valueHasChanged)
      if irow:
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

      if irow:
         curval = cat[ cat.colnames[icol] ][irow]
      else:
         curval = "xxx"

      self.addItem(" ")

      icurr = -1
      i = 0
      for opt in opts:
         self.addItem(opt)
         if descs and len(descs) > i:
            self.setItemData( i + 1, descs[i], Qt.ToolTipRole )
         if opt == curval:
            icurr = i + 1
         i += 1

      if irow:
         if icurr == -1:
            self.addItem(curval)
            icurr = i
      else:
         icurr = 0

      self.setCurrentIndex( icurr )
      self.setFixedWidth(1.5*self.minimumSizeHint().width())
      self.currentIndexChanged.connect(self.indexHasChanged)

   def indexHasChanged(self, item ):
      self.catStore( str(self.itemText(item)) )

   def clear(self):
      self.setCurrentIndex( 0 )

class CatComboBoxM(QComboBox,CatItem):
   def __init__(self,parent,cat,irow,icol,opts,descs,t):
      QComboBox.__init__(self,parent)
      CatItem.__init__(self,parent,cat,irow,icol,opts,descs,t)

      if irow:
         self.curval = cat[ cat.colnames[icol] ][irow]
      else:
         self.curval = ""

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
      if irow:
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
      if irow:
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

      classifyAction = QAction(QIcon('icons/Tick.png'), '&Classify', self)
      classifyAction.setStatusTip('Classify music')
      classifyAction.triggered.connect(self.classify)
      classifyAction.setShortcut('Ctrl+L')

#      openAction = QAction(QIcon('icons/Open.png'), '&Open', self)
#      openAction.setStatusTip('Open an existing service or playlist')
#      openAction.triggered.connect(self.open)

      saveCatAction = QAction(QIcon('icons/SaveCat.png'), '&Save Catalogue', self)
      saveCatAction.setStatusTip('Save the music catalogue to disk')
      saveCatAction.triggered.connect(self.saveCatalogue)

#      scanAction = QAction( '&Scan', self)
#      scanAction.setShortcut('Ctrl+I')
#      scanAction.setStatusTip('Scan the music directory for uncatalogued MIDI files')
#      scanAction.triggered.connect(self.scan)

#  Set up status bar
      self.statusBar()

#  Set up menu bar
      menubar = self.menuBar()
      fileMenu = menubar.addMenu('&File')
#      fileMenu.addAction(openAction)
      fileMenu.addAction(exitAction)

      catMenu = menubar.addMenu('&Catalogue')
      catMenu.addAction(classifyAction)
#      catMenu.addAction(scanAction)
      catMenu.addAction(saveCatAction)

#  Set up the toolbar.
      toolbar = self.addToolBar('tools')
      toolbar.addAction(exitAction)
      toolbar.addAction(classifyAction)
#      toolbar.addAction(openAction)

#  The central widget
      pw = MainWidget( self, self.player, cat )
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
         del self.player.player
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

#  Ready to run...
    splash.finish(ex)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
