#!/usr/bin/env bash
# Management script for stashbot kubernetes processes

set -e

DEPLOYMENT=realtime-watchlist.worker
POD_NAME=realtime-watchlist.worker

TOOL_DIR=$(cd $(dirname $0)/.. && pwd -P)
VENV=${TOOL_DIR}/venv-bastion
if [[ -f ${VENV}/bin/activate ]]; then
    # Enable virtualenv
    source ${VENV}/bin/activate
fi

KUBECTL=/usr/bin/kubectl

_get_pod() {
    $KUBECTL get pods \
        --output=jsonpath={.items..metadata.name} \
        --selector=name=${POD_NAME}
}

case "$1" in
    start)
        echo "Starting realtime-watchlist k8s deployment(s)..."
        $KUBECTL create --validate=true -f ${TOOL_DIR}/etc/worker.yaml
        ;;
    stop)
        echo "Stopping realtime-watchlist k8s deployment(s)..."
        $KUBECTL delete deployment ${DEPLOYMENT}
        # FIXME: wait for the pods to stop
        ;;
    restart)
        echo "Restarting realtime-watchlist pod..."
        exec $KUBECTL delete pod $(_get_pod)
        ;;
    status)
        echo "Active pods:"
        exec $KUBECTL get pods -l name=${POD_NAME}
        ;;
    tail)
        exec $KUBECTL logs -f $(_get_pod)
        ;;
    attach)
        echo "Attaching to pod..."
        exec $KUBECTL exec -i -t $(_get_pod) -- /bin/bash
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|tail|attach}"
        exit 1
        ;;
esac

exit 0
# vim:ft=sh:sw=4:ts=4:sts=4:et:
