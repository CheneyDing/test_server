import numpy as np
import tensorflow as tf
import datetime
import time
from test_server.test_server.tikv_prome import *
from sklearn.feature_selection import VarianceThreshold
import lightgbm as lgb
from sklearn.feature_selection import SelectFromModel
from sklearn.linear_model import LogisticRegression
import pandas as pd
from itertools import chain
from sklearn.linear_model import LassoCV
import matplotlib.pyplot as plt

minReplicas = 3
maxReplicas = 4
scaleIntervalMins = 10
averageUtilization = 4  # 4/8
correlation_threshold = 0.975
n_iterations = 50
cumulative_importance = 0.99

kk = 0
history_data = []  # 二维的list，第一维为时间，第二维为metrics种类
feature_inputs = [fetch_tikv_cpu_usage, fetch_io_utilization, fetch_disk_latency,
                  fetch_tikv_grpc_poll_cpu, fetch_io_in_bandwidth, fetch_io_out_bandwidth, fetch_grpc_duration_put,
                  fetch_grpc_duration_prewrite, fetch_grpc_duration_commit, fetch_grpc_duration_cop,
                  fetch_grpc_duration_get, fetch_grpc_duration_scan]
feature_inputs2 = [fetch_tikv_cpu_usage, fetch_tikv_grpc_poll_cpu, fetch_grpc_duration_put,
                   fetch_grpc_duration_prewrite, fetch_grpc_duration_commit, fetch_grpc_duration_cop,
                   fetch_grpc_duration_get, fetch_grpc_duration_scan]
feature_kinds = ['cpu', 'io util', 'io latency read', 'io latency write', 'grpc cpu', 'io bandwidth in',
                 'io bandwidth ', 'out', 'put', 'prewrite', 'commit', 'cop', 'get', 'scan']
feature_kinds2 = ['cpu', 'grpc cpu', 'put', 'prewrite', 'commit', 'cop', 'get', 'scan']
to_drop = {}


# 获取20份数据，每份20批
def get_train_data(batch_size, time_step, predict_step, input_size):
    train_x = np.empty([50, batch_size]).tolist()
    train_y = np.empty([50, batch_size]).tolist()
    for i in range(50):
        for j in range(batch_size):
            train_x[i][j] = []
            train_y[i][j] = []
    with open("metrics.txt", "r") as f:
        train_data = [[] for _ in range(1200)]
        j = 0
        iter = 0
        for line in f.readlines():
            line = line.strip('\n')
            train_data[iter].append(float(line))
            j += 1
            if j == input_size:
                iter += 1
                j = 0

        i = 0
        # 50个batch，一个batch内部，分别是[0,15), [1,16)..., [19,34)
        # 第二个batch开始，是[20,35),[21,26)...[39,54)
        while i < 50:
            train_num = 0
            while train_num < batch_size:
                iter = i * batch_size + train_num
                j = 0
                while j < time_step:
                    train_x[i][train_num].append(train_data[iter + j])
                    j += 1
                j = 0
                while j < predict_step:
                    train_y[i][train_num].append(train_data[iter + time_step + j][0])
                    j += 1

                train_num += 1
            i += 1

    return train_x, train_y


# 特征选择
def feature_selection(df, train_y):
    ################
    # 数据预处理，特征选择
    global to_drop
    # 去掉那些变化不大的特征
    variances = VarianceThreshold().fit(df).variances_.tolist()
    drop_variance = []
    for i in range(len(variances)):
        if variances[i] < 0.25:
            drop_variance.append(feature_kinds2[i])
    to_drop['variance'] = drop_variance

    # 计算Pearson相关系数，剔除相关性过高的特征
    coef = df.corr()
    # 提取矩阵的上三角
    upper = coef.where(np.triu(np.ones(coef.shape), k=1).astype(np.bool))
    drop_corr = [column for column in upper.columns if any(upper[column].abs() > correlation_threshold)]
    to_drop['corr'] = drop_corr

    # 使用LightGBM剔除重要性为0的特征
    features = pd.get_dummies(df)
    feature_names = list(features)
    features = np.array(features)
    labels = np.array(train_y).reshape((-1,))
    feature_importance_values = np.zeros(len(feature_names))
    for iter in range(n_iterations):
        model = lgb.LGBMClassifier(n_estimators=1000, learning_rate=0.05, verbose=-1)
        print("Start lgbm fit ", iter, " times")
        model.fit(features, labels.astype('int'))

        # 记录特征的重要性
        feature_importance_values += model.feature_importances_ / n_iterations

    feature_importances = pd.DataFrame({'feature': feature_names, 'importance': feature_importance_values})

    # 根据重要性对特征进行排序
    feature_importances = feature_importances.sort_values('importance', ascending=False).reset_index(
        drop=True)

    # 将重要性标准化
    feature_importances['normalized_importance'] = feature_importances['importance'] / feature_importances[
        'importance'].sum()
    feature_importances['cumulative_importance'] = np.cumsum(feature_importances['normalized_importance'])

    # 提取重要性为0的特征
    record_zero_importance = feature_importances[feature_importances['importance'] == 0.0]

    drop_importance_zero = list(record_zero_importance['feature'])
    to_drop['importance_zero'] = drop_importance_zero
    print("lightgbm finished.")

    # 剔除那些重要性小的特征
    feature_importances = feature_importances.sort_values('cumulative_importance')
    record_low_importance = feature_importances[feature_importances['cumulative_importance'] > cumulative_importance]
    drop_importance_low = list(record_low_importance['feature'])
    to_drop['importance_low'] = drop_importance_low

    # L1正则化
    labels = np.array(train_y).reshape((-1,))
    print("df.shape: ", df.shape)
    print("labels.shape: ", labels.shape)
    clf = LassoCV(max_iter=10000)
    clf.fit(df, labels)
    selector = SelectFromModel(estimator=clf, prefit=True)
    support = selector.get_support()
    print(support)
    drop_feature_lassocv = []
    for iter in range(len(feature_kinds2)):
        if support[iter] is False:
            drop_feature_lassocv.append(feature_kinds2[iter])
    to_drop['L1'] = drop_feature_lassocv

    print(to_drop)
    # 将上述要丢弃的特征整合，去除重复的
    features_to_drop = set(list(chain(*list(to_drop.values()))))
    features_to_drop = list(features_to_drop)

    print("Selected features.")
    return features_to_drop


# ——————————————————定义网络——————————————————
def lstm(X, weights, biases, input_size, rnn_unit, kp):
    batch_size = tf.shape(X)[0]
    time_step = tf.shape(X)[1]
    w_in = weights['in']
    b_in = biases['in']

    # 输入隐藏层
    ###########
    # (batch_size * time_step, input_size)
    input = tf.reshape(X, [-1, input_size])  # 需要将tensor转成2维进行计算，计算后的结果作为隐藏层的输入
    input_rnn = tf.matmul(input, w_in) + b_in
    # (batch_size, time_step, rnn_unit)
    input_rnn = tf.reshape(input_rnn, [-1, time_step, rnn_unit])  # 将tensor转成3维，作为lstm cell的输入
    ###########
    # cell
    ###########
    cell = tf.nn.rnn_cell.BasicLSTMCell(rnn_unit)  # reuse = sign
    init_state = cell.zero_state(batch_size, dtype=tf.float32)
    # output_rnn是记录lstm每个输出节点的结果，final_states是最后一个cell的结果
    output_rnn, final_states = tf.nn.dynamic_rnn(cell, input_rnn, initial_state=init_state, dtype=tf.float32)
    ###########
    # 输出隐藏层
    ###########
    output = tf.unstack(tf.transpose(output_rnn, [1, 0, 2]))
    results = tf.matmul(output[-1], weights['out']) + weights['out']
    results = tf.nn.dropout(results, keep_prob=kp)

    return results


# ——————————————————模型—————————————————
def train_lstm(input_size, output_size, lr, rnn_unit, weights, biases, time_step, kp, save_model_path, save_model_name,
               train_x, train_y):
    # 为None的维度表示不确定，需要在运行时决定
    X = tf.placeholder(tf.float32, shape=[None, time_step, input_size])
    Y = tf.placeholder(tf.float32, shape=[None, output_size])
    keep_prob = tf.placeholder('float')
    pred = lstm(X, weights, biases, input_size, rnn_unit, keep_prob)
    # 损失函数, 最小二乘法
    loss = tf.reduce_mean(tf.square(tf.reshape(pred, [-1, output_size]) - tf.reshape(Y, [-1, output_size])))
    train_op = tf.train.AdamOptimizer(lr).minimize(loss)

    saver = tf.train.Saver(max_to_keep=1)

    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())

        for i in range(len(train_y)):
            batch_x = train_x[i]
            batch_y = train_y[i]

            _, loss_ = sess.run([train_op, loss], feed_dict={X: batch_x, Y: batch_y, keep_prob: kp})
            print(i, loss_)

        saver.save(sess, save_model_path + save_model_name)

        # # 画图
        # fig = plt.figure()
        # ax1 = fig.add_subplot(111)
        # ax1.set_xlabel('time/min')
        # ax1.set_ylabel('cpu usage')
        # ax1.set_title('CPU')
        # # ax2 = fig.add_subplot(122)
        # # ax2.set_xlabel('time/min')
        # # ax2.set_ylabel('area')
        # # ax2.set_title('table2')
        # x = list(range(len(data)))
        # X = list(range(train_end, train_end + len(test_predict)))
        # y = [[] for i in range(output_size)]
        # Y = [[] for i in range(output_size)]
        # for i in range(output_size):
        #     y[i] = data[:, i]
        #     Y[i] = test_predict[:, i]
        # ax1.plot(x, y[0], color='b', label='real')
        # ax1.plot(X, Y[0], color='r', label='predict')
        # # ax2.plot(x, y[1], color='r', label='real')
        # # ax2.plot(X, Y[1], color='b', label='predict')
        # plt.legend()
        # plt.show()


def start_train_cpu():
    # 输入维度, cpu usage, io utilization, io latency, network bandwidth, raftstore cpu, grpc duration write/read
    # input_size = 12
    input_size = 8
    output_size = 1
    # 输出维度
    rnn_unit = 12  # 隐藏层节点
    lr = 0.004  # 学习率
    batch_size = 20  # 每次训练的一个批次的大小   30
    time_step = 15  # 前time_step步来预测下一步  20
    predict_step = 15  # 预测predict_step分钟后的负载
    kp = 1  # dropout保留节点的比例
    save_model_path = './save/predict_cpu_6-26/'  # checkpoint存在的目录
    save_model_name = 'MyModel'  # saver.save(sess, './save/MyModel') 保存模型

    train_x, train_y = get_train_data(batch_size, time_step, predict_step, input_size)
    print(np.array(train_x).shape)
    x_tmp, y_tmp = [], []

    for batch in train_x:
        x_tmp.append(batch[0])
    for batch in train_y:
        y_tmp.append(batch[0])

    # 由于每个batch内部的train_x是连续时间内的，变化不大，所以取每个batch的首个
    train_x0 = np.array(x_tmp)
    print(train_x0.shape)
    train_x0 = np.reshape(train_x0, (-1, input_size))

    train_y0 = np.array(y_tmp)
    print(train_y0.shape)
    train_y0 = np.reshape(train_y0, (-1, output_size))

    df = pd.DataFrame(train_x0.tolist(), columns=feature_kinds2)
    features_to_drop = feature_selection(df, train_y0)

    print(features_to_drop)
    train_x = np.array(train_x)
    train_x = np.reshape(train_x, (-1, input_size))
    df = pd.DataFrame(train_x.tolist(), columns=feature_kinds2)
    df.drop(columns=features_to_drop)
    train_x = df.to_numpy()
    train_x = np.reshape(train_x, (-1, batch_size, time_step, input_size - len(features_to_drop)))
    train_x = train_x.tolist()

    # ——————————————————定义神经网络变量——————————————————
    # 如果是加载已训练好的模型，w和b应该是相同的形状
    # 输入和输出的隐藏层
    weights = {
        'in': tf.Variable(tf.random_uniform([input_size, rnn_unit])),  # max_val=0.125
        'out': tf.Variable(tf.random_uniform([rnn_unit, output_size]))
    }
    biases = {
        'in': tf.Variable(tf.constant(0.1, shape=[rnn_unit, ])),
        'out': tf.Variable(tf.constant(0.1, shape=[output_size, ]))
    }
    train_lstm(input_size, output_size, lr, rnn_unit, weights, biases,
               time_step, kp, save_model_path, save_model_name, train_x, train_y)


start_train_cpu()
