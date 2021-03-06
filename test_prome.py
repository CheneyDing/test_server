from typing import Any, Callable

import requests
import time


def fetch_tikv_cpu_usage(prome_addr, start, end, step=30):
    r = requests.get(
        'http://%s/api/v1/query_range?query=sum(rate(tikv_thread_cpu_seconds_total[1m])) by (instance)&start=%s&end=%s&step=%s' % (
            prome_addr, start, end, step))
    res = r.json()
    if res['status'] == 'error':
        raise Exception(
            'an error occurred when fetching tikv cpu usage: errorType={}: {}'.format(res['errorType'], res['error']))
    return res['data']['result']


def fetch_disk_io_util(prome_addr, start, end, step=30):
    r = requests.get(
        'http://%s/api/v1/query_range?query=sum(rate(node_disk_io_time_seconds_total{job="node-exporter"'
        '}[2m])) by ( '
        'device)&start=%s&end=%s&step=%s' % (prome_addr, start, end, step))
    res = r.json()
    if res['status'] == 'error':
        raise Exception(
            'an error occurred when fetching tikv grpc poll cpu: errorType={}: {}'.format(res['errorType'],
                                                                                          res['error'])
        )
    return res['data']['result']


def fetch_tikv_disk_read_latency(prome_addr, start, end, step=30):
    r = requests.get(
        'http://%s/api/v1/query_range?query=sum(rate(node_disk_read_time_seconds_total[1m])) by (device) / sum(rate('
        'node_disk_reads_completed_total[1m])) by (device)&start=%s&end=%s&step=%s' % (prome_addr, start, end, step))
    res = r.json()
    if res['status'] == 'error':
        raise Exception(
            'an error occurred when fetching tikv disk latency: errorType={}: {}'.format(res['errorType'], res['error'])
        )
    return res['data']['result']


def fetch_tikv_disk_write_latency(prome_addr, start, end, step=30):
    r = requests.get(
        'http://%s/api/v1/query_range?query=sum(rate(node_disk_write_time_seconds_total[1m])) by (device) / '
        'sum(rate(node_disk_writes_completed_total'
        '[1m])) by (device)&start=%s&end=%s&step=%s' % (prome_addr, start, end, step))
    res = r.json()
    if res['status'] == 'error':
        raise Exception(
            'an error occurred when fetching tikv disk latency: errorType={}: {}'.format(res['errorType'], res['error'])
        )
    return res['data']['result']


def fetch_tikv_grpc_poll_cpu(prome_addr, start, end, step=30):
    r = requests.get(
        'http://%s/api/v1/query_range?query=sum(rate(tikv_thread_cpu_seconds_total{ '
        'name=~"grpc.*"}[1m])) by (instance)&start=%s&end=%s&step=%s' % (prome_addr, start, end, step))
    res = r.json()
    if res['status'] == 'error':
        raise Exception(
            'an error occurred when fetching tikv grpc poll cpu: errorType={}: {}'.format(res['errorType'], res['error'])
        )
    return res['data']['result']


def fetch_io_in_bandwidth(prome_addr, start, end, step=30):
    r = requests.get(
        'http://%s/api/v1/query_range?query=sum(rate(node_disk_read_bytes_total['
        '1m])) by (device)&start=%s&end=%s&step=%s' % (prome_addr, start, end, step))
    res = r.json()
    if res['status'] == 'error':
        raise Exception(
            'an error occurred when fetching tikv io bandwidth: errorType={}: {}'.format(res['errorType'],
                                                                                          res['error'])
        )
    return res['data']['result']


def fetch_io_out_bandwidth(prome_addr, start, end, step=30):
    r = requests.get(
        'http://%s/api/v1/query_range?query=sum(rate(node_disk_write_bytes_total['
        '1m])) by (device)&start=%s&end=%s&step=%s' % (prome_addr, start, end, step))
    res = r.json()
    if res['status'] == 'error':
        raise Exception(
            'an error occurred when fetching tikv io bandwidth: errorType={}: {}'.format(res['errorType'],
                                                                                          res['error'])
        )
    return res['data']['result']


def fetch_grpc_duration(prome_addr, start, end, step=30):
    r = requests.get(
        'http://%s/api/v1/query_range?query=sum(rate(tikv_grpc_msg_duration_seconds_sum['
        '1m])) by (type) / sum(rate(tikv_grpc_msg_duration_seconds_count[1m])) by (type)&start=%s&end=%s&step=%s' %
        (prome_addr, start, end, step))
    res = r.json()
    if res['status'] == 'error':
        raise Exception(
            'an error occurred when fetching tikv grpc duration put: errorType={}: {}'.format(res['errorType'],
                                                                                              res['error'])
        )
    return res['data']['result']


def fetch_grpc_duration_put(prome_addr, start, end, step=30):
    metrics = fetch_grpc_duration(prome_addr, start, end, step)
    put_metric = []
    for metric in metrics:
        if (metric['metric']['type'] == 'raw_batch_put') or (metric['metric']['type'] == 'raw_put'):
            put_metric.append(metric)
    return put_metric


def fetch_grpc_duration_prewrite(prome_addr, start, end, step=30):
    metrics = fetch_grpc_duration(prome_addr, start, end, step)
    prewrite_metric = []
    for metric in metrics:
        if metric['metric']['type'] == 'kv_prewrite':
            prewrite_metric.append(metric)
    return prewrite_metric


def fetch_grpc_duration_commit(prome_addr, start, end, step=30):
    metrics = fetch_grpc_duration(prome_addr, start, end, step)
    commit_metric = []
    for metric in metrics:
        if metric['metric']['type'] == 'kv_commit':
            commit_metric.append(metric)
    return commit_metric


def fetch_grpc_duration_cop(prome_addr, start, end, step=30):
    metrics = fetch_grpc_duration(prome_addr, start, end, step)
    cop_metric = []
    for metric in metrics:
        if metric['metric']['type'] == 'coprocessor' or metric['metric']['type'] == 'coprocessor_stream':
            cop_metric.append(metric)
    return cop_metric


def fetch_grpc_duration_get(prome_addr, start, end, step=30):
    metrics = fetch_grpc_duration(prome_addr, start, end, step)
    get_metric = []
    for metric in metrics:
        if 'get' in metric['metric']['type']:
            get_metric.append(metric)
    return get_metric


def fetch_grpc_duration_scan(prome_addr, start, end, step=30):
    metrics = fetch_grpc_duration(prome_addr, start, end, step)
    scan_metric = []
    for metric in metrics:
        if 'scan' in metric['metric']['type']:
            scan_metric.append(metric)
    return scan_metric


prome_addr = '10.233.18.170:9090'
start = str(int(time.time()))
end = str(int(time.time()))
step = 60
cpudata = fetch_tikv_cpu_usage(prome_addr, start, end, step)
print("cpudata: ", cpudata)
io_util = fetch_disk_io_util(prome_addr, start, end, step)
print("io_util: ", io_util)
read_latency = fetch_tikv_disk_read_latency(prome_addr, start, end, step)
print("read_latency: ", read_latency)
write_latency = fetch_tikv_disk_write_latency(prome_addr, start, end, step)
print("write_latency: ", write_latency)
grpcdata = fetch_tikv_grpc_poll_cpu(prome_addr, start, end, step)
print("grpcdata: ", grpcdata)
io_in = fetch_io_in_bandwidth(prome_addr, start, end, step)
print("io_in: ", io_in)
io_out = fetch_io_out_bandwidth(prome_addr, start, end, step)
print("io_out: ", io_out)
grpc_duration_put = fetch_grpc_duration_put(prome_addr, start, end, step)
print("grpc_duration_put: ", grpc_duration_put)
grpc_duration_prewrite = fetch_grpc_duration_prewrite(prome_addr, start, end, step)
print("grpc_duration_prewrite: ", grpc_duration_prewrite)
grpc_duration_commit = fetch_grpc_duration_commit(prome_addr, start, end, step)
print("grpc_duration_commit: ", grpc_duration_commit)
grpc_duration_cop = fetch_grpc_duration_cop(prome_addr, start, end, step)
print("grpc_duration_cop: ", grpc_duration_cop)
grpc_duration_get = fetch_grpc_duration_get(prome_addr, start, end, step)
print("grpc_duration_get: ", grpc_duration_get)
grpc_duration_scan = fetch_grpc_duration_scan(prome_addr, start, end, step)
print("grpc_duration_scan: ", grpc_duration_scan)
