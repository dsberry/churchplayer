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
class Service(QFrame):
   def __init__(self,parent,player):
      QFrame.__init__(self,parent)
      self.setFrameStyle( QFrame.Box )
      self.player = player

      grid = QGridLayout()
      grid.setContentsMargins( 5, 5, 5, 0 )
      grid.setSpacing( 5 )

      j = 0
      for i in range(10):
         if i > 0:
            grid.addWidget( HLine(), j, 0, 1, 3 )
            j += 1

         item = ServiceItem( self, player )
         grid.addWidget( item.playButton, j, 0 )
         grid.addWidget( item.desc, j, 1 )
         grid.addWidget( item.kbdChooser, j, 2 )
         j += 1

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
class VolumeSlider(QSlider):
   def __init__(self,parent,player):
      QSlider.__init__(self,Qt.Vertical,parent)

      self.setToolTip("Drag and release to change the playback volume")
      self.sliderReleased.connect( self.changer )

   def changer(self):
      print( "Volume changed!!!")


# ----------------------------------------------------------------------
class PitchSlider(QSlider):
   def __init__(self,parent,player):
      QSlider.__init__(self,Qt.Vertical,parent)

      self.setToolTip("Drag and release to change the playback pitch")
      self.sliderReleased.connect( self.changer )

   def changer(self):
      print( "Pitch changed!!!")


# ----------------------------------------------------------------------
class TempoSlider(QSlider):
   def __init__(self,parent,player):
      QSlider.__init__(self,Qt.Vertical,parent)

      self.setToolTip("Drag and release to change the playback tempo")
      self.sliderReleased.connect( self.changer )

   def changer(self):
      print( "Tempo changed!!!")


# ----------------------------------------------------------------------
class ServiceItem(QWidget):
   def __init__(self,parent,player):
      QWidget.__init__(self,parent)
      self.player = player

      self.playButton = PlayerButton( self, False, 'icons/Play.png',
                                      'icons/Play-disabled.png' )
      self.playButton.mouseReleaseEvent = self.playit
      self.playButton.setToolTip("Click to play this item of music")

      self.desc = QLabel("Click here to choose music", self )
      self.desc.setToolTip("The music played when the play-button is clicked")
      self.desc.mouseReleaseEvent = self.musicChooser

      self.kbdChooser = QComboBox( self )
      self.kbdChooser.setToolTip("Choose the type of organ or piano to use")
      self.kbdChooser.currentIndexChanged.connect( self.kybdChooser )

   def playit(self, event):
      print( "PLAY clicked!!!")

   def musicChooser(self, event):
      print( "Desc clicked!!!")

   def kybdChooser(self):
      print( "Keyboard changed!!!")



# ----------------------------------------------------------------------
class PlayController(QWidget):
   def __init__(self,parent,player,cat):
      QWidget.__init__(self,parent)
      self.player = player
      self.cat = cat

      layout = QHBoxLayout()

      stop = PlayerButton( self, False, 'icons/Stop.png',
                           'icons/Stop-disabled.png' )
      stop.setToolTip("Stop any currently playing music abruptly")
      stop.mouseReleaseEvent = self.stopper
      layout.addWidget( stop )

      fade = PlayerButton( self, False, 'icons/Fade.png',
                           'icons/Fade-disabled.png' )
      fade.mouseReleaseEvent = self.fader
      fade.setToolTip("Fade out any currently playing music slowly")
      layout.addWidget( fade )

      self.setLayout( layout )

   def stopper(self, event ):
      print( "STOP clicked!!!")


   def fader(self, event ):
      print( "FADE clicked!!!")


# ----------------------------------------------------------------------
class MainWidget(QWidget):
   def __init__( self, parent, player, cat ):
      QWidget.__init__( self, parent )
      self.player = PlayController( self, player, cat )

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

      sliders =  QHBoxLayout()
      sliders.addStretch()

      sl1 = QVBoxLayout()
      self.volumeslider = VolumeSlider( self, self.player )
      sl1.addWidget( self.volumeslider )
      sl1.addWidget( QLabel("Volume" ) )
      sliders.addLayout( sl1 )

      sliders.addStretch()

      sl2 = QVBoxLayout()
      self.temposlider = TempoSlider( self, self.player )
      sl2.addWidget( self.temposlider )
      sl2.addWidget( QLabel("Tempo" ) )
      sliders.addLayout( sl2 )

      sliders.addStretch()

      sl3 = QVBoxLayout()
      self.pitchslider = PitchSlider( self, self.player )
      sl3.addWidget( self.pitchslider )
      sl3.addWidget( QLabel("Pitch" ) )
      sliders.addLayout( sl3 )

      sliders.addStretch()
      rightpanel.addLayout( sliders )

      layout.addLayout( rightpanel )

      self.setLayout( layout )




# ----------------------------------------------------------------------
class RecordForm(QWidget):
   def __init__(self,parent,dialog,player,cat,irow,editable=False,header=None):
      QWidget.__init__(self,parent)
      self.player = player
      self.cat = cat
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
      while waited < 20:
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
   size = 40
   def __init__(self,parent,enabled,enabledFile,disabledFile):
      QLabel.__init__(self,parent)
      self.enabledPixmap = QPixmap(enabledFile).scaledToHeight( PlayerButton.size, Qt.SmoothTransformation )
      self.disabledPixmap = QPixmap(disabledFile).scaledToHeight( PlayerButton.size, Qt.SmoothTransformation )
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
   def __init__(self,parent,player,playable=None,fade=False,inst=False):
      QWidget.__init__(self,parent)
      self.player = player
      self.playable = None
      self.layout = QHBoxLayout()
      self.layout.setSpacing(0)
      self.layout.addStretch()

      self.playButton = PlayerButton( self, False, 'icons/Play.png',
                                      'icons/Play-disabled.png', 'Play' )
      self.playButton.mouseReleaseEvent = self.play
      self.layout.addWidget(self.playButton)

      self.stopButton = PlayerButton( self, False, 'icons/Stop.png',
                                      'icons/Stop-disabled.png', 'Stop' )
      self.stopButton.mouseReleaseEvent = self.stop
      self.layout.addWidget(self.stopButton)

      if fade:
         self.fadeButton = PlayerButton( self, False, 'icons/Fade.png',
                                         'icons/Fade-disabled.png', 'Fade' )
         self.fadeButton.mouseReleaseEvent = self.fade
         self.layout.addWidget(self.fadeButton)
      else:
         self.fadeButton = None

      if inst:
         self.spin = QSpinBox( self )
         self.spin.setMinimum( 0 )
         self.spin.setMaximum( 127 )
         self.layout.addWidget(self.spin)

      self.setPlayable( playable )
      self.layout.addStretch()
      self.setLayout( self.layout )

   def setPlayable(self,playable):
      if not self.playable and playable:
         self.playButton.enable()
      elif self.playable and not playable:
         self.playButton.disable()

      self.playable = playable
      if playable:
         self.playButton.setToolTip("Click to play {0}".format(playable.desc()))
         self.stopButton.setToolTip("Click to stop {0}".format(playable.desc()))
         if self.fadeButton:
            self.fadeButton.setToolTip("Click to fade {0} gradually".format(playable.desc()))
      else:
         self.playButton.setToolTip("")
         self.stopButton.setToolTip("")
         if self.fadeButton:
            self.fadeButton.setToolTip("")

   def play(self, event ):
      if self.playButton.enabled:
         self.playButton.disable()
         self.stopButton.enable()
         if self.fadeButton:
            self.fadeButton.enable()
         if self.spin:
            inst = self.spin.value()
            if inst:
               self.playable.instrument = inst
            else:
               self.playable.instrument = cpmodel.DEFAULT_INSTRUMENT

         self.player.listener.stopped.connect(self.ended)
         self.player.play( self.playable, cpmodel.STOP )

   def stop(self, event):
      if self.stopButton.enabled:
         self.playButton.enable()
         self.stopButton.disable()
         if self.fadeButton:
            self.fadeButton.disable()
         self.player.stop( cpmodel.STOP )

   def fade(self, event):
      if self.stopButton.enabled:
         self.playButton.enable()
         self.stopButton.disable()
         if self.fadeButton:
            self.fadeButton.disable()
         self.player.stop( cpmodel.FADE )

   @pyqtSlot()
   def ended(self):
      if self.stopButton.enabled:
         self.playButton.enable()
         self.stopButton.disable()
         if self.fadeButton:
            self.fadeButton.disable()


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
      self.col[ self.irow ] = text

class CatSpinBox(QSpinBox,CatItem):
   def __init__(self,parent,cat,irow,icol,opts,descs,t):
      QSpinBox.__init__(self,parent)
      self.setMaximum( 5000 )
      CatItem.__init__(self,parent,cat,irow,icol,opts,descs,t)
      self.valueChanged.connect(self.valueHasChanged)
      text = cat[ cat.colnames[icol] ][irow]
      if text:
         self.setValue( int(text) )

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
      self.player = player

#  Set up tool tips
      QToolTip.setFont(QFont('SansSerif', 10))

#  Actions...
      exitAction = QAction(QIcon('icons/Exit.png'), '&Exit', self)
      exitAction.setStatusTip('Exit application')
      exitAction.triggered.connect(self.exit)

#      openAction = QAction(QIcon('icons/Open.png'), '&Open', self)
#      openAction.setStatusTip('Open an existing service or playlist')
#      openAction.triggered.connect(self.open)

#      saveCatAction = QAction(QIcon('icons/SaveCat.png'), '&Save Catalogue', self)
#      saveCatAction.setStatusTip('Save the music catalogue to disk')
#      saveCatAction.triggered.connect(self.saveCatalogue)

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

#      catMenu = menubar.addMenu('&Catalogue')
#      catMenu.addAction(scanAction)
#      catMenu.addAction(saveCatAction)

#  Set up the toolbar.
      toolbar = self.addToolBar('tools')
      toolbar.addAction(exitAction)
#      toolbar.addAction(openAction)

#  The central widget
      pw = MainWidget( self, player, cat )
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

    app = QApplication(sys.argv)

# Create and display the splash screen
    splash_pix = QPixmap('icons/splash-loading.png')
    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    splash.setMask(splash_pix.mask())
    splash.show()
    app.processEvents()

#  Set up the catalogue etc
    cat = cpmodel.Catalogue()
    app.processEvents()
    cat.verify()
    app.processEvents()
    player = cpmodel.Player()
    app.processEvents()
    player.listener = PlayerListener()
    app.processEvents()
    player.listener.start()
    app.processEvents()
    ex = ChurchPlayer( app, cat, player )

#  Ready to run...
    splash.finish(ex)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
