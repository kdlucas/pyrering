#!/bin/bash
#
# Copyright 2008 Google Inc. All Rights Reserved.
# Author: mwu@google.com (Mingyu Wu)

CURRENT_DIR=`pwd`
./pyrering.py --project_name pyrering --source_dir=${CURRENT_DIR} \
--report_dir=${CURRENT_DIR}/reports \
--conf_file=${CURRENT_DIR}/conf/pyrering.conf \
--nosendmail --log_file=pyrering.log pyrering_selftest.suite
