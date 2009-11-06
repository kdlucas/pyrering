#!/usr/bin/python
#
# Copyright 2008 Google Inc. All Rights Reserved.

"""SETUP.py will gather some information about your hardware and OS.

SETUP should capture some important hardware and sofware details. The intent is
to feed some details to include in a report file. Sometimes test cases will
fail because of specific hardware characteristics or driver issues.

Classes in this module: Machine
"""

__author__ = 'kdlucas@google.com (Kelly Lucas)'
__version__ = '0.3 Alpha Release'

import optparse
import platform
import subprocess
import sys


class Machine(object):
  """A class to represent a machine we want to inventory.

  Machine class will rely upon lshw, a program that should be on all Goobuntu
  boxes. lshw compiles a list of details about a machine, by in turn calling a
  number of programs to extract info, including information in the bios.
  Therefore, if the bios is incorrect, lshw will also be incorrect in what it
  reports. I made an conscious effort to not rely on what the OS detects, in
  order to give us some info on what the bios says we have compared to what the
  OS may report.

  Machine class will make heavy use of dictionaries, as I thought this was an
  easy way to store and retrieve details, as we could readily locate them based
  on a key.
  """

  def __init__(self):
    """Initialize a few variables and dictionaries we will use.

    Attributes:
      system, processor, bios, memory, video, nic, storage:
        dicts of string identifiers used with commands stored in the 'command'
        key of that dictionary.
        The 'command' key identifies the shell command to extract data.
      components: a list that holds the dictionary name of each subsystem we
        want to inventory.
      summary: dictionary to hold the values we want to track. The keys of
        this dictionary match the keys of all of the component dicts.
      desc: dictionary to describe each inventory component. The keys should
        match each key of the summary dictionary.
      basic_list: a list that contains summary/desc keys to print basic
        components.
    """

    self.system = {'command': 'sudo lshw -C system',
                   'form': 'description:',
                   'model': 'product:',
                   'serial': 'serial:',
                   'sysconfig': 'capabilities:',
                   'vendor': 'vendor:',
                  }

    self.processor = {'command': 'sudo lshw -C cpu',
                      'cpu_bits': 'width:',
                      'cpu_capability': 'capabilities:',
                      'cpu_capacity': 'capacity:',
                      'cpu_model': 'product:',
                      'cpu_speed': 'size:',
                      'cpu_vendor': 'vendor:',
                     }

    self.bios = {'command': 'sudo dmidecode -t bios',
                 'bios_date': 'Release Date:',
                 'bios_vendor': 'Vendor:',
                 'bios_version': 'Version',
                }

    self.memory = {'command': 'lshw -C memory',
                   'mem_size': 'size:',
                  }

    self.video = {'command': 'lshw -C video',
                  'video_memory': 'size:',
                  'video_model': 'product:',
                  'video_vendor': 'vendor:',
                 }

    self.nic = {'command': 'sudo lshw -C network',
                'nic_config': 'configuration:',
                'nic_mac': 'serial:',
                'nic_model': 'product:',
                'nic_speed': 'capacity:',
                'nic_vendor': 'vendor:',
                'nic_width': 'width:',
               }

    self.storage = {'command': 'lshw -C storage',
                    'dsk_config': 'configuration:',
                    'dsk_model': 'product:',
                    'dsk_speed': 'clock:',
                    'dsk_type': 'description:',
                    'dsk_vendor': 'vendor:',
                    'dsk_width': 'width:',
                   }

    # The list items should correspond to the name of each dictionary
    # that contains the elements we want to inventory. List items must be
    # already defined in this class.
    # TODO(kdlucas): populate list from an optional config file.
    self.components = [self.bios,
                       self.memory,
                       self.processor,
                       self.nic,
                       self.storage,
                       self.system,
                       self.video,
                      ]

    self.summary = {'arch': None,
                    'bios_date': None,
                    'bios_vendor': None,
                    'bios_version': None,
                    'cpu_bits': None,
                    'cpu_capability': None,
                    'cpu_capacity': None,
                    'cpu_model': None,
                    'cpu_qty': 0,
                    'cpu_speed': None,
                    'cpu_vendor': None,
                    'dsk_config': None,
                    'dsk_model': None,
                    'dsk_speed': None,
                    'dsk_type': None,
                    'dsk_vendor': None,
                    'dsk_width': None,
                    'form': None,
                    'google_rel': None,
                    'google_track': None,
                    'kernel': None,
                    'mem_size': None,
                    'model': None,
                    'nic_config': None,
                    'nic_mac': None,
                    'nic_model': None,
                    'nic_speed': None,
                    'nic_vendor': None,
                    'nic_width': None,
                    'node': None,
                    'os_distrib': None,
                    'os_rev': None,
                    'serial': None,
                    'sysconfig': None,
                    'vendor': None,
                    'video_memory': None,
                    'video_model': None,
                    'video_vendor': None,
                   }

    self.desc = {'arch': 'System Architecture:',
                 'bios_date': 'Bios Date:',
                 'bios_vendor': 'Bios Vendor:',
                 'bios_version': 'Bios Version:',
                 'cpu_bits': 'Processor Data Width:',
                 'cpu_capability': 'Processor Capabilities:',
                 'cpu_capacity': 'Processor Maximum Speed:',
                 'cpu_model': 'Processor Model:',
                 'cpu_qty': 'Number of Processors:',
                 'cpu_speed': 'Processor Speed:',
                 'cpu_vendor': 'Processor Vendor:',
                 'dsk_config': 'Disk Controller Options:',
                 'dsk_model': 'Disk Controller Model:',
                 'dsk_speed': 'Disk Controller clock rate:',
                 'dsk_type': 'Disk Interface:',
                 'dsk_vendor': 'Disk Controller Vendor:',
                 'dsk_width': 'Disk Controller width:',
                 'form': 'Form Factor:',
                 'google_rel': 'Google Release:',
                 'google_track': 'Developer Track:',
                 'kernel': 'Kernel Version:',
                 'mem_size': 'System Memory:',
                 'model': 'Machine Model:',
                 'nic_config': 'Network Card Configuration:',
                 'nic_mac': 'Network Card MAC Address:',
                 'nic_model': 'Network Card Model:',
                 'nic_speed': 'Network Card Speed:',
                 'nic_vendor': 'Network Card Vendor:',
                 'nic_width': 'Network Card Data Width:',
                 'node': 'Host Name:',
                 'os_distrib': 'Linux Distribution:',
                 'os_rev': 'Distribution Revision:',
                 'serial': 'System Serial:',
                 'sysconfig': 'System Configuration:',
                 'vendor': 'System Vendor:',
                 'video_model': 'Graphics Adapter Model:',
                 'video_vendor': 'Graphics Adapter Vendor:',
                 'video_memory': 'Graphics Adapter Memory:',
                }

    # Maintain the order of this list for reporting purposes.
    self.basic_list = ['os_distrib',
                       'google_rel',
                       'os_rev',
                       'google_track',
                       'model',
                       'kernel',
                       'arch',
                       'cpu_model',
                       'cpu_qty',
                       'mem_size',
                       'bios_date',
                       'bios_vendor',
                       'dsk_model',
                       'node',
                      ]
    # This self test will report errors with return codes. However, don't stop
    # running if there are errors, as we want to gather what information we
    # can, and any follow on modules should be called and run. If modules or
    # tests depend on a successful test, capture the return code of
    # _TestDictKeys().
    self._TestDictKeys()

  def _TestDictKeys(self):
    """A simple test to check that dictionary keys match.

    Args:
      None.

    Returns:
      retval: an integer that could be used if that's more convenient than
      using output from the error messages.

    This will gather all the dictionary keys of the pertinent dictionaries, and
    ensure they keys are identical. Component identification, descriptions, and
    the search strings rely on matching keys to track the data.

    By definition, the components list contains all of our component dicts.
    The set of all keys in the component dicts should be a subset of the
    summary dictionary keys. The summary and desc keys should be identical.
    I'm using sets because sets has some nice features that identify subsets
    and the differences in 2 sets.

    retval can be caught if necessary. retval will equal the total number of
    dict key errors.
    """

    retval = 0
    kcomp = set()
    for item in self.components:
      k = item.keys()
      k = set(k)
      k.remove('command')  # This is a special key that we know needs removed.
      # Ensure there are no duplicates within the component dictionaries. If we
      # don't do this check, duplicates will be silently ignored.
      dups = kcomp.intersection(k)
      if dups:
        print "Error: key duplicates found in component dictionaries!"
        print "Check %s for duplicates." % (k)
        retval += 1
      kcomp.update(k)
    ksummary = set(self.summary.keys())
    kdesc = set(self.desc.keys())
    kbasic = set(self.basic_list)

    diff = ksummary.difference(kdesc)
    if diff:
      print "Error: dictionary keys don't match."
      print "Check keys: %s" % (diff)
      retval += 1
    for k in [kcomp, kbasic]:
      subset = k.issubset(ksummary)
      if not subset:
        print "Error: dictionary key error in the basic list."
        print "Keys in %s not in summary dictionary." % k
        retval += 1

    return retval

  def ReadLSBRel(self):
    """Read /etc/lsb-release, and parse contents into dictionary.

    This will parse all the key/value pairs in lsb-release and use the
    left-hand column as a key to values in the right hand column.

    Args:
      None.

    Returns:
      None.
    """

    lsbdict = {}  # to hold our key value pairs
    lsbfname = '/etc/lsb-release'

    try:
      lsbfh = open(lsbfname)
    except IOError, err:
      print 'Error opening %s\n%s' % (lsbfname, err)
      raise

    lsblist = lsbfh.readlines()
    lsbfh.close()

    for line in lsblist:
      if line:
        line = line.strip()
        key, value = line.split('=')
        value = value.strip('"')
        lsbdict[key] = value
    self.summary['google_rel'] = lsbdict['GOOGLE_RELEASE']
    self.summary['google_track'] = lsbdict['GOOGLE_TRACK']
    self.summary['os_distrib'] = lsbdict['GOOGLE_ID']
    self.summary['os_rev'] = lsbdict['GOOGLE_CODENAME']

  def RunInventory(self):
    """Run through all the dictionaries to get an inventory.

    This will call GetInventory() which will process the actual command and
    parse the output. RunInventory() is a simple way to cycle through a list of
    components. Each component is a dictionary, and the 'command' key maps to
    the actual os level command that provides the inventory data. The other
    key's provide strings that we use to match the relevant data we care about.
    All of these keys are identical to keys in the desc and summary
    dictionaries, which hold the descriptions and data respectively.

    Args:
      None.

    Returns:
      None.
    """

    for item in self.components:
      self.GetInventory(item)

    system_os = platform.uname()
    self.summary['node'] = system_os[1]
    self.summary['kernel'] = system_os[2]
    self.summary['arch'] = system_os[4]

  def GetInventory(self, component):
    """Collect machine data in place in summary dictionary.

    This function will attempt to execute the values from the commands
    dictionary. Using text markers from component dicts, it will place the
    resulting text in the summary dictionary. This function manipulates the
    output to eliminate output we don't care about.

    Args:
      component: the name of the dictionary we're passing in.

    Returns:
      None.
    """

    # A general marker for a cpu flag.
    cpu_marker = '*-cpu'
    cpu_count = 0

    cmd = component['command']
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    output = p.stdout.read()
    # TODO(kdlucas): use something like status = p.wait() to determine logic
    # flow if needs dictate that the outcome of this subprocess need to be
    # verified, or a use case shows where this would be useful.

    # The following for loop takes all of the output from the command, and
    # breaks it into one line. There is specific logic for the cpu_marker to
    # keep track of the qty of cpus. The delimiter character is used because
    # there are various sections of output that have identical keys. This code
    # depends on using the first instance of these keys to get the correct
    # values. To do this, I've used a counter to count the number of times we
    # see a delimiter character sequence. As long as that counter doesn't
    # exceed 1, we'll add the value to the summary dictionary. There are
    # identical key fields in the output, like 'size', 'vendor', 'capacity',
    # etc. In all cases we only care about the 1st occurrence of these strings.
    # Therefore, to prevent getting invalid data a counter ensures only data
    # from the first occurrence of matching string is stored.
    for line in output.splitlines():
      if cpu_marker in line:
        cpu_count += 1
      for item, key in component.iteritems():
        if item != 'command' and key in line:
          if not self.summary[item]:
            fields = line.split(component[item])
            self.summary[item] = fields[1].lstrip()
    if cpu_count > 0:                      # Prevents qty from getting reset.
      self.summary['cpu_qty'] = cpu_count  # If component is not processor.

  def PrintInventory(self, detail):
    """Print out inventory results.

    This method prints the contents of the summary dictionary.
    The amount of data depends on the value passed from detail.

    Args:
      detail: a string to determine the level of detail to output, and
      possibly a future determination of format.

    Returns:
      None.
    """

    if detail == 'basic':
      for item in self.basic_list:
        print "%25s  %-20s" % (self.desc[item], self.summary[item])
    elif detail == "detailed":
      for key in self.desc:
        print "%27s  %-20s" % (self.desc[key], self.summary[key])

  def SaveInventory(self, filename):
    """Save the inventory results to a file.

    This method will save all of the key value pairs to a file. This can be
    used for future reads to prevent another inventory of a system.

    Args:
      filename: the name of a file to save the inventory to.

    Returns:
      None.
    """

    fout = open(filename, 'w')

    try:
      for key in self.desc:
        try:
          fout.write("%27s  %-20s\n" % (self.desc[key], self.summary[key]))
        except IOError, e:
          print e
          raise
    finally:
      fout.close()


def GetArgs():
  """Get user supplied args.

  This function uses optparse to collect the command line arguments. Both
  defaults of the detail level and the filename to save data to can be
  overridden by passing in values to --detail and --save.
  Args:
    None.
  Returns:
    A dictionary of options provided.
  """
  # Set hostname to use in a default filename.
  nodename = platform.node()
  outfile = nodename + '.platform'

  parser = optparse.OptionParser(version=__version__)
  parser.add_option('--detail', '-d', help="machine detail", type="choice",
                    dest="detail", choices=["basic", "detailed"])
  parser.add_option('--save', '-s', help="save output")
  parser.set_defaults(detail="basic", save=outfile)
  options, unused_arguments = parser.parse_args()
  return vars(options)


def main(argv):
  opts = GetArgs()
  sut = Machine()
  sut.ReadLSBRel()
  sut.RunInventory()
  sut.PrintInventory(opts['detail'])
  sut.SaveInventory(opts['save'])

if __name__ == '__main__':
  main(sys.argv)
