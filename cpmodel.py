DEFAULT_INSTRUMENT = -1
FADE = 0
STOP = 1

FADE_CMD = "f"
STOP_CMD = "s"
PLAY_CMD = "p"
EMPTY_CMD = "e"

PLAYING_CODE = "p"
STOPPED_CODE = "s"
ENDING_CODE = "e"

WFIFO = "/tmp/churchplayerfifo_wr"

import signal
import os.path
import subprocess
import sys
import time
import psutil
import os
import re
import commands
import copy

def midiInstrument( value ):
   if value == DEFAULT_INSTRUMENT:
      return value

   elif isinstance( value, int ):
      return value

   elif isinstance( value, str ):
      if value.isdigit():
         return int( value )
      elif value == "ORGAN":
         return 20
      else:
         return DEFAULT_INSTRUMENT

   else:
      return DEFAULT_INSTRUMENT

# ----------------------------------------------------------------------
class ChurchPlayerError(Exception):
   """

   A base class for all the classes of Exception that can be raised by
   this module.

   """
   pass


# ----------------------------------------------------------------------
class Catalogue(dict):

   def __init__(self):
      super(Catalogue, self).__init__()
      self.warnings = []
      self._readCatalogue()
      self.modified = False
      self.midifiles = []




#  Open the catalogue disk file and read its contents into the properties
#  of this Catalogue object.
   def _readCatalogue(self):

#  Decide on the catalogue file to be opened.
      if "CPMUSIC" in os.environ:
         self.catname = os.environ[ "CPMUSIC" ]
      else:
         self.catname = os.path.join(os.path.dirname(sys.argv[0]), "cpmusic.txt")

      if not os.path.isfile( self.catname ):
         raise ChurchPlayerError("\n\nMusic catalogue {0} does not "
                                 "exist".format(self.catname))

#  Create regexps to match each sort of line in the catalogue file.
      white = re.compile( "^\s*$" )
      comment = re.compile( "^#" )
      column = re.compile( "^c:(\S+) +(.+)$" )
      root = re.compile( "^r:(\S+)$" )
      book = re.compile( "^b:(\S+) +(.+)$" )
      instrumentation = re.compile( "^i:(\S+) +(.+)$" )
      origin = re.compile( "^o:(\S+) +(.+)$" )
      tags = re.compile( "^t:(\S) +(.+)$" )
      record = re.compile( "@" )

#  Initialise all the arrays to store the header info read from the
#  catalogue.
      self.rootdir = os.path.join(os.path.dirname(sys.argv[0]), "music")
      self.colnames = []
      self.coldescs = []
      self.booknames = []
      self.bookdescs = []
      self.instrnames = []
      self.instrdescs = []
      self.orignames = []
      self.origdescs = []
      self.tagnames = []
      self.tagdescs = []
      self.ncol = 0
      self.nrow = 0

#  Open the catalogue file and read each line in turn, removing any trailing
#  or leading white space (e.g. the trailing newline character).
      cat = open( self.catname, "r" )
      for line in cat:
         line = line.strip()

#  Classify the line by matching it against each regexp created above.
#  Extract the required info from each sort of header line and store in
#  the arrays created above.
         match = comment.search( line )
         if match:
            continue

         match = white.search( line )
         if match:
            continue

         match = root.search( line )
         if match:
            self.rootdir = match.group(1)
            continue

         match = column.search( line )
         if match:
            self.colnames.append( match.group(1) )
            self.coldescs.append( match.group(2) )

#  For each column name, create a new empty array and store it as a new
#  entry in the parent dict using the column name as the key name.
            self[match.group(1)] = []
            self.ncol += 1
            continue

         match = book.search( line )
         if match:
            self.booknames.append( match.group(1) )
            self.bookdescs.append( match.group(2) )
            continue

         match = instrumentation.search( line )
         if match:
            self.instrnames.append( match.group(1) )
            self.instrdescs.append( match.group(2) )
            continue

         match = origin.search( line )
         if match:
            self.orignames.append( match.group(1) )
            self.origdescs.append( match.group(2) )
            continue

         match = tags.search( line )
         if match:
            self.tagnames.append( match.group(1) )
            self.tagdescs.append( match.group(2) )
            continue

#  If this line describes a midi file (rather than being a header line),
#  split it into fields and check that the number of fields matches the
#  number of columns. If so, append each field value to the end of the
#  arrays in the parent dict.
         match = record.search( line )
         if match:
            values = line.split("@")
            nv = len(values)
            if nv > self.ncol:
               self.warnings.append("Too many columns ({1}) in line: '{0}'".
                                    format( line, nv ) )
               nv = self.ncol
            elif nv < self.ncol:
               self.warnings.append("Too few columns ({1}) in line: '{0}'".
                                    format( line, nv ) )
            for i in range(nv):
               if values[i] == '':
                  values[i] = None
               self[ self.colnames[i] ].append( values[i] )

            if nv < self.ncol:
               for i in range(nv,self.ncol):
                  self[ self.colnames[i] ].append( None )

            self.nrow += 1
            continue

#  Arrive here if the line does not match any of the expected line
#  formats (i.e. regexps).
         self.warnings.append("Cannot interpret line: '{0}'".format( line ) )

#  Close the catalogue file.
      cat.close()




#  Verify the values read from the catalogue.
   def verify(self):
      irow = -1
      for tags in self['TAGS']:
         irow += 1
         if tags:
            for tag in tags:
               if tag not in self.tagnames:
                  self.warnings.append("Unknown tag character ('{0}') "
                    "associated with '{1}'.".format(tag,self['TITLE'][irow] ) )
      irow = -1
      for origin in self['ORIGIN']:
         irow += 1
         if origin:
            if origin not in self.orignames:
                  self.warnings.append("Unknown origin ('{0}') associated"
                           "with '{1}'.".format(origin, self['TITLE'][irow] ) )
      irow = -1
      for book in self['BOOK']:
         irow += 1
         if book:
            if book not in self.booknames:
                  self.warnings.append("Unknown book ('{0}') associated"
                  " with '{1}'.".format(book,self['TITLE'][irow] ) )
      irow = -1
      for instr in self['INSTR']:
         irow += 1
         if instr:
            if instr not in self.instrnames:
                  self.warnings.append("Unknown instrumentation ('{0}') "
                       "associated with '{1}'.".format(instr, self['TITLE'][irow] ) )

      for colname in ('NUMBER','NVERSE','TRANS','SPEED','VOLUME','PROG0'):
         irow = -1
         for value in self[colname]:
            irow += 1
            if value:
               try:
                  ival = int( value )
               except Exception:
                  self.warnings.append("Illegal value ('{0}') for column "
                          "{2} associated with '{1}'.".
                          format(value, self['TITLE'][irow],colname ) )
            else:
               self[colname][ irow ] = "0"

#  Check all the midi files exist.
      for path in self['PATH']:
         if path:
            midifile = os.path.join(self.rootdir,path)
            ismidi = self._isMidi( midifile )
            if ismidi == 2:
               self.midifiles.append( None )
               self.warnings.append("Midi file {0} cannot be found within "
                                    "directory {1}.".format( path, self.rootdir ) )
            elif ismidi == 1:
               self.midifiles.append( None )
               self.warnings.append("Music file {0} is not a usable MIDI "
                                    "file .".format( midifile ) )
            else:
               self.midifiles.append( midifile )

         else:
            self.midifiles.append( None )
            self.warnings.append("No midi file given for '{1}'.".
                                 format(instr, self['TITLE'][irow] ) )


#  Search for any uncatalogued midi files in the root directory. Return a
#  new catalogue that contains their paths, and guesses at everything else.
#  The structure of the new catalogue is inherited from self.
   def searchForNew(self):
      newMidis = []
      badMidis = []

      rlen = len( self.rootdir ) + 1
      for root, subFolders, files in os.walk(self.rootdir):
         for file in files:
            if os.path.splitext(file)[1] == ".mid":
               midifile = os.path.join( root, file )
               newpath = midifile[rlen:]
               if newpath not in self["PATH"]:
                  if self._isMidi( midifile ) == 0:
                     newMidis.append( newpath )
                  else:
                     badMidis.append( newpath )

      ngood = len(newMidis)
      nbad = len(badMidis)
      if ngood + nbad > 0:
         newcat = copy.copy( self )
         newcat.nrow = ngood + nbad

         num = re.compile( "^(\d+)\W*(.*)" )

         for col in newcat:
            newcat[col] = [''] * ( ngood + nbad )

         newcat.midifiles = []
         newcat['PATH'] = []
         newcat['BOOK'] = []
         newcat['NUMBER'] = []
         newcat['INSTR'] = []
         newcat['TITLE'] = []
         newcat['ORIGIN'] = []
         newcat['TRANS'] =['0'] * ( ngood + nbad )
         newcat['SPEED'] =['0'] * ( ngood + nbad )
         newcat['VOLUME'] =['0'] * ( ngood + nbad )
         newcat['PROG0'] =[]

         for file in newMidis:
            newcat.midifiles.append( os.path.join( self.rootdir, file ) )
            newcat['PATH'].append( file )
            dir = os.path.dirname( file )

            if dir.upper() in self.booknames:
               newcat['BOOK'].append( dir.upper() )
               if dir.upper() == 'STF':
                  newcat['INSTR'].append( 'KEYBD' )
                  newcat['PROG0'].append( '0' )
               else:
                  newcat['INSTR'].append( '' )
                  newcat['PROG0'].append( '-1' )
            else:
               newcat['BOOK'].append( '' )
               newcat['INSTR'].append( '' )
               newcat['PROG0'].append( '-1' )

            if dir.upper() in self.orignames:
               newcat['ORIGIN'].append( dir.upper() )
            else:
               newcat['ORIGIN'].append( '' )

            basename = os.path.splitext( os.path.basename( file ) )[0]
            match = num.search( basename )
            if match:
               print( match.group(1) )
               newcat['NUMBER'].append( match.group(1).strip() )
               title = match.group(2)
            else:
               newcat['NUMBER'].append( '' )
               title = basename
            title = re.sub( '[^0-9a-zA-Z+]', ' ', title )
            if not title.strip():
               title = basename
            newcat['TITLE'].append( title.strip() )

         for file in badMidis:
            newcat.midifiles.append( None )
            newcat['PATH'].append( file )
            newcat['BOOK'].append( '' )
            newcat['NUMBER'].append( '' )
            newcat['TITLE'].append( '' )
            newcat['INSTR'].append( '' )
            newcat['ORIGIN'].append( '' )

         return newcat
      else:
         return None


#  Add a new row to the end of the catalogue
   def addrow(self,row):
      icol = 0
      for colname in self.colnames:
         self[ colname ].append( row[icol] )
         icol += 1
      self.nrow += 1
      self.modified = True

#  Create a playable Record from a row of the catalogue
   def getRecord(self,row):
      path = self.midifiles[row]
      if path:
         trans = self['TRANS'][row]
         instr = self['INSTR'][row]
         title = self['TITLE'][row]
         if not trans:
            trans = '0'
         return Record( path, trans, instr, title )
      else:
         return None

#  Return a tuple in which the first item indicates the type of the
#  column ('t'=arbitrary text,'i'=positive integer, 's'=single selection
#  from choice,'m'=multiple selections from choice). For 's' and 'm', the
#  second item is a list of options, and the third item is a list of
#  option descriptions (which may be None).
   def getOptions(self,icol):
      type = 't'
      names = None
      descs = None

      if self.colnames[icol] == "TAGS":
         type = 'm'
         names = self.tagnames
         descs = self.tagdescs

      elif self.colnames[icol] == "BOOK":
         type = 's'
         names = self.booknames
         descs = self.bookdescs

      elif self.colnames[icol] == "NUMBER":
         type = 'i'
         descs = "Hymn/song number within book"

      elif self.colnames[icol] == "INSTR":
         type = 's'
         names = self.instrnames
         descs = self.instrdescs

      elif self.colnames[icol] == "TRANS":
         type = 's'
         names = []
         descs = []
         for i in range(-6,7):
            names.append(str(i))
            if i < -1:
               descs.append("Transpose down by {0} semitones".format(-i))
            elif i == -1:
               descs.append("Transpose down by 1 semitone" )
            elif i == 0:
               descs.append("Play in original key" )
            elif i == 1:
               descs.append("Transpose up by 1 semitone" )
            else:
               descs.append("Transpose up by {0} semitones".format(i))

      elif self.colnames[icol] == "NVERSE":
         type = 's'
         names = []
         descs = []
         for i in range(10):
            names.append(str(i))
            if i == 0:
               descs.append("Does not have regular repeated verses")
            elif i == 1:
               descs.append("Has only 1 verse" )
            else:
               descs.append("Has {0} verses".format(i))

      elif self.colnames[icol] == "ORIGIN":
         type = 's'
         names = self.orignames
         descs = self.origdescs

      elif self.colnames[icol] == "TITLE":
         type = 't'
         descs = "Title of hymn/song"

      elif self.colnames[icol] == "PATH":
         type = 'l'
         descs = "Path to midi file within the music directory"

      return (type,names,descs)


#  Test if a path refers to an existing usable midi file. Returns 0 if it
#  is, 1 if the file exists but is not a usable midi file, and 2 if the file
#  does not exist.
   def _isMidi(self,path):
      if os.path.isfile( path ):
         text = commands.getstatusoutput( "file '{0}'".format(path) )
         if "Standard MIDI" in text[1]:
            return 0
         else:
            return 1
      else:
         return 2

   def save(self):
      self.modified = False
      for version in range(10000000):
         backup = "{0}_v{1}".format(self.catname,version+1)
         if not os.path.isfile( backup ):
            break
      os.rename( self.catname, backup )

      cat = open( self.catname, "w" )
      cat.write("# Path to root directory for MIDI files\n# -------------------------------------\n")
      cat.write("r:{0}\n".format(self.rootdir))
      cat.write("\n# Column names and titles:\n# ------------------------\n")
      for (name,desc) in zip( self.colnames,self.coldescs):
         cat.write("c:{0} {1}\n".format(name,desc))
      cat.write("\n# Known books:\n# ------------\n")
      for (name,desc) in zip( self.booknames,self.bookdescs):
         cat.write("b:{0} {1}\n".format(name,desc))
      cat.write("\n# Known instrumentations:\n# -----------------------\n")
      for (name,desc) in zip( self.instrnames,self.instrdescs):
         cat.write("i:{0} {1}\n".format(name,desc))
      cat.write("\n# Known origins:\n# --------------\n")
      for (name,desc) in zip( self.orignames,self.origdescs):
         cat.write("o:{0} {1}\n".format(name,desc))
      cat.write("\n# Classification tags (all single characters) and descriptions:\n# -------------------------------------------------------------\n")
      for (name,desc) in zip( self.tagnames,self.tagdescs):
         cat.write("t:{0} {1}\n".format(name,desc))

      cat.write("\n\n\n# Data:\n# ----\n")
      for irow in range(self.nrow):
         icol = 0
         text = ""
         for col in self.colnames:
            if icol > 0:
               text += "@"
            if self[col][irow]:
               text += self[col][irow]
            icol += 1
         text += "\n"
         cat.write(text)

      cat.close()

# ----------------------------------------------------------------------
class Record(object):
   def __init__(self, path, transpose=0, instrument=DEFAULT_INSTRUMENT,
                title="" ):
      self._setPath( path )
      self._setTranspose( transpose )
      self._setInstrument( instrument )
      self._setTitle( title )

   def _getPath(self):
         return self._path
   def _setPath(self,path):
         if os.path.isfile( path ):
            self._path = path
         else:
            raise  ChurchPlayerError("\n\nFailed to create a new Record: No "
                                     "such file '{0}'.".format(path))
   path = property(_getPath, None, None, "The path to the music file")

   def _getTranspose(self):
         return self._transpose
   def _setTranspose(self,transpose):
         if isinstance(transpose,str):
            transpose = int( transpose )
         if transpose < -8 or transpose > 8:
            raise  ChurchPlayerError("\n\nFailed to transpose a Record: "
                                     "requested key shift ({0} semitones) "
                                     "is too great.".format(transpose))
         else:
            self._transpose = transpose
   def _delTranspose(self):
         self._transpose = 0
   transpose = property( _getTranspose, _setTranspose, _delTranspose,
                         "The number of semitones to transpose" )

   def _getInstrument(self):
         return self._instrument
   def _setInstrument(self,instrument):
         instrument = midiInstrument( instrument )
         if instrument == None or instrument == DEFAULT_INSTRUMENT:
            self._instrument = DEFAULT_INSTRUMENT
         elif instrument < 0 or instrument > 127:
            raise  ChurchPlayerError("\n\nFailed to change instrument for a "
                                     "Record: requested instrument number "
                                     "({0}) is illegal (must be between 0 "
                                     "and 127).".format(instrument))
         else:
            self._instrument = instrument
   def _delInstrument(self):
         self._instrument = DEFAULT_INSTRUMENT
   instrument = property( _getInstrument, _setInstrument, _delInstrument,
                         "The GM program number for the instrument to use")

   def _getTitle(self):
         return self._title
   def _setTitle(self,title):
         self._title = title

   title = property(_getTitle, None, None, "The music title")


   def __str__(self):
      return "Path:{0}  Tran:{1} Instr:{2}  Title:{3}".format(self._getPath(),self._getTranspose(),self._getInstrument(),self._getTitle())


   def desc(self):
      return self._title


# ----------------------------------------------------------------------
class Playlist(object):
   def __init__(self):
      self.__records = []

   def add( self, path, transpose=0, instrument=DEFAULT_INSTRUMENT, title="" ):
      self.__records.append( Record( path, transpose, instrument, title ) )

   def __len__(self):
      return len(self.__records)
   def __getitem__(self, key):
      return self.__records[key]
   def __setitem__(self, key, value):
      raise ChurchPlayerError("\n\nAttempt to change the contents of a Playlist")
   def __delitem__(self, key):
      raise ChurchPlayerError("\n\nAttempt to delete a record from a PlayList" )
   def __iter__(self):
      self.__inext = -1
      return self
   def __next__(self):
      return self.next()
   def next(self):
      self.__inext += 1
      if self.__inext < len( self.__records ):
         return self.__records[ self.__inext ]
      else:
         raise StopIteration


   def __str__(self):
      result = ""
      for record in self.__records:
         result = "{0}{1}\n".format(result,record)
      return result






# ----------------------------------------------------------------------
class Player(object):

   def __init__(self):
      self._serverPopen = None
      self._controllerPopen = None
      self._start()

   def __del__(self):
      self._stop()

   def _stop(self):
      print( "Killing player processes" )
      self._killServerProcess();
      self._killControllerProcess();

   def _start(self):
      self._startServerProcess()
      self._startControllerProcess()

   def _startServerProcess(self):
      self._serverPopen = subprocess.Popen(["./server"])
      time.sleep(2)

   def _killProcess(self, name ):
      os.system("killall -9 {0}".format(name));

   def _killServerProcess(self):
      self._killProcess( "fluidsynth" )
      self._killProcess( "server" )

   def _killControllerProcess(self):
      self._killProcess( "aplaymidi" )
      self._killProcess( "controller" )

   def _startControllerProcess(self):
      self._controllerPopen = subprocess.Popen(["./controller","-v"])
      time.sleep(2)

   def _sendCommand( self, command ):
      os.system( "./sendcommand {0}".format(command))

   def _playRecord( self, record ):
      self._sendCommand( "{0} '{1}' {2} {3}".format( PLAY_CMD,
                         record.path, record.transpose,
                         record.instrument ))

   def _end( self, end ):
      if end == FADE:
         self._sendCommand( FADE_CMD )
      elif end != None:
         self._sendCommand( STOP_CMD )


#  Restart all processes (e.g. for use in case of a note being stuck on).
   def restart(self):
      print("Restarting server and controller processes...")
      self._stop()
      self._start()

#  Queue a Playlist or a Record, optionally aborting any currently playing
#  music first so that the new music starts immediately ("end" can be
#  FADE, STOP or None - in which case the music is just added to the end
#  of the queue).
   def play( self, playable, end=FADE ):
      if isinstance( playable, Record ):
         self._end( end )
         self._playRecord( playable )
      elif isinstance( playable, Playlist ):
         self._end( end )
         for record in playable:
            self._playRecord( record )
      else:
         raise  ChurchPlayerError("\n\nPlayer.play(): Supplied object is "
                                  "not a Record or Playlist" )

#  Move onto the next queued item.
   def next( self, end=FADE ):
      self._end( end )

#  Stop the current item and empty the player queue.
   def stop( self, end=FADE ):
      self._sendCommand( EMPTY_CMD )
      self._end( end )



