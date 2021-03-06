'''
Checks the validity of the provided XML files at job submission

Created on Feb 24, 2011

@author: S. Poss
@since: Feb 24, 2011
'''
from DIRAC                                                import S_OK, S_ERROR
from xml.etree.ElementTree                                import ElementTree

def CheckXMLValidity(xmlfile):
  """ Check that the xml parsing of the specified xml will not fail when running on the GRID
  @param xmlfile: path to xml file
  """
  tree = ElementTree()
  try:
    tree.parse(xmlfile)
  except Exception, x:
    return S_ERROR("Found problem in file %s: %s %s"%(xmlfile, Exception, x))
  
  return S_OK()