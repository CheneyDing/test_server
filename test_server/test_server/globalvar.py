class GlobalVar:
    predict_regions = {
        'time': 0,
        'predict_step': 0,
        'history_r2_score_total': 0,
        'table_num': 0,
        'table_info': [],
        # 'history_r2_score': [],
        # 'maxvalue': [],
        # 'minvalue': [],
        # 'key_range':[],
        # 'predict': []
    }
    predict_tikv_replicas = {
        'name': "",
        'namespace': "",
        'type': "tikv",
        'recommendedReplicas': 1,
    }
    predict_tidb_replicas = {
        'name': "",
        'namespace': "",
        'type': "tidb",
        'recommendedReplicas': 1,
    }

# def set_demo_value(value):
    # gloVar.data = value
# def get_demo_value():
    # return gloVar.data


def get_regions():
    return GlobalVar.predict_regions


def get_tikv_replicas():
    return GlobalVar.predict_tikv_replicas


def get_tidb_replicas():
    return GlobalVar.predict_tidb_replicas
