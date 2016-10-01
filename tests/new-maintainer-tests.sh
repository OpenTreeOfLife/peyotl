#!/bin/bash
#!/bin/sh
for d in peyotl extras scripts tutorials tests
do 
    if ! test -d "$d"
    then
        echo "$0 must be run from the PEYOTL_ROOT dir (the parent of the tests dir)."
        exit 1
    fi
done
num_fails=0
num_checks=1
if ! bash tests/test-logger.sh
then
    num_fails=$(expr 1 + ${num_fails})
fi





num_passes=$(expr ${num_checks} - ${num_fails})
echo "Passed $num_passes out of $num_checks checks in $0"
test ${num_checks} = ${num_passes}

