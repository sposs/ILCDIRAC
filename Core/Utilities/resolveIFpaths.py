'''
Created on Jun 28, 2010

@author: sposs
'''
import os
from DIRAC import S_OK,S_ERROR
from DIRAC import gLogger
def resolveIFpaths(inputfiles):
  """ Try to find out in which sub-directory are each file. In the future, should be useless if PoolXMLCatalog can be used. 
  """
  listoffiles = []
  string = "Will look for:"
  for file in inputfiles:
    listoffiles.append(os.path.basename(file))
    string += "%s\n"%file
  gLogger.info(string)
  
  listofpaths = []
  listofdirs = []
  for dir in os.listdir(os.getcwd()):
    if os.path.isdir(dir):
      listofdirs.append(dir)
  filefound = False
  for f in listoffiles:
    filefound = False
    if os.path.exists(f):
      listofpaths.append(os.getcwd()+os.sep+f)
      filefound=True
    else:
      for dir in listofdirs:
        if os.path.exists(os.getcwd()+os.sep+dir+os.sep+f):
          listofpaths.append(os.getcwd()+os.sep+dir+os.sep+f)
          listofdirs.remove(dir)
          filefound = True
          break
  if not filefound:
    return S_ERROR("resolveIFPath: Input file not found locally")
  return S_OK(listofpaths)