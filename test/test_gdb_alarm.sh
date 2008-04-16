#! /bin/sh
# Copyright 2006, Google Inc.  All rights reserved.
# Author: mec@google.com (Michael Chastain)
# Author: kdlucas@google.com (KD Lucas)
#
# PR_START Override defaults, pass to harness
# TIMEOUT="600"
## xx = integer in seconds, default is 600
# ROOT_ACCESS="FALSE"
## default is FALSE
# EXPECTED_RETURN="0"
## yy = non zero value, default is 0
# CONCURRENT="TRUE"
## default is TRUE
# NFS="TRUE"
## default is FALSE
# PR_END
#
#
# Test gdb.

# Gdb to test, program to test.
# This gdb will always exist.
GDB_TO_TEST=/home/build/static/projects/tools/gdb
PROGRAM_TO_TEST="$GDB_TO_TEST"

# Minimal script
SCRIPT_TO_TEST="/tmp/test-gdb-$$.script"
cat > "$SCRIPT_TO_TEST" << 'EOF'
break main
run
quit
yes
EOF

# Actually run gdb.
# Messages about "tcsetpgrp failed in terminal_inferior" are harmless.
/usr/local/scripts/alarm 60 "$GDB_TO_TEST" --command="$SCRIPT_TO_TEST"\
  "$PROGRAM_TO_TEST" 
status=$?

# Clean up and exit.
rm -f "$SCRIPT_TO_TEST"
if [ $status != 0 ]
then
  echo "FAIL: $0"
else
  echo "PASS: $0"
fi

exit $status
