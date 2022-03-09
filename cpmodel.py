FIXED_INSTRUMENT = -2
DEFAULT_INSTRUMENT = -1
FADE = 0
STOP = 1
NRAND = 20

FADE_CMD = "f"
STOP_CMD = "s"
PLAY_CMD = "p"
EMPTY_CMD = "e"
PROG0_CMD = "i"
TRANS_CMD = "r"
SPEED_CMD = "m"

PLAYING_CODE = "p"
STOPPED_CODE = "s"
ENDING_CODE = "e"
REMAINING_CODE = "r"

WFIFO = "/tmp/churchplayerfifo_wr"
FSFIFO = "/tmp/fluidsynthfifo"

JOLLY_ORGAN = 'Organ 7'
QUIET_ORGAN = 'Organ 9'
JOLLY_PIANO = 'Piano 2'
QUIET_PIANO = 'Warm Piano 1'

EXCLUDE_FROM_GENERAL = 'cavel'

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
import random

instrumentNames = [
   'Original',
   'Piano 1',
   'Warm Piano 1',
   'Piano 2',
   'Piano 3',
   'E-Piano 1',
   'Warm E-Piano 1',
   'E-Piano 2',
   'E-Piano 3',
   'E-Piano 4',
   'Organ 1',
   'Organ 2',
   'Organ 3',
   'Organ 4',
   'Organ 5',
   'Organ 6',
   'Organ 7',
   'Organ 8',
   'Organ 9',
   'Organ 10',
   'Organ 11',
   'Harpsichord',
   'Vibraphone',
   'Xylophone',
   'Strings'
]

#  These are most GM numbers, but with some extra organs.
instruments = {
   '(ensemble)': FIXED_INSTRUMENT,
   'Original': DEFAULT_INSTRUMENT,
   'Piano 1': 0,
   'Warm Piano 1': 1,
   'Piano 2': 2,
   'Piano 3': 3,
   'E-Piano 1': 4,
   'Warm E-Piano 1': 5,
   'E-Piano 2': 7,
   'E-Piano 3': 8,
   'E-Piano 4': 9,
   'Organ 1': 127,
   'Organ 2': 120,
   'Organ 3': 118,
   'Organ 4': 119,
   'Organ 5': 121,
   'Organ 6': 123,
   'Organ 7': 122,
   'Organ 8': 124,
   'Organ 9': 125,
   'Organ 10': 126,
   'Organ 11': 19,
   'Harpsichord': 6,
   'Vibraphone': 11,
   'Xylophone': 13,
   'Strings': 48
}

instrumentByNumber = {}
for instr in instruments:
   instrumentByNumber[instruments[instr]] = instr

def midiInstrument( value ):
   if isinstance( value, int ):
      return value

   elif isinstance( value, str ):
      if value.isdigit():
         return int( value )

      elif value in instruments:
         return instruments[value]

      else:
         return DEFAULT_INSTRUMENT

   else:
      return DEFAULT_INSTRUMENT

def waitForProcess( name ):
   ntry = 0
   while ntry >= 0:
      try:
         subprocess.check_output(["pidof",name])
         ntry = -1
      except subprocess.CalledProcessError:
         ntry += 1
         if ntry < 60:
            time.sleep(1)
         else:
            ntry = -1
            raise ChurchPlayerError("\n\nWaited {0} seconds for the {1} "
                                    "process to start, but no luck. "
                                    "Something is wrong :-( ".format(ntry,name) )

#  Test if a path refers to an existing usable midi file. Returns 0 if it
#  is, 1 if the file exists but is not a usable midi file, and 2 if the file
#  does not exist.
def isMidi(path):
   if os.path.isfile( path ):
      text = commands.getstatusoutput( "file '{0}'".format(path) )
      if "Standard MIDI" in text[1]:
         return 0
      else:
         return 1
   else:
      return 2

# ----------------------------------------------------------------------
class ChurchPlayerError(Exception):
   """

   A base class for all the classes of Exception that can be raised by
   this module.

   """
   pass


# ----------------------------------------------------------------------
class Catalogue(dict):

   def __init__(self,readcat=True):
      super(Catalogue, self).__init__()
      self.warnings = []
      if readcat:
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
      column = re.compile( "^c:(\S+) +([01]) +([0-9]+) +(.+)$" )
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
      self.colsearchable = []
      self.coluser = []
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
      self.usercols = [None]*20
      self.metres = []

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
            colname = match.group(1)
            self.colnames.append( colname )
            if match.group(2) == "1":
               self.colsearchable.append( True )
            else:
               self.colsearchable.append( False )
            iuser = int( match.group(3) )
            self.coluser.append(iuser)
            if iuser > 0:
               self.usercols[iuser-1] = colname

            self.coldescs.append( match.group(4) )

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

#  Traditional hymns should use an organ by default, not a piano.
            if self[ 'TAGS' ][ -1 ] and self[ 'INSTR' ][ -1 ] == "KEYBD":
               if "H" in self[ 'TAGS' ][ -1 ]:
                  if int(self[ 'PROG0' ][ -1 ]) == DEFAULT_INSTRUMENT:
                     if "Q" in self[ 'TAGS' ][ -1 ]:
                        prog0 = instruments[ QUIET_ORGAN ]
                     else:
                        prog0 = instruments[ JOLLY_ORGAN ]
                     self[ 'PROG0' ][ -1 ] = prog0

#  Quiet modern should default to warm piano
               elif "M" in self[ 'TAGS' ][ -1 ]:
                  if int(self[ 'PROG0' ][ -1 ]) == DEFAULT_INSTRUMENT:
                     if "Q" in self[ 'TAGS' ][ -1 ]:
                        prog0 = instruments[ QUIET_PIANO ]
                     else:
                        prog0 = instruments[ JOLLY_PIANO ]
                     self[ 'PROG0' ][ -1 ] = prog0

            self.nrow += 1
            continue

#  Arrive here if the line does not match any of the expected line
#  formats (i.e. regexps).
         self.warnings.append("Cannot interpret line: '{0}'".format( line ) )

#  Close the catalogue file.
      cat.close()

#  Get a map giving the column index for each column name.
      self.colindices = {}
      for i in range( len(self.colnames) ):
         self.colindices[ self.colnames[i] ] = i

#  Remove unused elements from the usercols list.
      self.usercols = [x for x in self.usercols if x]

#  Get a list of the different metres found in the catalogue.
      for metre in self['METRE']:
         if metre:
            if metre not in self.metres:
               self.metres.append( metre )
      self.metres.sort()

#  Cannot search on metre if none were found in the catalogue.
      if len(self.metres) == 0:
         icol = self.colnames.index('METRE')
         if icol >= 0:
            self.colsearchable[icol] = False

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
            if instr != "KEYBD":
               self['PROG0'][irow] = FIXED_INSTRUMENT

      for colname in ('NUMBER','TRANS','SPEED','VOLUME','PROG0'):
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
            if os.path.isfile( midifile ):
               self.midifiles.append( midifile )
            else:
               self.midifiles.append( None )
               self.warnings.append("Midi file {0} cannot be found within "
                                    "directory {1}.".format( path, self.rootdir ) )
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
                  if isMidi( midifile ) == 0:
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
            newcat['PROG0'].append( '' )

         return newcat
      else:
         return None


#  Add a new row to the end of the catalogue
   def addrow(self,row,midifile):
      icol = 0
      for colname in self.colnames:
         self[ colname ].append( row[icol] )
         icol += 1
      self.midifiles.append(midifile)
      self.nrow += 1
      self.modified = True

#  Remove a row from the catalogue, specified by index.
   def delrow(self,irow):
      for colname in self.colnames:
         del self[ colname ][ irow ]
      del self.midifiles[ irow ]
      self.nrow -= 1
      self.modified = True

#  Create a playable Record from a row of the catalogue
   def getRecord(self,row,prog0=None,trans=None,volume=None,tempo=None):
      path = self.midifiles[row]
      if path:
         if None == trans:
            trans = self['TRANS'][row]
         if None == prog0:
            prog0 = self['PROG0'][row]
         if None == volume:
            volume = self['VOLUME'][row]
         if None == tempo:
            tempo = self['SPEED'][row]
         title = self['TITLE'][row]
         return Record( path, row, trans, tempo, volume, prog0, title )
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

      elif self.colnames[icol] == "METRE":
         type = 's'
         names = self.metres
         descs = "The metrical pattern of the hymn"

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


   def save(self):
      self.modified = False
      for version in range(10000000):
         backup = "{0}_v{1}".format(self.catname,version+1)
         if not os.path.isfile( backup ):
            break
      os.rename( self.catname, backup )

      print("Saving changes to music catalogue" )
      cat = open( self.catname, "w" )
      cat.write("# Path to root directory for MIDI files\n# -------------------------------------\n")
      cat.write("r:{0}\n".format(self.rootdir))
      cat.write("\n# Column names, 'searchable' flags, 'user interest' flag, and titles:\n# --------------------------------------------------------\n")
      for (name,sea,user,desc) in zip(self.colnames,self.colsearchable,self.coluser,self.coldescs):
         if sea:
            sea = 1
         else:
            sea = 0
         cat.write("c:{0} {1} {2} {3}\n".format(name,sea,user,desc))
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
               text += str(self[col][irow])
            icol += 1
         text += "\n"
         cat.write(text)

      cat.close()

   def getUserValues(self,irow):
      vals = []
      tips = []
      widths = []

      for col in self.usercols:
         val = self[col][irow]
         if not val:
            val = ""
            tip = None
            ok = False
         else:
            ok = True

         if col == "TITLE":
            width = 500;
            if ok:
               val = '"{0}"'.format(val)
               tip = "The title or first line"

         elif col == "METRE":
            width = 150;
            if ok:
               val = '"{0}"'.format(val)
               tip = "The rhythmic metre of the hymn/song"

         elif col == "TUNE":
            width = 250;
            if ok:
               val = '({0})'.format(val)
               tip = "The name of the tune"

         elif col == "BOOK":
            width = 50;
            if ok:
               tip = self.bookdescs[self.booknames.index(val)]

         elif col == "TAGS":
            width = 60;
            if ok:
               tip = None
               if val != "":
                  for i in range(len(self.tagnames)):
                     if self.tagnames[i] in val:
                        if tip == None:
                           tip = "Tags: {0}".format(self.tagdescs[i])
                        else:
                           tip = "{0}, {1}".format(tip,self.tagdescs[i])

         elif col == "INSTR":
            width = 100;
            if ok:
               for i in range(len(self.instrnames)):
                  if self.instrnames[i] == val:
                     tip = "Instrumentation: {0}".format(self.instrdescs[i])

         elif col == "ORIGIN":
            width = 50;
            if ok:
               if val == "STF":
                  tip = "The midi file was made by Methodist Publishing House"
               elif val == "DSB":
                  tip = "The midi file was made by David Berry"
               else:
                  tip = "The origin of the midi file..."

         else:
            width = 50;
            tip = None

         vals.append( val )
         tips.append( tip )
         widths.append( width )

      return zip(vals,tips,widths)

   def countTagMatches( self, tags ):
      icol = self.colindices["TAGS"]
      return len( self.search( [tags], [icol], sort=False ) )

   def search( self, searchVals, searchCols, sort=True ):
      matchingRows = range( self.nrow )
      nmatch = self.nrow

      book = None
      number = None
      for (icol,val) in zip(searchCols,searchVals):
         if val:
            if self.colnames[icol] == 'BOOK':
               book = val.upper()
            elif self.colnames[icol] == 'NUMBER':
               number = int(val)

      if book and number:
         isalso = "{0}:{1}".format(book,number)
      else:
         isalso = None

      for (icol,val) in zip(searchCols,searchVals):
         if val:
            newmatches = []
            col = self.colnames[icol]
            if col == "TAGS":
               tags = list( val.lower() )

               for irow in matchingRows:
                  lctext = self[col][irow]
                  if lctext:
                     lctext = lctext.lower()
                     ok = True
                     for tag in tags:
                        if tag == "g":
                           general = True
                           for xtag in EXCLUDE_FROM_GENERAL:
                              if xtag in lctext:
                                 general = False
                                 break;
                           if not general:
                              ok = False
                              break
                        elif not tag in lctext:
                           ok = False
                           break
                     if ok:
                        newmatches.append( irow )

            elif col == "TITLE":
               words = val.lower().split()

               for irow in matchingRows:
                  title_words = re.compile('\w+').findall(self[col][irow].lower())
                  ok = True
                  for word in words:
                     if not word in title_words:
                        ok = False
                        break
                  if ok:
                     newmatches.append( irow )

            elif ( col == "BOOK" or col == "NUMBER" ) and isalso:
               for irow in matchingRows:
                  if self[col][irow] == val:
                     newmatches.append( irow )
                  elif self['ISALSO'][irow]:
                     if isalso+" " in self['ISALSO'][irow]:
                        newmatches.append( irow )
                     elif self['ISALSO'][irow].endswith(isalso):
                        newmatches.append( irow )

            else:
               for irow in matchingRows:
                  if self[col][irow] == val:
                     newmatches.append( irow )

            matchingRows = newmatches

         if len( matchingRows ) == 0:
            break;

      if sort and len( matchingRows ) > 1:
         keys = {}
         for irow in matchingRows:
            thisbook = self['BOOK'][irow]
            if  book and thisbook == book:
               thisbook = "AAAA"+thisbook
            thisorigin = self['ORIGIN'][irow]
            thistitle = self['TITLE'][irow]
            keys[irow] = "{0}_{1}_{2}".format(thisorigin,thisbook,thistitle)
         matchingRows.sort( key=lambda irow: keys[irow] )

      return matchingRows

   def makePlaylist( self, irows ):
      result = Playlist()
      for irow in irows:
         title = "{0} {1}: {2}".format(self['BOOK'][irow],self['NUMBER'][irow],self['TITLE'][irow] )

         result.add( self.rootdir+"/"+self['PATH'][irow], irow,
                     self['TRANS'][irow],
                     self['SPEED'][irow],
                     self['VOLUME'][irow],
                     self['PROG0'][irow],
                     title )
      return result

#  Find the row index of an entry with a given path.
   def findPath(self,path):
      tpath = str(path)
      if tpath.startswith( self.rootdir+"/" ):
         npath = tpath[ len(self.rootdir+"/"): ]
      else:
         npath = tpath
      try:
         result = self['PATH'].index( npath )
      except ValueError:
         result = -1
      return result

# ----------------------------------------------------------------------
class Record(object):
   def __init__(self, path, irow, trans, speed, volume, prog0, title ):

      self._setPath( path )
      self._setIrow( irow )
      self._setTranspose( trans )
      self._setInstrument( prog0 )
      self._setTitle( title )
      self._setVolume( volume )
      self._setTempo( speed )

   def _getPath(self):
         return self._path
   def _setPath(self,path):
         ismidi = isMidi(path)
         if ismidi == 1:
            raise  ChurchPlayerError("\n\nFailed to create a new Record: Not "
                                     "a usable MIDI file '{0}'.".format(path))
         elif ismidi == 2:
            raise  ChurchPlayerError("\n\nFailed to create a new Record: No "
                                     "such file '{0}'.".format(path))
         else:
            self._path = path

   path = property(_getPath, None, None, "The path to the music file")

   def _getIrow(self):
         return self._irow
   def _setIrow(self,irow):
         if isinstance(irow,str):
            irow = int( irow )
         if irow < 0:
            raise  ChurchPlayerError("\n\nBad irow value ({0}) when "
                                     "creating a Record.".format(irow))
         else:
            self._irow = irow
   irow = property( _getIrow, _setIrow, None, "The row number within the music catalogue" )

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
         inst = self._instrument
         if inst == FIXED_INSTRUMENT:
            inst = DEFAULT_INSTRUMENT
         return inst
   def _setInstrument(self,instrument):
         instrument = midiInstrument( instrument )
         if instrument == None or instrument == DEFAULT_INSTRUMENT:
            self._instrument = DEFAULT_INSTRUMENT
         elif instrument == FIXED_INSTRUMENT:
            self._instrument = FIXED_INSTRUMENT
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

   def _getVolume(self):
         return self._volume
   def _setVolume(self,volume):
         if isinstance(volume,str):
            self._volume = int( volume )
         else:
            self._volume = volume
   def _delVolume(self):
         self._volume = 0
   volume = property( _getVolume, _setVolume, _delVolume,
                      "The change in volume" )

   def _getTempo(self):
         return self._tempo
   def _setTempo(self,tempo):
         if isinstance(tempo,str):
            self._tempo = int( tempo )
         else:
            self._tempo = tempo
   def _delTempo(self):
         self._tempo = 0
   tempo = property( _getTempo, _setTempo, _delTempo,
                      "The change in tempo" )

   def __str__(self):
      return "Path:{0}  Tran:{1} Instr:{2}  Title:{3}".format(self._getPath(),self._getTranspose(),self._getInstrument(),self._getTitle())

   def desc(self):
      return self._title


# ----------------------------------------------------------------------
class Playlist(object):
   def __init__(self):
      self._records = []

   def add( self, path, row, trans, speed, volume, prog0, title ):
      self._records.append( Record( path, row, trans, speed, volume, prog0, title ) )

   def __len__(self):
      return len(self._records)
   def __getitem__(self, key):
      return self._records[key]
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
      if self.__inext < len( self._records ):
         return self._records[ self.__inext ]
      else:
         raise StopIteration


   def __str__(self):
      result = ""
      for record in self._records:
         result = "{0}{1}\n".format(result,record)
      return result

   def desc(self):
      result = None
      for record in self._records:
         if result:
            result = "{0}; {1}\n".format(result,record.desc())
         else:
            result = record.desc()
      return result

   def getIrows(self):
      result = []
      for record in self._records:
         result.append( record.irow )
      return result

   def _getPath(self):
      return self._records[0].path
   def _setPath(self,path):
      self._records[0].path = path
   path = property(_getPath, None, None, "The path to the first music file")

   def _getIrow(self):
      return self._records[0].irow
   def _setIrow(self,path):
      self._records[0].path = irow
   irow = property( _getIrow, _setIrow, None, "The row number within the music catalogue" )

   def _getTranspose(self):
      return self._records[0].transpose
   def _setTranspose(self,transpose):
      self._records[0].transpose = transpose
   def _delTranspose(self):
      del self._records[0].transpose
   transpose = property( _getTranspose, _setTranspose, _delTranspose,
                         "The number of semitones to transpose" )

   def _getInstrument(self):
      return self._records[0].instrument
   def _setInstrument(self,instrument):
      self._records[0].instrument = instrument
   def _delInstrument(self):
         del self._records[0].instrument
   instrument = property( _getInstrument, _setInstrument, _delInstrument,
                         "The GM program number for the instrument to use")

   def _getTitle(self):
         return self._records[0].title
   def _setTitle(self,title):
         self._records[0].title = title

   title = property(_getTitle, None, None, "The music title")

   def _getVolume(self):
      return self._records[0].volume
   def _setVolume(self,volume):
      self._records[0].volume = volume
   def _delVolume(self):
      del self._records[0].volume
   volume = property( _getVolume, _setVolume, _delVolume,
                      "The change in volume" )

   def _getTempo(self):
      return self._records[0].tempo
   def _setTempo(self,tempo):
      self._records[0].tempo = tempo
   def _delTempo(self):
      del self._records[0].tempo
   tempo = property( _getTempo, _setTempo, _delTempo,
                      "The change in tempo" )



# ----------------------------------------------------------------------
class RandomPlaylist(Playlist):
   def __init__(self, tags, cat ):
      Playlist.__init__(self)
      if not tags:
         tags = "g"
      self.__tags = tags
      self.__cat = cat
      self.played = []
      self.all = []
      random.seed( None )
      self.findAll()

      record = self.choose()
      if self.choose:
         self._records.append( self.choose() )

   def desc(self):
      return self._getTitle()
   def _getTitle(self):
      if self.__tags == "any":
         return "Random music"
      else:
         return "Random music with tags '{0}'".format(self.__tags)

   def _setTitle(self,title):
      pass

   def __len__(self):
      return NRAND;
   def __getitem__(self, key):
      return self.choose()
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
      if self.__inext < NRAND:
         return self.choose()
      else:
         raise StopIteration

   def choose( self ):
      found = False
      while not found:
         mylen = len( self.all )
         if mylen > 0:
            irow = self.all[ random.randint( 0, mylen-1 ) ]
         else:
            mylen = len( self.__cat['PATH'] )
            irow = random.randint( 0, mylen-1 )

         if irow not in self.played or mylen <= len( self.played ):
            found = True
      if len( self.played ) == 5:
         self.played.pop(0)
      self.played.append( irow )

      return self.__cat.getRecord(irow)

   def findAll( self ):
      self.all = []
      icol = self.__cat.colindices["TAGS"]
      self.all = self.__cat.search( [self.__tags], [icol], sort=False )
      if len( self.all ) == 0:
         for irow in range( catlen ):
            self.all.append(irow)


# ----------------------------------------------------------------------
class Player(object):

   def __init__(self):
      self._serverPopen = None
      self._controllerPopen = None
      self.listener = None
      self.fspipe = None
      self.mastervol = 0.5
      self.relvol = None
      self._start()

   def __del__(self):
      self._stop()

   def _stop(self):
      print( "Killing player processes" )
      self._killServerProcess();
      self._killControllerProcess();
      if self.fspipe != None:
         os.close(self.fspipe)

   def _start(self):
      self._startServerProcess()
      self._startControllerProcess()

   def _startServerProcess(self):
      self._serverPopen = subprocess.Popen(["./server"])
      time.sleep(2)
      self.fspipe = os.open(FSFIFO,os.O_WRONLY)

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
      waitForProcess( "aplaymidi" )

   def _sendCommand( self, command ):
      os.system( "./sendcommand {0}".format(command))

   def _playRecord( self, record ):
      self.setFSGain( record.volume )
      self._sendCommand( "{0} '{1}' {2} {3} {4}".format( PLAY_CMD,
                         record.path, record.transpose,
                         record.instrument, record.tempo))

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

#  Queue a Record, optionally aborting any currently playing music first
#  so that the new music starts immediately ("end" can be FADE, STOP or
#  None - in which case the music is just added to the end of the queue).
   def play( self, record, end=FADE ):
      if isinstance( record, Record ):
         self._end( end )
         self._playRecord( record )
      else:
         raise  ChurchPlayerError("\n\nPlayer.play(): Supplied object is "
                                  "not a Record" )

#  Move onto the next queued item.
   def next( self, end=FADE ):
      self._end( end )

#  Stop the current item and empty the player queue.
   def stop( self, end=FADE ):
      self._sendCommand( EMPTY_CMD )
      self._end( end )

#  Send real-time instrument change for channel 0.
   def sendProg0( self, prog0 ):
      if prog0 != FIXED_INSTRUMENT:
         self._sendCommand( "{0} {1}".format( PROG0_CMD, prog0 ) )

#  Send real-time transposition change.
   def sendTrans( self, trans ):
      self._sendCommand( "{0} {1}".format( TRANS_CMD, trans ) )

#  Send real-time tempo change.
   def sendTempo( self, tempo ):
      self._sendCommand( "{0} {1}".format( SPEED_CMD, tempo ) )

#  Send any real-time change.
   def sendRT(self,colname,value):
      if colname == "TRANS":
         self._sendCommand( "{0} {1}".format( TRANS_CMD, value ) )
      elif colname == "PROG0":
         self._sendCommand( "{0} {1}".format( PROG0_CMD, value ) )
      elif colname == "SPEED":
         self._sendCommand( "{0} {1}".format( SPEED_CMD, value ) )
      elif colname == "VOLUME":
         self.setFSGain( value )
      else:
         raise ChurchPlayerError("\n\nPlayer.sendRT does not yet "
                                 "support column '{0}'.".format(colname) )


#  Send a command to the fluidsynth process.
   def sendFS( self, cmd ):
      if self.fspipe == None:
         self.fspipe = os.open(FSFIFO,os.O_WRONLY)
      os.write(self.fspipe, cmd )

#  Modify the FluidSynth gain using a relative "volume" in the range -10
#  to +10. This relative volume is relative to the current master volume.
   def setFSGain( self, volume ):
      self.relvol = volume
      self.sendFS( "gain {0}\n".format(self.mastervol*pow( 10.0, 0.01*volume )) )

#  Get/Set the master volume (in range 0 -> 1.0).
   def setMasterVolume( self, mastervolume ):
      if self.mastervol != mastervolume:
         self.mastervol = mastervolume
         print( "Setting master vol to {0}".format(mastervolume ) )
         if self.relvol != None:
            self.setFSGain( self.relvol )

   def getMasterVolume( self ):
      return self.mastervol

