import time
from datetime import datetime

import pytz
from engine.services.db import (
    MAX_LEN_PREV_STATUS_HYP,
    cleanup_hypervisor_gpus,
    close_rethink_connection,
    new_rethink_connection,
)
from engine.services.db.domains import get_vgpus_mdevs
from engine.services.log import log, logs
from rethinkdb import r
from rethinkdb.errors import ReqlNonExistenceError

from .db import rethink


def get_hyps_ready_to_start():
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")

    l = list(
        rtable.filter({"enabled": True, "status": "ReadyToStart"})
        .pluck("id", "hostname", "hypervisors_pools")
        .run(r_conn)
    )
    close_rethink_connection(r_conn)

    hyps_hostnames = {d["id"]: d["hostname"] for d in l}

    return hyps_hostnames


def get_hypers_disk_operations():
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")

    hypers_ids = [
        d["id"]
        for d in list(
            rtable.filter({"enabled": True, "capabilities": {"disk_operations": True}})
            .pluck("id")
            .run(r_conn)
        )
    ]

    close_rethink_connection(r_conn)

    return hypers_ids

    pass


def update_hyp_thread_status(thread_type, hyp_id, status):
    if thread_type in ["worker", "disk_operations"] and status in [
        "Started",
        "Stopped",
        "Starting",
        "Stopping",
        "Deleting",
    ]:
        r_conn = new_rethink_connection()
        rtable = r.table("hypervisors")
        result = (
            rtable.get(hyp_id)
            .update({"thread_status": {thread_type: status}})
            .run(r_conn)
        )

        if status != "Started":
            d = (
                rtable.get(hyp_id)
                .pluck("thread_status", "status", "capabilities")
                .run(r_conn)
            )
            status_hyp = d["status"]
            if status_hyp == "Online":
                update_hyp_status(
                    hyp_id,
                    "Offline",
                    f"thread {thread_type} is not Started. Status of thread: {status}",
                )
            elif status_hyp == "Deleting":
                ko_disk_operations = False
                if d["capabilities"].get("disk_operations", False) is True:
                    if d["thread_status"].get("disk_operations", "") == "Stopped":
                        ko_disk_operations = True
                elif d["capabilities"].get("disk_operations", True) is False:
                    ko_disk_operations = True

                ko_worker = False
                if d["capabilities"].get("hypervisor", False) is True:
                    if d["thread_status"].get("worker", "") == "Stopped":
                        ko_worker = True
                elif d["capabilities"].get("hypervisor", True) is False:
                    ko_worker = True

                if ko_worker is True and ko_disk_operations is True:
                    cleanup_hypervisor_gpus(hyp_id)
                    result = rtable.get(hyp_id).delete().run(r_conn)
                    close_rethink_connection(r_conn)
                    return result

        elif status == "Started":
            d = (
                rtable.get(hyp_id)
                .pluck("thread_status", "status", "capabilities")
                .run(r_conn)
            )

            ok_disk_operations = False
            if d["capabilities"].get("disk_operations", False) is True:
                if d["thread_status"].get("disk_operations", "") == "Started":
                    ok_disk_operations = True
            elif d["capabilities"].get("disk_operations", True) is False:
                ok_disk_operations = True

            ok_worker = False
            if d["capabilities"].get("hypervisor", False) is True:
                if d["thread_status"].get("worker", "") == "Started":
                    ok_worker = True
            elif d["capabilities"].get("hypervisor", True) is False:
                ok_worker = True

            if ok_worker is True and ok_disk_operations is True:
                logs.workers.info(
                    f"All threads for hyp are started in hypervisor: {hyp_id}"
                )
        close_rethink_connection(r_conn)
        return result
    else:
        return False


def update_hyp_status(id, status, detail="", uri=""):
    # INFO TO DEVELOPER: TODO debería pillar el estado anterior del hypervisor y ponerlo en un campo,
    # o mejor aún, guardar un histórico con los tiempos de cambios en un diccionario que
    # en python puede ser internamente una cola de X elementos (número de elementos de configuración)
    # como una especie de log de cuando cambio de estado

    # INFO TO DEVELOPER: pasarlo a una función en functions
    defined_status = [
        "Offline",
        #'TryConnection',
        #'ReadyToStart',
        #'StartingThreads',
        "Error",
        "Deleting",
        "Online",
    ]
    #'Blocked',
    #'DestroyingDomains',
    #'StoppingThreads']
    if status == "Error":
        pass
    if status in defined_status:
        r_conn = new_rethink_connection()
        rtable = r.table("hypervisors")
        if len(uri) > 0:
            dict_update = {"status": status, "uri": uri}
        else:
            dict_update = {"status": status}

        d = (
            rtable.get(id)
            .pluck("status", "status_time", "prev_status", "detail")
            .run(r_conn)
        )

        if "status" in d.keys():
            if "prev_status" not in d.keys():
                dict_update["prev_status"] = []

            else:
                if type(d["prev_status"]) is list:
                    dict_update["prev_status"] = d["prev_status"]
                else:
                    dict_update["prev_status"] = []

            d_old_status = {}
            d_old_status["status"] = d["status"]
            if "detail" in d.keys():
                d_old_status["detail"] = d["detail"]
            else:
                d_old_status["detail"] = ""
            if "status_time" in d.keys():
                d_old_status["status_time"] = d["status_time"]

            dict_update["prev_status"].insert(0, d_old_status)
            dict_update["prev_status"] = dict_update["prev_status"][
                :MAX_LEN_PREV_STATUS_HYP
            ]

        now = int(time.time())
        dict_update["status_time"] = now

        # if len(detail) == 0:
        #     rtable.filter({'id':id}).\
        #           update(dict_update).\
        #           run(r_conn)
        #     # rtable.filter({'id':id}).\
        #     #       replace(r.row.without('detail')).\
        #     #       run(r_conn)
        #     close_rethink_connection(r_conn)
        #
        # else:
        dict_update["detail"] = str(detail)
        rtable.filter({"id": id}).update(dict_update).run(r_conn)
        close_rethink_connection(r_conn)

    else:
        log.error("hypervisor status {} is not defined".format(status))
        return False


def get_id_hyp_from_uri(uri):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    l = list(rtable.filter({"uri": uri}).pluck("id").run(r_conn))
    close_rethink_connection(r_conn)
    if len(l) > 0:
        return l[0]["id"]
    else:
        log.error(
            "function: {} uri {} not defined in hypervisors table".format(
                str(__name__), uri
            )
        )


def get_hyp_hostnames_online():
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    l = list(
        rtable.filter({"enabled": True, "status": "Online"})
        .pluck("id", "hostname")
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    log.debug(l)
    if len(l) > 0:
        hyps_hostnames = {d["id"]: d["hostname"] for d in l}

        return hyps_hostnames
    else:
        return dict()


# def update_hyp_enable(hyp_id, enable=True):
#     """
#     NOT USED
#     :param hyp_id:
#     :param enable:
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('hypervisors')
#     # out={}
#     # for hyp_id in argv:
#     #     o = rtable.get(hyp_id).\
#     #          update({'enabled':enable}).\
#     #          run(r_conn)
#     #     out[hyp_id] = o
#     out = rtable.get(hyp_id). \
#         update({'enabled': enable}). \
#         run(r_conn)
#     close_rethink_connection(r_conn)
#     return out


# def update_hyp_capability(hyp_id, capability, enable=True):
#     """
#     NOT USED
#     :param hyp_id:
#     :param capability:
#     :param enable:
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('hypervisors')
#
#     out = rtable.get(hyp_id). \
#         update({'capabilities': {capability: enable}}). \
#         run(r_conn)
#     close_rethink_connection(r_conn)
#     return out


def update_hyp_only_forced(hyp_id, only_forced=True):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    if only_forced != True:
        only_forced = False
    out = rtable.get(hyp_id).update({"only_forced": only_forced}).run(r_conn)
    close_rethink_connection(r_conn)
    return out


def update_uri_hyp(hyp_id, uri):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    out = rtable.get(hyp_id).update({"uri": uri}).run(r_conn)
    close_rethink_connection(r_conn)
    return out


def get_hyp_info(hyp_id):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    try:
        out = rtable.get(hyp_id).pluck("info", "min_free_mem_gb").run(r_conn)
    except ReqlNonExistenceError:
        close_rethink_connection(r_conn)
        return False

    close_rethink_connection(r_conn)
    min_free_mem_gb = out.get("min_free_mem_gb", 0)
    if min_free_mem_gb is None or min_free_mem_gb is False:
        min_free_mem_gb = 0
    if "info" in out.keys():
        if type(out["info"]) is dict and len(out["info"]) > 0:
            out["info"]["min_free_mem_gb"] = min_free_mem_gb
            return out["info"]

    return out.get("info", False)


def get_hyp_default_gpu_models(hyp_id):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    try:
        out = rtable.get(hyp_id).pluck("default_gpu_models").run(r_conn)
    except ReqlNonExistenceError:
        close_rethink_connection(r_conn)
        return {}

    close_rethink_connection(r_conn)
    return out.get("default_gpu_models", {})


def get_hyp_status(hyp_id):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    try:
        out = rtable.get(hyp_id).pluck("status").run(r_conn)
    except ReqlNonExistenceError:
        close_rethink_connection(r_conn)
        return False

    close_rethink_connection(r_conn)
    return out["status"]


def get_hyp_hostname_from_id(id):
    r_conn = new_rethink_connection()
    try:
        l = (
            r.table("hypervisors")
            .get(id)
            .pluck(
                "hostname",
                "port",
                "user",
                "nvidia_enabled",
                "force_get_hyp_info",
                "init_vgpu_profiles",
            )
            .run(r_conn)
        )
        close_rethink_connection(r_conn)
    except ReqlNonExistenceError:
        close_rethink_connection(r_conn)
        return False, False, False
    if len(l) > 0:
        if l.__contains__("user") and l.__contains__("port"):
            return (
                l["hostname"],
                l["port"],
                l["user"],
                l.get("nvidia_enabled", False),
                l.get("force_get_hyp_info", False),
                l.get("init_vgpu_profiles", False),
            )

        else:
            log.error(
                "hypervisor {} does not contain user or port in database".format(id)
            )
            return False, False, False, False, False, False
    else:
        return False, False, False, False, False, False


def get_hypers_ids_with_status(status):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")

    l = list(rtable.filter({"status": status}).pluck("id").run(r_conn))
    if len(l) > 0:
        hypers = [d["id"] for d in l]
    else:
        hypers = []
    close_rethink_connection(r_conn)
    return hypers


def get_hypers_enabled_with_capabilities_status():
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")

    hypers = list(
        rtable.filter({"enabled": True})
        .pluck("capabilities", "status", "id", "thread_status")
        .run(r_conn)
    )

    close_rethink_connection(r_conn)
    return hypers


def get_hypers_not_forced_disk_operations():
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")

    hypers = list(
        rtable.filter({"enabled": True, "status": "Online", "only_forced": False})[
            "id"
        ].run(r_conn)
    )

    close_rethink_connection(r_conn)
    return hypers


def get_hyp_hostname_user_port_from_id(id):
    r_conn = new_rethink_connection()
    l = r.table("hypervisors").get(id).pluck("hostname", "user", "port").run(r_conn)
    close_rethink_connection(r_conn)

    if len(l) > 0:
        if l.__contains__("user") and l.__contains__("port"):
            return l
        else:
            log.error(
                "hypervisor {} does not contain user or port in database".format(id)
            )
            return False
    else:
        return False


def update_all_hyps_status(reset_status="Offline", reset_thread_status="Stopped"):
    r_conn = new_rethink_connection()
    d_reset_thread_status = {
        "worker": reset_thread_status,
        "disk_operations": reset_thread_status,
    }
    results = (
        r.table("hypervisors")
        .update({"status": reset_status, "thread_status": d_reset_thread_status})
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    return results


def get_hyps_with_status(list_status, not_=False, empty=False):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    if not_ == True:
        l = list(
            rtable.filter({"enabled": True})
            .filter(lambda d: r.not_(r.expr(list_status).contains(d["status"])))
            .run(r_conn)
        )
    else:
        l = list(
            rtable.filter({"enabled": True})
            .filter(lambda d: r.expr(list_status).contains(d["status"]))
            .run(r_conn)
        )

    if empty == True:
        nostatus = list(
            rtable.filter({"enabled": True})
            .filter(lambda n: ~n.has_fields("status"))
            .run(r_conn)
        )
        l = l + nostatus

    close_rethink_connection(r_conn)
    return l


def update_hypervisor_failed_connection(id, fail_connected_reason=""):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    rtable.get(id).update({"detail": str(fail_connected_reason)}).run(r_conn)
    # if len(fail_connected_reason) > 0:
    #     rtable.get(id).update({'detail':fail_connected_reason}).run(r_conn)
    # else:
    #     rtable.get(id).replace(r.row.without('fail_connected_reason')).run(r_conn)
    close_rethink_connection(r_conn)


# def initialize_db_status_hyps():
#     """
#     NOT USED
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('hypervisors')
#
#     # all hyps to offline
#     rtable.filter({'enabled': False}). \
#         update({'status': 'Offline'}). \
#         run(r_conn)
#     rtable.filter({'enabled': True}). \
#         update({'status': 'Offline'}). \
#         run(r_conn)
#     # return only enabled
#     l = list(rtable.filter({'enabled': True}). \
#              pluck(['id', 'hostname']).
#              run(r_conn))
#
#     close_rethink_connection(r_conn)
#     if len(l) > 0:
#         hyps_hostnames = {d['id']: d['hostname'] for d in l}
#
#         return hyps_hostnames
#     else:
#         return dict()


# def insert_hyp(id,
#                hostname,
#                enable=True,
#                status='Offline',
#                hypervisors_pools=['default'],
#                user='root',
#                port='22'):
#     """
#     NOT USED
#     :param id:
#     :param hostname:
#     :param enable:
#     :param status:
#     :param hypervisors_pools:
#     :param user:
#     :param port:
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('hypervisors')
#
#     rtable.insert({'id': id,
#                    'hostname': hostname,
#                    'enabled': enable,
#                    'status': status,
#                    'hypervisors_pools': pools,
#                    'user': user,
#                    'port': port,
#                    'detail': 'new hypervisor created'}). \
#         run(r_conn)
#     close_rethink_connection(r_conn)


# def add_hypers_to_pool(id_pool, *id_hypers):
#     """
#     NOT USED
#     :param id_pool:
#     :param id_hypers:
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('hypervisors')
#     return_operations = []
#     for id_hyp in id_hypers:
#         old_pool = rtable.get(id_hyp).pluck('hypervisors_pools').run(r_conn)
#         if len(old_pool) == 0:
#             pools = [id_pool]
#         else:
#             pools = old_pool['hypervisors_pools']
#         if id_pool not in pools:
#             pools.append(id_pool)
#         return_operations.append(rtable.filter({'id': id_hyp}). \
#                                  update({'hypervisors_pools': pools}). \
#                                  run(r_conn))
#
#     close_rethink_connection(r_conn)
#     return return_operations


# def del_hypers_from_pool(id_pool, *id_hypers):
#     """
#     NOT USED
#     :param id_pool:
#     :param id_hypers:
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('hypervisors')
#     return_operations = []
#     for id_hyp in id_hypers:
#         old_pool = rtable.get(id_hyp).pluck('hypervisors_pools').run(r_conn)
#         if len(old_pool) == 0:
#             pools = [id_pool]
#         else:
#             pools = old_pool['hypervisors_pools']
#             if id_pool in pools:
#                 pools.remove(id_pool)
#                 return_operations.append(rtable.filter({'id': id_hyp}). \
#                                          update({'hypervisors_pools': pools}). \
#                                          run(r_conn))
#
#     close_rethink_connection(r_conn)
#     return return_operations


def get_pool_hypers_conf(id_pool="default"):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors_pools")

    result = rtable.get(id_pool).run(r_conn)

    close_rethink_connection(r_conn)
    return result


def get_diskopts_online(
    id_pool="default",
    forced_hyp=None,
    favourite_hyp=None,
):
    r_conn = new_rethink_connection()
    disk_opts_online = list(
        r.table("hypervisors")
        .filter({"status": "Online", "capabilities": {"disk_operations": True}})
        .filter(r.row["storage_pools"].contains(id_pool))
        .pluck("id", "only_forced", "gpu_only", "stats", "mountpoints")
        .run(r_conn)
    )
    return filter_available_hypers(
        disk_opts_online,
        forced_hyp=forced_hyp,
        favourite_hyp=favourite_hyp,
        exclude_outofmem=False,
    )


def get_hypers_online(
    id_pool="default",
    forced_hyp=None,
    favourite_hyp=None,
):
    r_conn = new_rethink_connection()
    hypers_online = list(
        r.table("hypervisors")
        .filter({"status": "Online", "capabilities": {"hypervisor": True}})
        .filter(r.row["hypervisors_pools"].contains(id_pool))
        .pluck(
            "id", "only_forced", "gpu_only", "stats", "mountpoints", "min_free_mem_gb"
        )
        .run(r_conn)
    )
    return filter_available_hypers(
        hypers_online,
        forced_hyp=forced_hyp,
        favourite_hyp=favourite_hyp,
        exclude_gpu=True,
        exclude_outofmem=True,
    )


def filter_available_hypers(
    hypers_online,
    forced_hyp=None,
    favourite_hyp=None,
    exclude_gpu=False,
    exclude_outofmem=True,
):
    # exclude hypers with low memory (HYPER_FREE_MEM)
    if exclude_outofmem:
        hypers_online = filter_outofmem_hypers(hypers_online)

    # exclude hypers with gpu
    # NOTE: we are not excluding gpu when we are looking for disk operations,
    #       we are only excluding gpu when we are looking for hypervisors
    if exclude_gpu:
        hypers_online = [h for h in hypers_online if not h.get("gpu_only", None)]

    # check if forced_hyp is online
    if forced_hyp:
        forced_hyp_found = [h for h in hypers_online if h["id"] in forced_hyp]
        if len(forced_hyp_found):
            return forced_hyp_found
        return []

    # exclude now hypers only_forced
    hypers_online = [h for h in hypers_online if not h.get("only_forced")]

    if favourite_hyp:
        favourite_hyp_found = [h for h in hypers_online if h["id"] in favourite_hyp]
        if len(favourite_hyp_found):
            return favourite_hyp_found

    return hypers_online


def filter_outofmem_hypers(hypers_online):
    hypers_with_ram = []
    for hyper in hypers_online:
        if (
            int(hyper.get("stats", {}).get("mem_stats", {}).get("available", 0))
            >= int(hyper.get("min_free_mem_gb", 0)) * 1048576
        ):
            hypers_with_ram.append(hyper)
        else:
            logs.workers.error(
                "Hyper %s removed from start desktops pool because low available ram. %s"
                % (
                    hyper["id"],
                    hyper,
                )
            )
    if not len(hypers_with_ram):
        logs.workers.error(
            "No hypers left with ram available to start desktops from %s active."
            % len(hypers_online)
        )
        return []
    logs.workers.debug("--------------------------------------")
    logs.workers.debug(
        "hypers_with_ram: %s"
        % int(hyper.get("stats", {}).get("mem_stats", {}).get("available", 0))
    )
    logs.workers.debug("--------------------------------------")
    return hypers_with_ram


def get_hypers_gpu_online(
    id_pool="default",
    forced_hyp=None,
    favourite_hyp=None,
    gpu_brand_model_profile=None,
    forced_gpus_hypervisors=None,
    exclude_outofmem=True,
):
    r_conn = new_rethink_connection()
    hypers_online = list(
        r.table("hypervisors")
        .filter({"status": "Online"})
        .filter(r.row["hypervisors_pools"].contains(id_pool))
        .pluck(
            "id",
            "only_forced",
            "gpu_only",
            "info",
            "stats",
            "mountpoints",
            "min_free_mem_gb",
        )
        .run(r_conn)
    )

    # exclude hypers with low memory (HYPER_FREE_MEM)
    if exclude_outofmem:
        hypers_online = filter_outofmem_hypers(hypers_online)

    # Check profile format: "NVIDIA-A10-2Q"
    try:
        gpu_brand, gpu_model, gpu_profile = gpu_brand_model_profile.split("-")
    except:
        logs.workers.error(
            f"Error parsing gpu_profile: {gpu_brand_model_profile}. Not in format BRAND-MODEL-PROFILE"
        )
        return []

    hypers_online_with_gpu = [
        h
        for h in hypers_online
        if len(
            [i for i in h.get("info", {}).get("nvidia", {}).values() if i == gpu_model]
        )
        > 0
    ]

    if forced_hyp:
        forced_hyp_found = [h for h in hypers_online_with_gpu if h["id"] in forced_hyp]
        if len(forced_hyp_found) > 0:
            hypers_online_with_gpu = forced_hyp_found
        else:
            return []

    if favourite_hyp:
        favourite_hyp_found = [
            h for h in hypers_online_with_gpu if h["id"] in favourite_hyp
        ]
        if len(favourite_hyp_found) > 0:
            hypers_online_with_gpu = favourite_hyp_found

    if forced_gpus_hypervisors:
        hypers_online_with_gpu = [
            h for h in hypers_online_with_gpu if h["id"] in forced_gpus_hypervisors
        ]
        if not len(hypers_online_with_gpu):
            return []

    hypervisors_with_available_profile = []
    # now find hypervisors with free uuids:
    for h in hypers_online_with_gpu:
        hyper_with_free_uuid = False
        for pci, model in h["info"]["nvidia"].items():
            if model == gpu_model:
                gpu_id = h["id"] + "-" + pci
                gpu_profile_active, mdevs = get_vgpus_mdevs(gpu_id, gpu_profile)

                if gpu_profile_active == gpu_profile:
                    for mdev_uuid, d in mdevs[gpu_profile].items():
                        if (
                            d["domain_reserved"] is False
                            and d["domain_started"] is False
                            and d["created"] is True
                        ):
                            hyper_with_free_uuid = True
                            break
                    if hyper_with_free_uuid:
                        break
        if hyper_with_free_uuid:
            logs.workers.info(
                f"hypervisor with available profile gpu: {h['id']}, uuid_selected: {mdev_uuid}, "
                + f"gpu_profile: {gpu_brand_model_profile}, gpu_id: {gpu_id}"
            )
            hypervisors_with_available_profile.append(
                {
                    **h,
                    **{
                        "gpu_selected": {
                            "uuid_selected": mdev_uuid,
                            "next_hyp": h["id"],
                            "next_available_uid": mdev_uuid,
                            "next_gpu_id": gpu_id,
                            "gpu_profile": gpu_brand_model_profile,
                        }
                    },
                }
            )

    if not len(hypervisors_with_available_profile):
        logs.workers.error("No free mdevs found for gpu_profile: %s" % gpu_profile)
        return []

    if forced_hyp:
        # return hypervisors_with_available_profile if it's id is in forced_hyp list
        return [h for h in hypervisors_with_available_profile if h["id"] in forced_hyp]

    if forced_gpus_hypervisors:
        # If force_gpus is set, we return the hypervisors with the
        # profiles requested. If no hypervisor is found, we return an empty
        # list.

        return [
            h["id"]
            for h in hypers_online_with_gpu
            if h["id"] in hypervisors_with_available_profile
        ]

    # exclude now hypers only_forced
    hypervisors_with_available_profile = [
        h for h in hypervisors_with_available_profile if not h.get("only_forced")
    ]

    if favourite_hyp:
        favourite_hyp_found = [
            h for h in hypervisors_with_available_profile if h["id"] in favourite_hyp
        ]
        if len(favourite_hyp_found):
            return favourite_hyp_found

    return hypervisors_with_available_profile


def get_hypers_in_pool(
    id_pool="default",
    only_online=True,
    exclude_hyp_only_forced=False,
    exclude_hyp_gpu_only=False,
):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")

    l_forced = []
    l_gpu_only = []
    d_filter = {}
    if only_online:
        d_filter["status"] = "Online"

    if exclude_hyp_only_forced is True:
        d_filter_only_forced = d_filter.copy()
        d_filter_only_forced["only_forced"] = True
        l_forced = list(
            rtable.filter(r.row["hypervisors_pools"].contains(id_pool))
            .filter(d_filter_only_forced)
            .pluck("id")
            .run(r_conn)
        )

    if exclude_hyp_gpu_only is True:
        d_filter_gpu_only = d_filter.copy()
        d_filter_gpu_only["gpu_only"] = True
        l_gpu_only = list(
            rtable.filter(r.row["hypervisors_pools"].contains(id_pool))
            .filter(d_filter_gpu_only)
            .pluck("id")
            .run(r_conn)
        )

    l = list(
        rtable.filter(r.row["hypervisors_pools"].contains(id_pool))
        .filter(d_filter)
        .pluck("id")
        .run(r_conn)
    )

    hyps_gpu_only = [a["id"] for a in l_gpu_only]
    hyps_only_forced = [a["id"] for a in l_forced]
    hyps_all = [a["id"] for a in l]
    hyps_to_start = [
        a["id"] for a in l if a["id"] not in (hyps_only_forced + hyps_gpu_only)
    ]

    close_rethink_connection(r_conn)
    return hyps_to_start, hyps_only_forced, hyps_all


def get_hypers_info(
    id_pool="default", pluck=None, exclude_only_forced=False, exclude_gpu_only=False
):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")
    l_only_forced = []
    l_gpu_only = []
    if exclude_only_forced is True:
        l_only_forced = list(
            rtable.filter(r.row["hypervisors_pools"].contains(id_pool))
            .filter({"status": "Online", "only_forced": True})
            .pluck("id")
            .run(r_conn)
        )

    if exclude_gpu_only is True:
        l_gpu_only = list(
            rtable.filter(r.row["hypervisors_pools"].contains(id_pool))
            .filter({"status": "Online", "gpu_only": True})
            .pluck("id")
            .run(r_conn)
        )

    l_hyp_id_exclude = [a["id"] for a in l_only_forced] + [a["id"] for a in l_gpu_only]

    if not pluck:
        l_all = list(
            rtable.filter(r.row["hypervisors_pools"].contains(id_pool))
            .filter({"status": "Online"})
            .run(r_conn)
        )
    else:
        l_all = list(
            rtable.filter(r.row["hypervisors_pools"].contains(id_pool))
            .filter({"status": "Online"})
            .pluck(pluck)
            .run(r_conn)
        )

    results = [a for a in l_all if a["id"] not in l_hyp_id_exclude]
    close_rethink_connection(r_conn)
    return results


# def delete_hyp(hyp_id):
#     """
#     NOT USED
#     :param hyp_id:
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('hypervisors')
#
#     results = rtable.get(hyp_id).delete().run(r_conn)
#     close_rethink_connection(r_conn)


# def list_all_hyps():
#     """
#     NOT USED
#     :return:
#     """
#     r_conn = new_rethink_connection()
#     rtable = r.table('hypervisors')
#
#     results = rtable.run(r_conn)
#     l = list(results)
#     close_rethink_connection(r_conn)
#     return l


def update_db_hyp_info(id, hyp_info):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")

    rtable.filter({"id": id}).update({"info": hyp_info}).run(r_conn)
    close_rethink_connection(r_conn)


def get_vgpu_model_profile_change(vgpu_id):
    r_conn = new_rethink_connection()
    rtable = r.table("vgpus")
    try:
        d = (
            rtable.get(vgpu_id)
            .pluck("model", "vgpu_profile", "changing_to_profile")
            .run(r_conn)
        )
    except ReqlNonExistenceError:
        close_rethink_connection(r_conn)
        return False
    close_rethink_connection(r_conn)
    return d


def get_vgpu_info(vgpu_id):
    r_conn = new_rethink_connection()
    rtable = r.table("vgpus")
    out = False
    try:
        out = rtable.get(vgpu_id).pluck("hyp_id", "info").run(r_conn)
    except ReqlNonExistenceError:
        close_rethink_connection(r_conn)
        return False
    close_rethink_connection(r_conn)
    return out


def get_domains_started_in_vgpu(vgpu_id):
    r_conn = new_rethink_connection()
    rtable = r.table("vgpus")

    profile = rtable.get(vgpu_id).pluck("vgpu_profile").run(r_conn)["vgpu_profile"]
    mdevs = (
        rtable.get(vgpu_id)
        .pluck({"mdevs": [profile]})
        .run(r_conn)["mdevs"]
        .get(profile, {})
    )
    l_domains = [
        i["domain_started"]
        for i in mdevs.values()
        if type(i.get("domain_started", False)) is str and len(i["domain_started"]) > 0
    ]

    close_rethink_connection(r_conn)
    return l_domains


def update_vgpu_uuids(vgpu_id, d_uuids):
    r_conn = new_rethink_connection()
    rtable = r.table("vgpus")

    rtable.filter({"id": vgpu_id}).update({"mdevs": d_uuids}).run(r_conn)
    close_rethink_connection(r_conn)


def update_vgpu_uuid_started_in_domain(hyp_id, pci_id, profile, mdev_uuid, domain_id):
    r_conn = new_rethink_connection()
    rtable = r.table("vgpus")
    vgpu_id = "-".join([hyp_id, pci_id])
    rtable.filter({"id": vgpu_id}).update(
        {"mdevs": {profile: {mdev_uuid: {"domain_started": domain_id}}}}
    ).run(r_conn)
    close_rethink_connection(r_conn)


def reset_vgpu_created_started(hyp_id, pci_id, d_mdevs_running):
    r_conn = new_rethink_connection()
    rtable = r.table("vgpus")
    vgpu_id = "-".join([hyp_id, pci_id])
    out = rtable.get(vgpu_id).run(r_conn)
    for profile, d in out["mdevs"].items():
        for uuid64, d_uid in d.items():
            d_uid["created"] = True if uuid64 in d_mdevs_running.keys() else False
            d_uid["domain_started"] = False
            d_uid["domain_reserved"] = False
    rtable.filter({"id": vgpu_id}).update({"mdevs": out["mdevs"]}).run(r_conn)
    close_rethink_connection(r_conn)


def update_vgpu_profile(vgpu_id, vgpu_profile):
    r_conn = new_rethink_connection()
    rtable = r.table("vgpus")

    rtable.filter({"id": vgpu_id}).update({"vgpu_profile": vgpu_profile}).run(r_conn)
    close_rethink_connection(r_conn)


def update_db_hyp_nvidia_info(hyp_id, d_info_nvidia):
    r_conn = new_rethink_connection()
    rtable = r.table("vgpus")
    for pci_bus, d_vgpu in d_info_nvidia.items():
        vgpu_id = "-".join([hyp_id, pci_bus])
        try:
            result = rtable.get(vgpu_id).delete().run(r_conn)
        except ReqlNonExistenceError:
            pass
        d = {}
        d["id"] = vgpu_id
        d["hyp_id"] = hyp_id
        d["force_selected_profile"] = False
        d["changing_to_profile"] = False
        # d["selected_profile"] = False
        d["nvidia_uids"] = {}
        d["info"] = d_vgpu
        d["model"] = d_vgpu["model"]
        d["brand"] = "NVIDIA"
        result = rtable.insert(d).run(r_conn)

        gpus = list(
            r.table("gpus")
            .filter(
                {
                    "brand": d["brand"],
                    "model": d["model"],
                    "physical_device": None,
                }
            )
            .pluck("id")
            .run(r_conn)
        )
        if len(gpus) == 0:
            logs.workers.error(
                "A new GPU has been added to Isard, but there are no GPUs defined to accomodate it! Manual PCI assignation required for "
                + vgpu_id
            )

        else:
            r.table("gpus").get(gpus[0]["id"]).update({"physical_device": vgpu_id}).run(
                r_conn
            )

    close_rethink_connection(r_conn)
    return True


def update_vgpu_created(vgpu_id, profile, uuid64, created=True):
    r_conn = new_rethink_connection()
    rtable = r.table("vgpus")
    result = (
        rtable.get(vgpu_id)
        .update({"mdevs": {profile: {uuid64: {"created": created}}}})
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    return result


def update_vgpu_started(vgpu_id, profile, uuid64, domain_id):
    now = int(time.time())
    r_conn = new_rethink_connection()
    rtable = r.table("vgpus")
    result = (
        rtable.get(vgpu_id)
        .update(
            {
                "mdevs": {
                    profile: {
                        uuid64: {
                            "domain_started": {"timestamp": now, "domain_id": domain_id}
                        }
                    }
                }
            }
        )
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    return result


def update_vgpu_reserved(vgpu_id, profile, uuid64, domain_id):
    now = int(time.time())
    r_conn = new_rethink_connection()
    rtable = r.table("vgpus")
    result = (
        rtable.get(vgpu_id)
        .update(
            {
                "mdevs": {
                    profile: {
                        uuid64: {
                            "domain_reserved": {
                                "timestamp": now,
                                "domain_id": domain_id,
                            }
                        }
                    }
                }
            }
        )
        .run(r_conn)
    )
    close_rethink_connection(r_conn)
    return result


def get_vgpu(vgpu_id):
    r_conn = new_rethink_connection()
    rtable = r.table("vgpus")

    try:
        out = rtable.get(vgpu_id).run(r_conn)
    except ReqlNonExistenceError:
        close_rethink_connection(r_conn)
        return False
    close_rethink_connection(r_conn)
    return out


def get_vgpu_actual_profile(vgpu_id):
    start = datetime.now(pytz.utc).strftime("%Y-%m-%dT%H:%M%z")

    r_conn = new_rethink_connection()

    try:
        gpu = list(r.table("gpus").filter({"physical_device": vgpu_id}).run(r_conn))[0]
    except:
        logs.workers.error(
            "The gpu " + vgpu_id + " has no entry in gpus table right now!"
        )
        close_rethink_connection(r_conn)
        return None

    try:
        data = list(
            r.table("resource_planner")
            .get_all(gpu["id"], index="item_id")
            .filter(
                r.row["start"]
                <= datetime.strptime(start, "%Y-%m-%dT%H:%M%z").astimezone(pytz.UTC)
            )
            .filter(
                r.row["end"]
                >= datetime.strptime(start, "%Y-%m-%dT%H:%M%z").astimezone(pytz.UTC)
            )
            .run(r_conn)
        )[0]
        logs.workers.info("==================================")
        logs.workers.info(
            "GPU "
            + vgpu_id
            + " has a planning for profile "
            + data["subitem_id"]
            + " now!",
        )
        logs.workers.info("==================================")
    except:
        data = []
        logs.workers.info("==================================")
        logs.workers.error(
            "FAIL AT GETTING GPU PLAN: GPU "
            + vgpu_id
            + " has no running plan for any profile now!",
        )
        logs.workers.info("==================================")
    close_rethink_connection(r_conn)
    if len(data):
        return data["subitem_id"].split("-")[-1]
    return None


def get_hyp(hyp_id):
    r_conn = new_rethink_connection()
    rtable = r.table("hypervisors")

    out = rtable.get(hyp_id).run(r_conn)
    close_rethink_connection(r_conn)
    return out


@rethink
def get_storage_pool_hypervisor_ids(connection, storage_pool_id):
    return [
        hypervisor["id"]
        for hypervisor in r.table("hypervisors")
        .filter(r.row["storage_pools"].contains(storage_pool_id))
        .pluck("id")
        .run(connection)
    ]


def flatten(S):
    if S == []:
        return S
    if isinstance(S[0], list):
        return flatten(S[0]) + flatten(S[1:])
    return S[:1] + flatten(S[1:])


@rethink
def get_domains_started_from_vgpus_table(connection):
    rtable = r.table("vgpus")
    l_vgpus = list(rtable.run(connection))
    wow = [
        b
        for b in [
            [
                i
                for i in [
                    [
                        {
                            "hyp_id": l["hyp_id"],
                            "model": l["model"],
                            "gpu_id": l["id"],
                            "profile": profile,
                            "mdev": a,
                            "domain_id": v["domain_started"],
                        }
                        for a, v in d.items()
                        if v["domain_started"] != False
                    ]
                    for profile, d in l["mdevs"].items()
                ]
                if len(i) > 0
            ]
            for l in l_vgpus
        ]
        if len(b) > 0
    ]
    return flatten(wow)
