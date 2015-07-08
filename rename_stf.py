#!/usr/bin/python
import glob
import re
import os

with open("Stf-contents-list-numerical.csv") as f:
   lines = f.readlines()

tunes = {}
tags = {}
for line in lines:
   fields = line.split("@")
   try:
      number = int(fields[0])
      tunes[number] = fields[1]

      if "Kendrick" in fields[3] or \
         "Redman" in fields[3] or \
         "Hughes" in fields[3] or \
         "John L. Bell" in fields[3] or \
         "Utterbach" in fields[3] or \
         "Tomlin" in fields[3] or \
         "Townend" in fields[3] or \
         "Andy Park" in fields[3] or \
         "Doerksen" in fields[3] or \
         "Brenton Brown" in fields[3]:
         tags[number] = "M"

      elif "Wesley" in fields[3] or \
           "Pratt Green" in fields[3] or \
           "Isaac Watts" in fields[3] or \
           "John Newton" in fields[3] or \
           "Brian Wren" in fields[3]:
         tags[number] = "H"

   except:
      pass

with open("HAP-cross-reference.csv") as f:
   lines = f.readlines()

HAP = {}
for line in lines:
   fields = line.split("@")
   try:
      istf = int(fields[1])
      ihap = int(fields[2])
      HAP[istf] = ihap
   except:
      pass

rexp = re.compile( "^music/stf/(\d+)([a-z]*) +([^\(]+)([^\)]*)?(.*)\.MID$" )

oldnames = {}
records = []
haprecords = []
numbers = []
maxnumber = 0

for file in glob.glob("music/stf/*.MID"):
   match = rexp.search(file)
   if match:
      number = int( match.group(1).strip() )
      alt = match.group(2).strip()
      title = match.group(3).strip()
      ftitle = title.replace(" ","_")
      ftitle = re.sub(r'\W', '', ftitle)
      tune = match.group(4).replace("(","").strip()
      ftune = tune.replace(" ","_")
      ftune = re.sub(r'\W', '', ftune)
      extra = match.group(5).strip()

      if tune != "" and extra == "":
         print("!!! {0} has missing ) after tune".format(file))
         break

      if extra.replace(")","").strip() != "":
         print("!!! {0} has unexpected text after tune".format(file))
         break

      if tune == "":
         if number in tunes:
            tune = tunes[number]

   else:
      print("!!! {0} did not match the regexp".format(file))
      break

   if ftune != "":
      newname = "{0}_{1}_{2}.mid".format( number, ftitle, ftune )
   elif alt == "":
      newname = "{0}_{1}.mid".format( number, ftitle )
   else:
      print("!!! {0} did not include a tune".format(file))
      break

   if newname in oldnames:
      print("!!! Duplicate new file name {0}".format(newname))
      break
   else:
      oldnames[newname] = file

   if number > maxnumber:
      maxnumber = number

   if number in tags:
      tag = tags[number]
   else:
      if "thee" in title.lower() or \
         "thou" in title.lower() or \
         "thine" in title.lower() or \
         "thy" in title.lower():
         tag = "H"
      else:
         tag = ""

   if number >= 165 and number <= 189:
      tag += "A"
   elif number >= 190 and number <= 222:
      tag += "C"
   elif number >= 234 and number <= 241:
      tag += "L"
   elif number >= 292 and number <= 316:
      tag += "E"

   records.append("{0}@stf/{1}@{4}@STF@{2}@{3}@KEYBD@STF@@0@0@0@-1\n".format(title,newname,number,tune,tag))
   numbers.append(number)

   if number in HAP:
      haprecords.append("{0}@stf/{1}@@HAP@{2}@{3}@KEYBD@STF@@0@0@0@-1\n".format(title,newname,HAP[number],tune))

for newname in oldnames:
   os.rename( oldnames[newname], "music/stf/{0}".format(newname) )

fd = open( "cpmusic.txt", "a" )

nnum = len( numbers)
for number in range(1,maxnumber+1):
   for j in range(nnum):
      if numbers[j] == number:
         fd.write(records[j])

for record in haprecords:
   fd.write(record)

fd.close()
print( "New catalogue data appended to 'cpmusic.txt'" )
