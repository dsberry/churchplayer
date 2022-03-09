#!/usr/bin/env python
import cpmodel
import re


def xrefMP(cat):
   with open("mp_index") as f:
      lines = f.readlines()

   regex = re.compile('[^a-zA-Z]')

   mp = {}
   mpt = {}
   for line in lines:
      fields = line.split("@")
      imp = int(fields[0])
      ttlmp = regex.sub('', fields[1].lower().strip())
      if ttlmp:
         mp[ttlmp] = imp
         mpt[ttlmp] = fields[1].strip()

   for irow in range(cat.nrow):
      if cat['BOOK'][irow] == "STF":
         ttl = regex.sub('', cat['TITLE'][irow].lower())

         for mpttl in mp:
            if mpttl.startswith(ttl) or ttl.startswith(mpttl):
               print( "{0}|{1}@{2}@{3}".format( mpt[mpttl], cat['TITLE'][irow], mp[mpttl], cat['NUMBER'][irow] ) )


def addMP(cat):
   with open("mp2stf.csv") as f:
      lines = f.readlines()

   mp = {}
   for line in lines:
      fields = line.split("@")
      try:
         istf = int(fields[2])
         imp = int(fields[1])
         mp[istf] = imp
      except:
         pass

   for irow in range(cat.nrow):
      if cat['BOOK'][irow] == "STF":
         istf = int( cat['NUMBER'][irow] )
         if istf in mp:
            if cat['ISALSO'][irow]:
               if "MP" not in cat['ISALSO'][irow]:
                  cat['ISALSO'][irow] += " MP:{0}".format(mp[istf])
            else:
               cat['ISALSO'][irow] = "MP:{0}".format(mp[istf])
            cat.modified = True

#  Add HAP cross references to ISALSO column
def addHAP(cat):
   with open("HAP-cross-reference.csv") as f:
      lines = f.readlines()

   hap = {}
   for line in lines:
      fields = line.split("@")
      try:
         istf = int(fields[1])
         ihap = int(fields[2])
         hap[istf] = ihap
      except:
         pass

   for irow in range(cat.nrow):
      if cat['BOOK'][irow] == "STF":
         istf = int( cat['NUMBER'][irow] )
         if istf in hap:
            if cat['ISALSO'][irow]:
               cat['ISALSO'][irow] += " HAP:{0}".format(hap[istf])
            else:
               cat['ISALSO'][irow] = "HAP:{0}".format(hap[istf])
            cat.modified = True

#  Delete all rows with a given string value for a column.
def delAll( col, value ):
   rows = []
   for irow in range(cat.nrow):
      if cat[col][irow] == value:
          rows.append(irow)

   for irow in reversed(rows):
      cat.delrow(irow)

#  Add a new column, assigning a blank value to the column in each row.
def addCol( cat, name, desc ):
   cat.colnames.append(name)
   cat.coldescs.append(desc)
   cat.colsearchable.append(False)
   cat.coluser.append(0)
   cat.ncol += 1
   cat[name] = [""] * cat.nrow
   cat.modified = True

def editCat( cat ):
   xrefMP(cat)



# Main entry
cat = cpmodel.Catalogue()
cat.verify()
if cat.warnings:
   print( cat.warnings )
else:
   editCat( cat )
   if cat.modified:
      cat.save()







