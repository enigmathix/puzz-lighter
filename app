#!/bin/bash
CMD=$1
shift

# FIXME set these values
export GOOGLE_CLOUD_PROJECT=sample
HUNT=sample
PORT=8042

export APPLICATION_ID=dev~$GOOGLE_CLOUD_PROJECT
export DATASTORE_DATASET=$GOOGLE_CLOUD_PROJECT
export DATASTORE_EMULATOR_HOST=::1:8432
export DATASTORE_EMULATOR_HOST_PATH=::1:8432/datastore
export DATASTORE_HOST=http://::1:8432
export DATASTORE_GOOGLE_CLOUD_PROJECT_ID=$GOOGLE_CLOUD_PROJECT
export DEFERRED_USE_CROSS_COMPATIBLE_PICKLE_PROTOCOL=True

case $CMD in
run)
	python3 $HOME/google-cloud-sdk/bin/dev_appserver.py app.yaml -A $GOOGLE_CLOUD_PROJECT --skip_sdk_update_check=yes --port=$PORT --admin_port=8113 --enable_console --host=0.0.0.0 --log_level=debug --enable_host_checking False --datastore_path ./datastore.db --watcher_ignore_re $PWD/datastore.db --python_virtualenv_path ../pyenv --env_var HUNT=$HUNT $*
	;;

deploy)
	gcloud --configuration=enigmatix app deploy app.yaml --project $GOOGLE_CLOUD_PROJECT --version live $*
	;;

index)
	gcloud --configuration=enigmatix app deploy index.yaml --project $GOOGLE_CLOUD_PROJECT --version live $*
	;;

*)
	echo "$0 [run|deploy|index]"
	echo
	echo "Examples:"
	echo "$0 run"
	echo "$0 deploy"
	;;
esac
