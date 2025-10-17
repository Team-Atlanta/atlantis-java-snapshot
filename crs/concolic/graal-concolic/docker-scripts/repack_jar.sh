#!/bin/bash

FILE_NAME=$(basename $1)

cd $1 && zip -r $1/../$FILE_NAME.repacked .