# $HeadURL: svn+ssh://sposs@svn.cern.ch/reps/dirac/ILCDIRAC/trunk/ILCDIRAC/__init__.py $
# $Id: __init__.py 52610 2012-05-16 12:24:49Z sposs $

from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)

# Define Version

majorVersion = 10
minorVersion = 0
patchLevel = 9
preVersion = 0
    
version      = "v%sr%s" % ( majorVersion, minorVersion )
buildVersion = "v%dr%d" % ( majorVersion, minorVersion )
if patchLevel:
  version = "%sp%s" % ( version, patchLevel )
  buildVersion = "%s build %s" % ( buildVersion, patchLevel )
if preVersion:
  version = "%s-pre%s" % ( version, preVersion )
  buildVersion = "%s pre %s" % ( buildVersion, preVersion )

