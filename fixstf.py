#!/usr/bin/env python

import sys


class Voice(object):
   __id = 0;

   def __init__(self, note_on ):
      self._setNoteOn( note_on )
      self._setSilent( 0 )
      self._setDead( False )
      self._id = Voice.__id
      Voice.__id += 1

   def _getNoteOn(self):
      return self._note_on
   def _setNoteOn(self,note_on):
      if isinstance(note_on,Record):
         if note_on.isNoteOn:
            self._note_on = note_on
         else:
            raise TypeError('Event is not a note_on event')
      else:
         raise TypeError('Object is not a MIDI event')
   noteOn = property( _getNoteOn, _setNoteOn, None,
                       "Previous note_on for a Voice" )


   def _getDead(self):
      return self._dead
   def _setDead(self,dead):
      if isinstance(dead,bool):
         self._dead = dead
      else:
         raise TypeError('Value is not a boolean')
   dead = property( _getDead, _setDead, None, "Voice has ended" )


   def _getSilent(self):
      return self._silent
   def _setSilent(self,silent):
      if isinstance(silent,int):
         self._silent = silent
      else:
         raise TypeError('Value is not an int')
   silent = property( _getSilent, _setSilent, None,
                       "The tick at which the voice was silenced" )

   def _getId(self):
      return self._id
   id = property( _getId, None, None, "A unique integer id for each Voice")



class Record(object):
   def __init__(self, line ):
      if isinstance(line,str):
         rec = [x.strip() for x in line.split(',')]
         self._setTrack( rec[0] )
         self._setTime( rec[1] )
         self._setType( rec[2] )
         self._setData( rec[3:] )
         self._setVoice( None )

      elif isinstance(line,Record):
         self._setTrack( line.track )
         self._setTime( line.time )
         self._setType( line.type )
         self._setData( line.data )
         self._setVoice( None )
      else:
         raise TypeError('Line is not a string or a Record')



   def _getTrack(self):
      return self._track
   def _setTrack(self,track):
      self._track = int( track )

   track = property( _getTrack, _setTrack, None, "The track number" )

   def _getVoice(self):
      return self._voice
   def _setVoice(self,voice):
      if voice:
         if isinstance(voice,Voice):
            self._voice = voice
         else:
            raise TypeError('Value is not a Voice')
      else:
         self._voice = None

   voice = property( _getVoice, _setVoice, None, "The event voice" )

   def _getTime(self):
      return self._time
   def _setTime(self,time):
      self._time = int( time )
   time = property( _getTime, _setTime, None, "The event time" )

   def _getType(self):
      return self._type
   def _setType(self,type):
      self._type = type.strip()

   type = property( _getType, _setType, None, "The event type" )

   def _getData(self):
      return self._data
   def _setData(self,data):
      self._data = data

   data = property( _getData, _setData, None, "The event data values" )

   def _getFormattedData(self):
      data = self._getData()
      if data:
         data = ', '.join(map(str,data))
      return data

   def __str__(self):
      data = self._getFormattedData()
      if data:
         return "{0}, {1}, {2}, {3}".format(self._getTrack(),self._getTime(),
                self._getType(),data)
      else:
         return "{0}, {1}, {2}".format(self._getTrack(),self._getTime(),
                self._getType() )

   def _isNoteOn(self):
       result = False
       if self.isType("note_on_c"):
           if int( self._data[2] ) > 0:
             result = True
       return result
   isNoteOn = property( _isNoteOn, None, None, "Is this a note on event?" )

   def _isNoteOff(self):
       result = False
       if self.isType("note_on_c"):
          if int( self._data[2] ) == 0:
             result = True
       elif self.isType("note_off_c"):
          result = True
       return result
   isNoteOff = property( _isNoteOff, None, None, "Is this a note off event?" )

   def isType(self,rtype):
      return self.type.lower() == rtype.lower()

   def _getPitch(self):
       if self.isType("note_on_c") or self.isType("note_on_c"):
          return int( self._data[1] )
       else:
          raise TypeError('Event is not a note_on or a note_off')
   def _setPitch(self,pitch):
       if self.isType("note_on_c") or self.isType("note_on_c"):
          self._data[1] = str( time )
       else:
          raise TypeError('Event is not a note_on or a note_off')
   pitch = property( _getPitch, _setPitch, None, "The note event pitch" )




class Midifile(list):
   def __init__(self, file ):
      super(Midifile, self).__init__()
      if isinstance( file, str ):
         self._tpb = 0
         mspb = 0
         with open( file ) as f:
            for line in f:
               rec = Record( line )
               self.append( rec )
               if rec.isType( "header" ):
                  self._tpb = int( rec.data[2] )
               elif rec.isType( "tempo" ):
                  mspb = int( rec.data[0] )

         if self._tpb == 0:
            raise TypeError('No ticks per beat value found in {0}'.format(file))

         elif mspb == 0:
            raise TypeError('No tempo value found in {0}'.format(file))

         self._tps = 1.0E6*float(self._tpb)/float(mspb)

      elif isinstance( file, Midifile ):
         self._tpb = file._tpb
         self._tps = file._tps

      else:
         raise TypeError("file is not a string or a Midifile")


   def _getTpb(self):
      return self._tpb
   tpb = property( _getTpb, None, None, "The number of ticks per beat" )

   def _getTps(self):
      return self._tps
   tps = property( _getTps, None, None, "The number of ticks per second" )

   def write(self,file):
      fd = open( file, "w" )
      for rec in self:
         fd.write( "{0}\n".format(rec) )
      fd.close()

   def appendNoteOff(self, note, time ):
      irec = len(self) - 1
      while( self[irec].time > time and irec > 0 ):
         irec -= 1
      newrec = Record( note )
      newrec.time = time
      newrec.type = "Note_off_c"
      self.insert( irec + 1, newrec )

   def append(self,record):
      if isinstance(record,Record):
         super(Midifile, self).append(record)
      else:
         raise TypeError("record is not a Record")



def organise( oldmf ):
   mf = Midifile( oldmf )
   voices = []

   slimit = mf.tpb*4
   gap = int( mf.tps*0.05 )

   print("Gap is {0}/{1} = {2} beats".format(gap,oldmf.tpb,float(gap)/oldmf.tpb))

   for event in oldmf:

      if event.isNoteOn:
         pitch = event.pitch

         minint = 15
         minvoice = None

         for voice in voices:
            if voice.silent > event.time - slimit:
               thisint = abs( pitch - voice.noteOn.pitch )
               if thisint < minint:
                  minvoice = voice
                  minint = thisint

            elif voice.silent > 0:
               voice.dead = True

         for voice in voices:
            if voice.dead:
               mf.appendNoteOff( voice.noteOn, event.time - slimit )
               voices.remove( voice )

         if minvoice:

            stopTime = event.time - gap
            if stopTime < minvoice.silent:
               stopTime = minvoice.silent

            mf.appendNoteOff( minvoice.noteOn, stopTime )
            minvoice.noteOn = event
            minvoice.silent = 0
         else:
            voice = Voice( event )
            voices.append( voice )

         mf.append( event )

      elif event.isNoteOff:
         pitch = event.pitch
         for voice in voices:
            if voice.silent == 0:
               if voice.noteOn.pitch == pitch:
                  voice.silent = event.time
                  break

      else:
         mf.append( event )

   return mf



oldmf = Midifile( sys.argv[1] )
mf = organise( oldmf )
mf.write("New.csv")




