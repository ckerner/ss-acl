#!/usr/bin/env python
"""
We needed to be able to modify SpectrumScale ACLs easily and in parallel, and
the interface provided by IBM, namely mmgetacl and mmputacl are less that
friendly when it comes to parsing millions of files and maintaining ACLs on
them.

The source for this is publicly available at:
          github: https://github.com/ckerner/ssacl.git

Chad Kerner, Senior Storage Engineer
Storage Enabling Technologies
National Center for Supercomputing Applications
ckerner@illinois.edu     chad.kerner@gmail.com

This was born out of a need to programmatically interface with IBM Spectrum
Scale or the software formerly knows as GPFS.

There is NO support, use it at your own risk.  Although I have not coded
anything too awfully dramatic in here.

If you find a bug, fix it.  Then send me the diff and I will merge it into
the code.

You may want to pull often because this is being updated quite frequently as
our needs arise in our clusters.

"""

from __future__ import print_function
from subprocess import Popen, PIPE
import sys
import os
import shlex
import json
from stat import *
import tempfile
import pprint

DRYRUN = 0
MMGETACL = '/usr/lpp/mmfs/bin/mmgetacl'
MMPUTACL = '/usr/lpp/mmfs/bin/mmputacl'

"""
ACL Dictionary Structure:
    acl[FQPN]   - Fully qualified pathname of the file.
    acl[TYPE]   - f for file and D for directories
    acl[OWNER]  - Owner of the file
    acl[GROUP]  - Group of the file
    acl[USERP]  - User permissions
    acl[GROUPP] - Group permissions
    acl[OTHERP] - Other permissions
    acl[MASK]   - File mask
    acl[USERS]
          [USER]
             [PERMS]
             [EFFECTIVE]
    acl[GROUPS]
          [GROUP]
             [PERMS]
             [EFFECTIVE]
"""


def execute_command( commandString=None, Debug=False ):
    """
    This routing will execute a command and return its output.

    Arguments:
        commandString - The command you wish to execute.

    Return Values:
        1 - The return code of the command
        2 - The information sent to STDOUT from the command
        3 - The information sent to STDERR from the command

    Note: It is up to the caller to determine success/failure.

    """
    if not commandString:
       return( 99999999, None, None )

    shellCommand = shlex.split( commandString )
    subp = Popen( shellCommand, stdout=PIPE, stderr=PIPE )
    ( outdata, errdata ) = subp.communicate()

    if Debug:
       print("DEBUG: Command: {}".format(commandString))
       print("DEBUG: Return Code: {}".format(subp.returncode))
       print("DEBUG: STDOUT: {}".format(outdata))
       print("DEBUG: STDERR: {}".format(errdata))

    return  ( subp.returncode, outdata, errdata )


class mmacls:
      """
      This class will handle the manipulation of the SpectrumScale ACLs
      on the files that need them.
      """
      def __init__( self, fname=None ):
          self.debug = False
          self.dryrun = False
          self.verbose = False
          self.is_file = True
          self.fname = fname

          try:
             self.filename = os.path.abspath( fname )
             self.stats = os.stat( self.filename )
          except:
             self.filename = None
             return None

          if S_ISDIR( self.stats[ST_MODE] ):
             self.dirname = self.filename
             self.is_file = False
          else:
             self.dirname = os.path.dirname( self.filename )

          self.get_acl()


      def dump_mmacl( self ):
          print( "File: " + self.filename )
          print( "Directory: " + self.dirname )
          print( "ACL: " )
          pprint.pprint( self.acls )


      def dump_raw_acl( self ):
          cmd = MMGETACL + ' "' + self.filename + '"'
          #cmd = [ MMGETACL, self.filename ]

          ( rc, stdout, stderr ) = execute_command( cmd )
          if rc == 0:
             for line in output.splitlines():
                 print( line )
             print("")
          else:
             print("Command: %s ERROR: %s" % ( cmd, rc ) )
             print("STDOUT: %s\nSTDERR: %s" % ( stdout, stderr ) )


      def dump_raw_default_acl( self ):
          cmd = MMGETACL + ' -d ' + self.filename
          #cmd = [ MMGETACL, self.filename ]
          ( rc, stdout, stderr ) = execute_command( cmd )
          if rc == 0:
             for line in stdout.splitlines():
                 print( line )
             print("")
          else:
             print("Command: %s ERROR: %s" % ( cmd, rc ) )
             print("STDOUT: %s\nSTDERR: %s" % ( stdout, stderr ) )


      def clear_acls( self ):
          if 'MASK' in self.acls:
             del self.acls['MASK']
          if 'USERS' in self.acls:
             del self.acls['USERS']
          if 'GROUPS' in self.acls:
             del self.acls['GROUPS']


      def clear_default_acls( self ):
          if 'MASK' in self.default_acls:
             del self.default_acls['MASK']
          if 'USERS' in self.default_acls:
             del self.default_acls['USERS']
          if 'GROUPS' in self.default_acls:
             del self.default_acls['GROUPS']


      def get_acl( self ):
          """
          Fetch the file ACLs and return them in a dict.

          :param fnam: The name of the file or directory to get the ACLs on.
          :return: Returns a dict with the ACL information.
          """

          mydict = {}
          mydict['GROUPS'] = {}
          mydict['USERS'] = {}
          mydict['FQPN'] = self.filename
          mydict['DIRNAME'] = self.dirname

          cmd = MMGETACL + ' "' + self.filename + '"'
          #cmd = [ MMGETACL, self.filename ]
          ( rc, output, stderr ) = execute_command( cmd )
          if rc != 0:
             print("Command: %s ERROR: %s" % ( cmd, rc ) )
             print("STDOUT: %s\nSTDERR: %s" % ( stdout, stderr ) )
             return None

          for line in output.splitlines():
              if '#owner:' in line:
                 mydict['OWNER'] = line.split(':')[1]
              elif '#group:' in line:
                 mydict['GROUP'] = line.split(':')[1]
              elif line.startswith('user:'):
                 if line.split(':')[1] == '':
                    mydict['USERP'] = line.split(':')[2]
                 else:
                    user_name=line.split(':')[1]
                    mydict['USERS'][user_name] = {}
                    mydict['USERS'][user_name]['PERMS']=line.split(':')[2][0:4]
                    if 'effective' in line:
                       mydict['USERS'][user_name]['EFFECTIVE']=line.split(':')[3][1:5]
                    else:
                       mydict['USERS'][user_name]['EFFECTIVE']='????'
              elif line.startswith('group:'):
                 if line.split(':')[1] == '':
                    mydict['GROUPP'] = line.split(':')[2]
                 else:
                    group_name=line.split(':')[1]
                    mydict['GROUPS'][group_name] = {}
                    mydict['GROUPS'][group_name]['PERMS']=line.split(':')[2][0:4]
                    if 'effective' in line:
                       mydict['GROUPS'][group_name]['EFFECTIVE']=line.split(':')[3][1:5]
                    else:
                       mydict['GROUPS'][group_name]['EFFECTIVE']='????'
              elif 'other::' in line:
                 mydict['OTHERP'] = line.split(':')[2]
              elif 'mask::' in line:
                 mydict['MASK'] = line.split(':')[2]
          self.acls = mydict


      def get_default_acl( self ):
          """
          Fetch the file ACLs and return them in a dict.

          :param fnam: The name of the file or directory to get the ACLs on.
          :return: Returns a dict with the ACL information.
          """

          mydict = {}
          mydict['GROUPS'] = {}
          mydict['USERS'] = {}
          mydict['FQPN'] = self.dirname

          cmd = MMGETACL + ' -d "' + self.filename + '"'
          #cmd = [ MMGETACL, self.filename ]
          ( rc, output, stderr ) = execute_command( cmd )
          if rc != 0:
             print("Command: %s ERROR: %s" % ( cmd, rc ) )
             print("STDOUT: %s\nSTDERR: %s" % ( stdout, stderr ) )
             return None


          for line in output.splitlines():
              if '#owner:' in line:
                 mydict['OWNER'] = line.split(':')[1]
              elif '#group:' in line:
                 mydict['GROUP'] = line.split(':')[1]
              elif line.startswith('user:'):
                 if line.split(':')[1] == '':
                    mydict['USERP'] = line.split(':')[2]
                 else:
                    user_name=line.split(':')[1]
                    mydict['USERS'][user_name] = {}
                    mydict['USERS'][user_name]['PERMS']=line.split(':')[2][0:4]
                    if 'effective' in line:
                       mydict['USERS'][user_name]['EFFECTIVE']=line.split(':')[3][1:5]
                    else:
                       mydict['USERS'][user_name]['EFFECTIVE']='????'
              elif line.startswith('group:'):
                 if line.split(':')[1] == '':
                    mydict['GROUPP'] = line.split(':')[2]
                 else:
                    group_name=line.split(':')[1]
                    mydict['GROUPS'][group_name] = {}
                    mydict['GROUPS'][group_name]['PERMS']=line.split(':')[2][0:4]
                    if 'effective' in line:
                       mydict['GROUPS'][group_name]['EFFECTIVE']=line.split(':')[3][1:5]
                    else:
                       mydict['GROUPS'][group_name]['EFFECTIVE']='????'
              elif 'other::' in line:
                 mydict['OTHERP'] = line.split(':')[2]
              elif 'mask::' in line:
                 mydict['MASK'] = line.split(':')[2]
          self.default_acls = mydict


      def add_user_acl( self, username, mask ):
          """
          Add the specified user into the object ACL.

          :param: user name / uid
          :param: ACL mask
          """
          self.acls['USERS'][username] = {}
          self.acls['USERS'][username]['PERMS'] = mask


      def add_group_acl( self, groupname, mask ):
          """
          Add the specified group into the object ACL.

          :param: group name / gid
          :param: ACL mask
          """
          self.acls['GROUPS'][groupname] = {}
          self.acls['GROUPS'][groupname]['PERMS'] = mask


      def add_default_user_acl( self, username, mask ):
          """
          Add the specified user into the object default ACL.

          :param: user name / uid
          :param: ACL mask
          """
          self.default_acls['USERS'][username] = {}
          self.default_acls['USERS'][username]['PERMS'] = mask


      def add_default_group_acl( self, groupname, mask ):
          """
          Add the specified group into the object default ACL.

          :param: group name / gid
          :param: ACL mask
          """
          self.default_acls['GROUPS'][groupname] = {}
          self.default_acls['GROUPS'][groupname]['PERMS'] = mask


      def update_user_perms( self, mask ):
          """
          Update the POSIX user permissions.

          :param: ACL mask
          """
          self.acls['USERP'] = mask


      def update_group_perms( self, mask ):
          """
          Update the POSIX group permissions.

          :param: ACL mask
          """
          self.acls['GROUPP'] = mask


      def update_other_perms( self, mask ):
          """
          Update the POSIX other permissions.

          :param: ACL mask
          """
          self.acls['OTHERP'] = mask


      def update_default_user_perms( self, mask ):
          self.default_acls['USERP'] = mask


      def update_default_group_perms( self, mask ):
          self.default_acls['GROUPP'] = mask


      def update_default_other_perms( self, mask ):
          self.default_acls['OTHERP'] = mask


      def del_user_acl( self, username ):
          """
          Remove a user ACL from the current ACL list.

          :param: A username / uid for the user to remove.
          """
          if username in self.acls['USERS'].keys():
             del self.default_acls['USERS'][username]
          else:
             print("%s does not have a user ACL on %s" % ( username, self.filename ))


      def del_group_acl( self, groupname ):
          """
          Remove a group ACL from the current ACL list.

          :param: A group / gid for the user to remove.
          """
          if groupname in self.acls['GROUPS'].keys():
             del self.acls['GROUPS'][groupname]
          else:
             print("%s does not have a group ACL on %s" % ( groupname, self.filename ))


      def del_default_user_acl( self, username ):
          """
          Remove a user ACL from the current default ACL list.

          :param: A username / uid for the user to remove.
          """
          if username in self.default_acls['USERS'].keys():
             del self.default_acls['USERS'][username]
          else:
             print("%s does not have a user ACL on %s" % ( username, self.filename ))


      def del_default_group_acl( self, groupname ):
          """
          Remove a group ACL from the current default ACL list.

          :param: A group / gid for the user to remove.
          """
          if groupname in self.default_acls['GROUPS'].keys():
             del self.default_acls['GROUPS'][groupname]
          else:
             print("%s does not have a group ACL on %s" % ( groupname, self.filename ))


      def get_group_acl( self, group=None ):
          """
          This function will return the group ACL of the specified file.

          :param: A string containing the filename.
          :param: A string containing the name of the group to check for.
          :return: A 4 character string:
                     ???? - If the file does not exist.
                     ---- - If the group does not have an ACL on the file.
                          - The actual 4 character permission mask(Ex: rw--)
          """

          if self.acls == None:
             return '????'
          else:
             if group in self.acls['GROUPS'].keys():
                return self.acls['GROUPS'][group]['PERMS']
             else:
                return '----'


      def set_default_acl( self, aclfile=None ):
          """
          This function will set the default acl of the currently specified file directory to the
          contents of the file specified in the function call.

          :param: A string containing the fully qualified path to the ACL file.
          :return: Nothing
          """
          cmd = MMPUTACL +  '-d -i ' + aclfile + ' "' + self.filename + '"'
          #cmd = [ MMPUTACL, '-d', '-i', aclfile, "'"+self.filename+"'" ]
          if self.dryrun:
             print( "".join(cmd) )
          else:
             if self.verbose:
                print( "".join(cmd) )
             ( rc, stdout, stderr ) = execute_command( cmd )
             if rc != 0:
                print("Command: %s ERROR: %s" % ( cmd, rc ) )
                print("STDOUT: %s\nSTDERR: %s" % ( stdout, stderr ) )


      def set_acl( self, aclfile=None ):
          """
          This function will set the acl of the currently specified file or directory to the
          contents of the file specified in the function call.

          :param: A string containing the fully qualified path to the ACL file.
          :return: Nothing
          """
          cmd = MMPUTACL + ' -i ' + aclfile + ' "' + self.filename + '"'
          #cmd = [ MMPUTACL, '-i', aclfile, "'"+self.filename+"'" ]
          if self.dryrun:
             print( "".join(cmd) )
          else:
             if self.verbose:
                print( "".join(cmd) )

             ( rc, stdout, stderr ) = execute_command( cmd )
             if rc != 0:
                print("Command: %s ERROR: %s" % ( cmd, rc ) )
                print("STDOUT: %s\nSTDERR: %s" % ( stdout, stderr ) )


      def debug_on( self ):
          """
          Turn debug on.
          """
          self.debug = True


      def debug_off( self ):
          """
          Turn debug off.
          """
          self.debug = False


      def toggle_debug( self ):
          """
          Toggle debug mode.
          """
          if self.debug == True:
             self.debug = False
          else:
             self.debug = True


      def dryrun_on( self ):
          """
          Turn dryrun on.
          """
          self.dryrun = True


      def dryrun_off( self ):
          """
          Turn dryrun off.
          """
          self.dryrun = False


      def toggle_dryrun( self ):
          """
          Toggle dryrun mode.
          """
          if self.dryrun == False:
             self.dryrun = True
          else:
             self.dryrun = False


      def verbose_on( self ):
          """
          Turn verbose on.
          """
          self.verbose = True


      def verbose_off( self ):
          """
          Turn verbose off.
          """
          self.verbose = False


      def toggle_verbose( self ):
          """
          Toggle verbose mode.
          """
          if self.verbose == False:
             self.verbose = True
          else:
             self.verbose = False


def run_cmd2( cmdstr=None ):
    if not cmdstr:
       return None
    #print("CMDSTR: %s" % ( cmdstr ) )
    subp = Popen(cmdstr, stdout=PIPE, stderr=PIPE )
    (outdata, errdata) = subp.communicate()
    #    if subp.returncode == 22:
    #       return( 'File is not in gpfs.' )
    if subp.returncode != 0:
       dump_string = " ".join(cmdstr)
       msg = "Error\n Command: {0}\n Message: {1}".format(dump_string,errdata)
       raise UserWarning( msg )
       exit( subp.returncode )
    return( outdata )


def run_cmd( cmdstr=None ):
    """
    Wrapper around subprocess module calls.

    :param: A string containing the command to run.
    :return: The text output of the command.
    """
    if not cmdstr:
       return None
    cmd = shlex.split(cmdstr)
    subp = Popen(cmd, stdout=PIPE, stderr=PIPE)
    (outdata, errdata) = subp.communicate()
#    if subp.returncode == 22:
#       return( 'File is not in gpfs.' )
    if subp.returncode != 0:
       msg = "Error\n Command: {0}\n Message: {1}".format(cmdstr,errdata)
       raise UserWarning( msg )
       exit( subp.returncode )
    return( outdata )


def chown_file( fnam=None, owner=-1, group=-1 ):
    """
    To leave the owner or group the same, set it to -1
    """
    try:
       os.chown( fnam, owner, group )
    except:
       print("Error: %s %s %s" % ( fnam, owner, group ) )


def write_acl_file( aclfile=None, myacls=None, def_acl=None ):
    """
    Write an ACL file. This does not have to be part of a class. You may
    want to write one for other thigns.
    """
    if not aclfile:
       print("Error: write_acl_file: 3")
       return None

    if not myacls:
       print("Error: write_acl_file: 1")
       return None

    if not def_acl:
       print("Error: write_acl_file: 2")
       print( def_acl )
       return None

    fd = open( aclfile, "w" )
    if 'USERP' in myacls:
       fd.write( "user::" + myacls['USERP'] + "\n" )
    else:
       fd.write( "user::" + def_acl['USERP'] + "\n" )

    if 'GROUPP' in myacls:
       fd.write( "group::" + myacls['GROUPP'] + "\n" )
    else:
       fd.write( "group::" + def_acl['GROUPP'] + "\n" )

    if 'OTHERP' in myacls:
       fd.write( "other::" + myacls['OTHERP'] + "\n" )
    else:
       fd.write( "other::" + def_acl['OTHERP'] + "\n" )

    if 'MASK' in myacls.keys():
       fd.write( "mask::" + myacls['MASK'] + "\n" )
    else:
       # If we have USER and GROUP ACLs, we need a default mask
       if 'USERS' in myacls.keys():
          if 'GROUPS' in myacls.keys():
             fd.write( "mask::rwxc" + "\n" )

    if 'USERS' in myacls.keys():
       for user in myacls['USERS'].keys():
           fd.write( "user:" + user + ":" + myacls['USERS'][user]['PERMS'] + "\n" )

    if 'GROUPS' in myacls.keys():
       for group in myacls['GROUPS'].keys():
           fd.write( "group:" + group + ":" + myacls['GROUPS'][group]['PERMS'] + "\n" )
    fd.close()

def get_temp_filename():
    """
    Use the tempfile module to generate unique temporary work filenames.
    (For the future when this gets to be parallelized.)
    """
    #if options.debug:
    #   print("Trace: %s" % ( sys._getframe().f_code.co_name))

    tf = tempfile.NamedTemporaryFile()
    return tf.name


def gac_update_default_acl( filename=None, aclGroup=None, aclPerms=None, dryrun=False, verbose=False ):
    """
    This function will update the default ACL on a directory to the contents of the specified ACL file.
    """
    aclFile = get_temp_filename()

    cmd = MMGETACL + ' -d -o ' + aclFile + ' "' + filename + '"'
    #cmd = [ MMGETACL, '-d', '-o', aclFile, filename ]
    if dryrun:
       print( "".join(cmd) )
    else:
       if verbose:
          print( "".join(cmd) )
       ( rc, stdout, stderr ) = execute_command( cmd )
       if rc != 0:
          print("Command: %s ERROR: %s" % ( cmd, rc ) )
          print("STDOUT: %s\nSTDERR: %s" % ( stdout, stderr ) )
          return None


    found = False
    foundUser = False
    foundGroup = False
    foundOther = False
    foundMask = False
    with open( aclFile ) as f:
       inputLine = f.read()
       if aclGroup in inputLine:
          found = True
       if 'user::' in inputLine:
          foundUser = True
       if 'group::' in inputLine:
          foundGroup = True
       if 'other::' in inputLine:
          foundOther = True
       if 'mask::' in inputLine:
          foundMask = True

    if foundUser == False:
       fd = open( aclFile, "a" )
       fd.write( "user::rwxc\n" )
       fd.write( "group::r-x-\n" )
       fd.write( "other::----\n" )
       fd.write( "mask::r-x-\n" )
       foundMask = True
       fd.close()

    #if foundGroup == False:
    #   fd = open( aclFile, "a" )
    #   fd.close()

    #if foundOther == False:
    #   fd = open( aclFile, "a" )
    #   fd.close()

    #if foundMask == False:
    #   fd = open( aclFile, "a" )
    #   fd.close()

    if found == False:
       fd = open( aclFile, "a" )
       if foundMask == False:
          fd.write( "mask::r-x-\n" )
       fd.write( "group:" + aclGroup + ":" + aclPerms + "\n" )
       fd.close()

       cmd = MMPUTACL + ' -d -i ' + aclFile + ' "' + filename + '"'
       #cmd = [ MMPUTACL, '-d', '-i', aclFile, filename ]
       if dryrun:
          print( "".join(cmd) )
       else:
          if verbose:
             print( "".join(cmd) )
          ( rc, stdout, stderr ) = execute_command( cmd )
          if rc != 0:
             print("Command: %s ERROR: %s" % ( cmd, rc ) )
             print("STDOUT: %s\nSTDERR: %s" % ( stdout, stderr ) )
             return None


def gac_update_acl( filename=None, aclGroup=None, aclPerms=None, dryrun=False, verbose=False ):
    """
    This function will update the default ACL on a directory to the contents of the specified ACL file.
    """
    aclFile = get_temp_filename()

    cmd = MMGETACL + ' -o ' + aclFile + ' "' + filename + '"'
    #cmd = [ MMGETACL, '-o', aclFile, filename ]
    if dryrun:
       print( "".join(cmd) )
    else:
       if verbose:
          print( "".join(cmd) )
       ( rc, stdout, stderr ) = execute_command( cmd )
       if rc != 0:
          print("Command: %s ERROR: %s" % ( cmd, rc ) )
          print("STDOUT: %s\nSTDERR: %s" % ( stdout, stderr ) )
          return None

    found = False
    foundUser = False
    foundGroup = False
    foundOther = False
    foundMask = False
    with open( aclFile ) as f:
       inputLine = f.read()
       if aclGroup in inputLine:
          found = True
       if 'user::' in inputLine:
          foundUser = True
       if 'group::' in inputLine:
          foundGroup = True
       if 'other::' in inputLine:
          foundOther = True
       if 'mask::' in inputLine:
          foundMask = True
       if aclGroup in f.read():
          found = True

    if foundUser == False:
       fd = open( aclFile, "a" )
       fd.write( "user::rwxc\n" )
       fd.write( "group::r-x-\n" )
       fd.write( "other::----\n" )
       fd.write( "mask::r-x-\n" )
       foundMask = True
       fd.close()

    if found == False:
       fd = open( aclFile, "a" )
       if foundMask == False:
          fd.write( "mask::r-x-\n" )
       fd.write( "group:" + aclGroup + ":" + aclPerms + "\n" )
       fd.close()

       cmd = MMPUTACL + ' -i ' + aclFile + ' "' + filename + '"'
       #cmd = [ MMPUTACL, '-i', aclFile, filename ]
       if dryrun:
          print( "".join(cmd) )
       else:
          if verbose:
             print( "".join(cmd) )
          ( rc, stdout, stderr ) = execute_command( cmd )
          if rc != 0:
             print("Command: %s ERROR: %s" % ( cmd, rc ) )
             print("STDOUT: %s\nSTDERR: %s" % ( stdout, stderr ) )



def set_default_acl( filename=None, aclfile=None, dryrun=False, verbose=False ):
    """
    This function will set the default ACL on a directory to the contents of the specified ACL file.

    :param: A fully qualified pathname to the file or directory on which to set the ACL.
    :param: A fully qualified pathname to the ACL file to use.
    :param: Execute in dry-run mode. True or False. Default: False
    :param: Execute in verbose mode. True or False. Default: False
    """
    cmd = MMPUTACL + ' -d -i ' + aclfile + ' "' + filename + '"'
    #cmd = [ MMPUTACL, '-d', '-i', aclfile, "'"+filename+"'" ]
    #cmd = [ MMPUTACL, '-d', '-i', aclfile, filename ]
    if dryrun:
       print( "".join(cmd) )
    else:
       if verbose:
          print( "".join(cmd) )
       ( rc, stdout, stderr ) = execute_command( cmd )
       if rc != 0:
          print("Command: %s ERROR: %s" % ( cmd, rc ) )
          print("STDOUT: %s\nSTDERR: %s" % ( stdout, stderr ) )


def set_acl( filename=None, aclfile=None, dryrun=False, verbose=False ):
    """
    This function will set the ACL on a directory to the contents of the specified ACL file.

    :param: A fully qualified pathname to the file or directory on which to set the ACL.
    :param: A fully qualified pathname to the ACL file to use.
    :param: Execute in dry-run mode. True or False. Default: False
    :param: Execute in verbose mode. True or False. Default: False
    """
    #cmd = MMPUTACL + '-i ' + aclfile + ' "' + filename + '"'
    #cmd = [ MMPUTACL, '-i', aclfile, "'"+filename+"'" ]
    cmd = MMPUTACL + ' -i ' + aclfile + ' "' + filename + '"'
    #cmd = [ MMPUTACL, '-i', aclfile, filename ]
    if dryrun:
       print( "".join(cmd) )
    else:
       if verbose:
          print( "".join(cmd) )
       ( rc, stdout, stderr ) = execute_command( cmd )
       if rc != 0:
          print("Command: %s ERROR: %s" % ( cmd, rc ) )
          print("STDOUT: %s\nSTDERR: %s" % ( stdout, stderr ) )


def return_json( theacl=None ):
    """
    Given a dictionary, return the dictionary in JSON format.

    :param: A variable that contains a dictionary.
    :return: A string containing the dictionary in JSON format.
    """
    if theacl != None:
       return json.dumps( theacl )


if __name__ == '__main__':
   print("Get File ACL")
   a = mmacls( '/data/acl/a' )
   if a.filename:
      print("\nDump The Class Info:")
      a.dump_mmacl()
      print('ACL: %s' % ( return_json(a.acls) ) )
   else:
      print("File: %s does not exist." % ( a.fname ) )


