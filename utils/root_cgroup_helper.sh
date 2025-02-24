#!/bin/bash
ACTION=$1
CGROUP_PATH=$2
VALUE=$3
USERNAME=$(logname)

case $ACTION in
    "create")
        sudo sh -c "mkdir '$CGROUP_PATH'"
        ;;
    "chown")
        OWNER=$(stat -c %U $CGROUP_PATH)
        if [ "$OWNER" == "$USERNAME" ]; then
            exit 0
        elif [ "$OWNER" != "root" ]; then
            echo "Owned by $OWNER, not root or $USERNAME"
            exit 1
        else
            sudo sh -c "chown $USERNAME:$USERNAME '$CGROUP_PATH'"
        fi
        ;;
    "write")
        if [[ $CGROUP_PATH == *"cgroup.procs"* ]]; then
            sudo sh -c "echo $VALUE > $CGROUP_PATH"
        else
            echo $VALUE > $CGROUP_PATH
        fi
        ;;
    *)
        exit 1
        ;;
esac