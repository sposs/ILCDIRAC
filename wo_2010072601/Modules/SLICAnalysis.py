'''
ILCDIRAC.Workflow.Modules.SLICAnalysis Called by Job Agent. 

@since:  Apr 7, 2010

@author: Stephane Poss
'''
import os,sys,re, urllib, zipfile
from DIRAC.Core.Utilities.Subprocess                      import shellCall
#from DIRAC.Core.DISET.RPCClient                           import RPCClient
from ILCDIRAC.Workflow.Modules.ModuleBase                    import ModuleBase
from ILCDIRAC.Core.Utilities.CombinedSoftwareInstallation import LocalArea,SharedArea
from ILCDIRAC.Core.Utilities.PrepareOptionFiles           import PrepareMacFile
from ILCDIRAC.Core.Utilities.ResolveDependencies          import resolveDepsTar
from ILCDIRAC.Core.Utilities.resolveIFpaths import resolveIFpaths

from DIRAC                                                import S_OK, S_ERROR, gLogger, gConfig
import DIRAC

class SLICAnalysis(ModuleBase):
  """
  Specific Module to run a SLIC job.
  """
  def __init__(self):
    ModuleBase.__init__(self)
    self.enable = True
    self.STEP_NUMBER = ''
    self.log = gLogger.getSubLogger( "SLICAnalysis" )
    self.result = S_ERROR()
    self.systemConfig = ''
    self.applicationLog = ''
    self.applicationName = 'SLIC'
    self.applicationVersion=''
    self.startFrom = 0
    self.stdhepFile = ''
    self.InputData = '' # from the (JDL WMS approach)
    
    self.detectorModel = ''
    self.inmacFile = ''
    self.outputslcio = ''
    self.debug = False
    self.jobID = None
    if os.environ.has_key('JOBID'):
      self.jobID = os.environ['JOBID']
    
  def resolveInputVariables(self):
    """ Resolve all input variables for the module here.
    @return: S_OK()
    """
    if self.workflow_commons.has_key('SystemConfig'):
        self.systemConfig = self.workflow_commons['SystemConfig']

    if self.step_commons.has_key('applicationVersion'):
        self.applicationVersion = self.step_commons['applicationVersion']
        self.applicationLog = self.step_commons['applicationLog']

    if self.step_commons.has_key('numberOfEvents'):
        self.numberOfEvents = self.step_commons['numberOfEvents']
          
    if self.step_commons.has_key('startFrom'):
      self.startFrom = self.step_commons['startFrom']

    if self.step_commons.has_key('stdhepFile'):
      self.stdhepFile = self.step_commons['stdhepFile']
    if self.workflow_commons.has_key('InputData'):
      self.InputData = self.workflow_commons['InputData']
      
    if self.step_commons.has_key("inputmacFile"):
      self.inmacFile = self.step_commons['inputmacFile']

    if self.step_commons.has_key('detectorModel'):
      self.detectorModel = self.step_commons['detectorModel'] 
      
    if self.step_commons.has_key('outputFile'):
      self.outputslcio = self.step_commons['outputFile'] 
    if self.step_commons.has_key('debug'):
      self.debug =  self.step_commons['debug']
      
    if len(self.stdhepFile)==0 and not len(self.InputData)==0:
      inputfiles = self.InputData.split(";")
      for files in inputfiles:
        if files.lower().find(".stdhep")>-1 or files.lower().find(".hepevt")>-1:
          self.stdhepFile = files
          break
          
    return S_OK('Parameters resolved')
  
  def unzip_file_into_dir(self,file, dir):
    """Used to unzip the downloaded detector model
    """
    zfobj = zipfile.ZipFile(file)
    for name in zfobj.namelist():
      if name.endswith('/'):
        os.mkdir(os.path.join(dir, name))
      else:
        outfile = open(os.path.join(dir, name), 'wb')
        outfile.write(zfobj.read(name))
        outfile.close()
  
  def execute(self):
    """
    Called by JobAgent
    
    Execute the following:
      - get the environment variables that should have been set during installation
      - download the detector model, using CS query to fetch the address
      - prepare the mac file using L{PrepareMacFile}
      - run SLIC on this mac File and catch the exit status
    @return: S_OK(), S_ERROR()
    """
    self.result =self.resolveInputVariables()
    if not self.systemConfig:
      self.result = S_ERROR( 'No ILC platform selected' )
    elif not self.applicationLog:
      self.result = S_ERROR( 'No Log file provided' )
    if not self.result['OK']:
      return self.result
    if not os.environ.has_key('SLIC_DIR'):
      self.log.error('SLIC_DIR not found, probably the software installation failed')
      return S_ERROR('SLIC_DIR not found, probably the software installation failed')
    if not os.environ.has_key('SLIC_VERSION'):
      self.log.error('SLIC_VERSION not found, probably the software installation failed')
      return S_ERROR('SLIC_VERSION not found, probably the software installation failed')
    if not os.environ.has_key('LCDD_VERSION'):
      self.log.error('LCDD_VERSION not found, probably the software installation failed')
      return S_ERROR('LCDD_VERSION not found, probably the software installation failed')
    if not os.environ.has_key('XERCES_VERSION'):
      self.log.error('XERCES_VERSION not found, probably the software installation failed')
      return S_ERROR('XERCES_VERSION not found, probably the software installation failed')


    slicDir = os.environ['SLIC_DIR']
    mySoftwareRoot = ''
    localArea = LocalArea()
    sharedArea = SharedArea()
    if os.path.exists('%s%s%s' %(localArea,os.sep,slicDir)):
      mySoftwareRoot = '%s%s%s' %(localArea,os.sep,slicDir)
    if os.path.exists('%s%s%s' %(sharedArea,os.sep,slicDir)):
      mySoftwareRoot = '%s%s%s' %(sharedArea,os.sep,slicDir)
    if not mySoftwareRoot:
      self.log.error('Directory %s was not found in either the local area %s or shared area %s' %(slicDir,localArea,sharedArea))
      return S_ERROR('Failed to discover software')

    ### Resolve dependencies
    deps = resolveDepsTar(self.systemConfig,"slic",self.applicationVersion)
    for dep in deps:
      if os.path.exists(os.path.join(mySoftwareRoot,dep.rstrip(".tgz").rstrip(".tar.gz"))):
        depfolder = dep.rstrip(".tgz").rstrip(".tar.gz")
        if os.path.exists(os.path.join(mySoftwareRoot,depfolder,"lib")):
          self.log.verbose("Found lib folder in %s"%(depfolder))
          if os.environ.has_key("LD_LIBRARY_PATH"):
            os.environ["LD_LIBRARY_PATH"] = os.path.join(mySoftwareRoot,depfolder,"lib")+":%s"%os.environ["LD_LIBRARY_PATH"]
          else:
            os.environ["LD_LIBRARY_PATH"] = os.path.join(mySoftwareRoot,depfolder,"lib")

    #retrieve detector model from web
    detector_urls = gConfig.getValue('/Operations/SLICweb/SLICDetectorModels',[''])
    if len(detector_urls[0])<1:
      self.log.error('Could not find in CS the URL for detector model')
      return S_ERROR('Could not find in CS the URL for detector model')

    if not os.path.exists(self.detectorModel+".zip"):
      for detector_url in detector_urls:
        detmodel,headers = urllib.urlretrieve("%s%s"%(detector_url,self.detectorModel+".zip"),self.detectorModel+".zip")
        try:
          self.unzip_file_into_dir(open(self.detectorModel+".zip"),os.getcwd())
          break
        except:
          os.unlink(self.detectorModel+".zip")
          continue

    if not os.path.exists(self.detectorModel+".zip"):
      self.log.error('Detector model %s was not found neither locally nor on the web, exiting'%self.detectorModel)
      return S_ERROR('Detector model %s was not found neither locally nor on the web, exiting'%self.detectorModel)
    
    #unzip detector model
    #self.unzip_file_into_dir(open(self.detectorModel+".zip"),os.getcwd())
    
    slicmac = 'slicmac.mac'
    if len(self.stdhepFile)>0:
      res = resolveIFpaths([self.stdhepFile])
      if not res['OK']:
        self.log.error("Generator file not found")
        return res
      self.stdhepFile = res['Value'][0]
    if len(self.inmacFile)>0:
      self.inmacFile = os.path.basename(self.inmacFile)
    macok = PrepareMacFile(self.inmacFile,slicmac,self.stdhepFile,self.numberOfEvents,self.startFrom,self.detectorModel,self.outputslcio,self.debug)
    if not macok:
      self.log.error('Failed to create SLIC mac file')
      return S_ERROR('Error when creating SLIC mac file')
    
    scriptName = 'SLIC_%s_Run_%s.sh' %(self.applicationVersion,self.STEP_NUMBER)
    if os.path.exists(scriptName): os.remove(scriptName)
    script = open(scriptName,'w')
    script.write('#!/bin/sh \n')
    script.write('#####################################################################\n')
    script.write('# Dynamically generated script to run a production or analysis job. #\n')
    script.write('#####################################################################\n')
    script.write('declare -x XERCES_LIB_DIR=%s/packages/xerces/%s/lib\n'%(mySoftwareRoot,os.environ['XERCES_VERSION']))
    if os.environ.has_key('LD_LIBRARY_PATH'):
      script.write('declare -x LD_LIBRARY_PATH=$XERCES_LIB_DIR:$LD_LIBRARY_PATH\n')
    else:
      script.write('declare -x LD_LIBRARY_PATH=$XERCES_LIB_DIR\n')
      
    script.write('declare -x GEANT4_DATA_ROOT=%s/packages/geant4/data\n'%mySoftwareRoot)
    script.write('declare -x G4LEVELGAMMADATA=$(ls -d $GEANT4_DATA_ROOT/PhotonEvaporation*)\n')
    script.write('declare -x G4RADIOACTIVEDATA=$(ls -d $GEANT4_DATA_ROOT/RadioactiveDecay*)\n')
    script.write('declare -x G4LEDATA=$(ls -d $GEANT4_DATA_ROOT/G4EMLOW*)\n')
    script.write('declare -x G4NEUTRONHPDATA=$(ls -d $GEANT4_DATA_ROOT/G4NDL*)\n')
    script.write('declare -x GDML_SCHEMA_DIR=%s/packages/lcdd/%s\n'%(mySoftwareRoot,os.environ['LCDD_VERSION']))
    script.write('declare -x PARTICLE_TBL=%s/packages/slic/%s/data/particle.tbl\n'%(mySoftwareRoot,os.environ['SLIC_VERSION']))
    script.write('echo =========\n')
    script.write('env | sort >> localEnv.log\n')
    script.write('echo =========\n')
    comm = '%s/packages/slic/%s/bin/Linux-g++/slic -P $PARTICLE_TBL -m %s\n'%(mySoftwareRoot,os.environ['SLIC_VERSION'],slicmac)
    print comm
    script.write(comm)
    script.write('declare -x appstatus=$?\n')
    script.write('exit $appstatus\n')
    script.close()
    if os.path.exists(self.applicationLog): os.remove(self.applicationLog)

    os.chmod(scriptName,0755)
    comm = 'sh -c "./%s"' %scriptName
    self.setApplicationStatus('SLIC %s step %s' %(self.applicationVersion,self.STEP_NUMBER))
    self.stdError = ''
    self.result = shellCall(0,comm,callbackFunction=self.redirectLogOutput,bufferLimit=20971520)
    #self.result = {'OK':True,'Value':(0,'Disabled Execution','')}
    resultTuple = self.result['Value']

    status = resultTuple[0]
    # stdOutput = resultTuple[1]
    # stdError = resultTuple[2]
    self.log.info( "Status after the application execution is %s" % str( status ) )

    failed = False
    if status != 0:
      self.log.error( "SLIC execution completed with errors:" )
      failed = True
    else:
      self.log.info( "SLIC execution completed successfully")

    if failed:
      self.log.error( "==================================\n StdError:\n" )
      self.log.error( self.stdError) 
      self.setApplicationStatus('SLIC Exited With Status %s' %(status))
      self.log.error('SLIC Exited With Status %s' %(status))
      return S_ERROR('SLIC Exited With Status %s' %(status))    
    self.setApplicationStatus('SLIC %s Successful' %(self.applicationVersion))
    return S_OK('SLIC %s Successful' %(self.applicationVersion))

    #############################################################################
  def redirectLogOutput(self, fd, message):
    """Catch the stdout of the application
    """
    sys.stdout.flush()
    if message:
      if re.search('BeginEvent',message): print message
    if self.applicationLog:
      log = open(self.applicationLog,'a')
      log.write(message+'\n')
      log.close()
    else:
      self.log.error("Application Log file not defined")
    if fd == 1:
      self.stdError += message
    #############################################################################
    