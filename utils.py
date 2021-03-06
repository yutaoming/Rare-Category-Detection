from load_data import load_data_blog, load_data_cora, sparse_mx_to_torch_sparse_tensor
import numpy as np
import torch
import random
from sklearn.metrics import roc_auc_score, f1_score
import torch.nn.functional as F
import scipy.sparse as sp
from scipy.io import loadmat

# cora 用
# c_train_num是一个数组，用于记录每个类有多少个节点用于训练
def split_arti(labels, c_train_num):
    # labels: n-dim Longtensor, each element in [0,...,m-1].
    # cora: m=7
    num_classes = len(set(labels.tolist()))
    class_masks = []  # class-wise index
    train_mask = []
    val_mask = []
    test_mask = []
    # 候选集
    candidate_mask = []
    # 再额外加一列imbalance ratio
    c_num_mat = np.zeros((num_classes, 4)).astype(int)
    imbalance_ratio = np.zeros((num_classes, 1)).astype(float)
    # 每个类有25个节点用于验证集
    c_num_mat[:, 1] = 25
    # 每个类用55个节点用于测试集
    c_num_mat[:, 2] = 55

    num_max = 0
    for i in range(num_classes):
        # 得到i的索引
        class_mask = (labels == i).nonzero()[:, -1].tolist()
        # print('{:d}-th class sample number: {:d}'.format(i,len(class_mask)))
        random.shuffle(class_mask)
        class_masks.append(class_mask)

        train_mask = train_mask + class_mask[:c_train_num[i]]
        c_num_mat[i, 0] = c_train_num[i]

        val_mask = val_mask + class_mask[c_train_num[i]:c_train_num[i]+25]
        test_mask = test_mask + class_mask[c_train_num[i]+25:c_train_num[i]+80]
        candidate_mask = candidate_mask + class_mask[c_train_num[i]+80:]
        c_num_mat[i, 3] = len(class_mask[c_train_num[i]+80:])
        if(num_max < len(class_mask)):
            num_max = len(class_mask)
    for i in range(num_classes):
        class_mask = (labels == i).nonzero()[:, -1].tolist()
        imbalance_ratio[i, 0] = len(class_mask)/float(num_max)

    random.shuffle(train_mask)

    # list -> numpy -> tensor
    train_mask = np.array(train_mask)
    train_mask = torch.from_numpy(train_mask)

    val_mask = np.array(val_mask)
    val_mask = torch.from_numpy(val_mask)

    test_mask = np.array(test_mask)
    test_mask = torch.from_numpy(test_mask)

    candidate_mask = np.array(candidate_mask)
    candidate_mask = torch.from_numpy(candidate_mask)

    c_num_mat = np.array(c_num_mat)
    c_num_mat = torch.from_numpy(c_num_mat)
    # c_num_mat = torch.LongTensor(c_num_mat)
    imbalance_ratio = np.array(imbalance_ratio)
    imbalance_ratio = torch.from_numpy(imbalance_ratio)
    
    return train_mask, val_mask, test_mask, candidate_mask, c_num_mat, imbalance_ratio


# 如何随机生成 训练集 测试集？
# 对所有类做如下操作：
# 先获得当前类的
# 只要把数组随机排序，然后按比例切片即可
# for blog
def split_mask(labels):
    """用于生成trian_mask, val_mask, test_mask"""
    # labels: n-dim Longtensor, each element in [0,...,m-1].
    num_classes = len(set(labels.tolist()))
    # num_classes = 38
    # 对应class的索引
    class_masks = []
    train_mask = []
    val_mask = []
    test_mask = []
    candidate_mask = []
    # 生成一个num_classes * 3 的ndarray
    # 用来记录各个类 train val test candidate的数量 0.1, 0.1, 0.5, 0.3
    # TODO：适当下调train的比例比如只用0.05(使训练集尽可能的优质), 这里可以增加一个指标imbalance radio，以最多的类为基准
    # TODO：e.g. 最多的类的数量为1000，有两个稀有类一个是100，一个是200，稀有类程度就是0.1和0.2。这里可以选择稀有类就按1-imbalance radio
    # TODO：的比例来
    c_num_mat = np.zeros((num_classes, 4)).astype(int)
    imbalance_ratio = np.zeros((num_classes, 1)).astype(float)
    # 0是false 0以外是true
    num_max = 0
    for i in range(num_classes):
        # class_mask是某个类的索引
        class_mask = (labels == i).nonzero()[:, -1].tolist()
        class_num = len(class_mask)
        # print('{:d}-th class sample number: {:d}'.format(i,len(class_mask)))
        # shuffle 把一个数组打乱重新排序 就像是洗牌
        random.shuffle(class_mask)
        class_masks.append(class_mask)

        if class_num < 4:
            if class_num < 3:
                print("too small class type")
                # 一般不会执行到这步，除非某个类的数量小于3
                # ipdb.set_trace()
            c_num_mat[i, 0] = 1
            c_num_mat[i, 1] = 0
            c_num_mat[i, 2] = 1
            c_num_mat[i, 3] = 1
        else:
            c_num_mat[i, 0] = int(class_num * 0.1)
            c_num_mat[i, 1] = int(class_num * 0.1)
            c_num_mat[i, 2] = int(class_num * 0.5)
            c_num_mat[i, 3] = int(class_num * 0.3)

        train_mask += class_mask[:c_num_mat[i, 0]]
        val_mask += class_mask[c_num_mat[i, 0]:c_num_mat[i, 0] + c_num_mat[i, 1]]
        test_mask += class_mask[c_num_mat[i, 0] + c_num_mat[i, 1]:c_num_mat[i, 0] + c_num_mat[i, 1] + c_num_mat[i, 2]]
        candidate_mask += class_mask[c_num_mat[i, 0] + c_num_mat[i, 1] + c_num_mat[i, 2]:]
        if (num_max < len(class_mask)):
            num_max = len(class_mask)
    for i in range(num_classes):
        class_mask = (labels == i).nonzero()[:, -1].tolist()
        imbalance_ratio[i, 0] = len(class_mask)/float(num_max)

    # 避免出现相同的类连在一起的情况
    random.shuffle(train_mask)
    # list -> numpy -> tensor
    train_mask = np.array(train_mask)
    train_mask = torch.from_numpy(train_mask)

    val_mask = np.array(val_mask)
    val_mask = torch.from_numpy(val_mask)

    test_mask = np.array(test_mask)
    test_mask = torch.from_numpy(test_mask)

    candidate_mask = np.array(candidate_mask)
    candidate_mask = torch.from_numpy(candidate_mask)

    c_num_mat = np.array(c_num_mat)
    c_num_mat = torch.from_numpy(c_num_mat)
    # 只有train_mask顺序是乱的，val_mask，test_mask会按照类别的顺序
    imbalance_ratio = np.array(imbalance_ratio)
    imbalance_ratio = torch.from_numpy(imbalance_ratio)

    return train_mask, val_mask, test_mask, candidate_mask, c_num_mat, imbalance_ratio


# evaluation function
# 一共三个指标
# 第一个是 ACC 计算测试集的accuracy 因为稀有类只是少数，所以不够准确
# 第二个是 AUC-ROC 对每个类都求 然后取平均值
# 第三个是 F1 综合了precision和recall 同样是对每个类都求，然后取平均
def print_evaluation_metrics(output, labels, pre='valid'):
    # class_num_list: 一个记录类数目的列表
    pre_num = 0
    # print class-wise performance
    # 如果添加以下代码，请把class_num_list添加到函数参数列表中
    # for i in range(labels.max()+1):
    #     # 如果labels[mask]，那么label则会按照索引的顺序来 而不是labels自带的顺序
    #     cur_tpr = accuracy(output[pre_num:pre_num+class_num_list[i]], labels[pre_num:pre_num+class_num_list[i]])
    #     print(str(pre)+" class {:d} True Positive Rate: {:.3f}".format(i, cur_tpr.item()))
    #
    #     index_negative = labels != i
    #     # 生成一个全是i的labels
    #     labels_negative = labels.new(labels.shape).fill_(i)
    #     # output[index_negative, :] 预测不是i类的
    #     cur_fpr = accuracy(output[index_negative, :], labels_negative[index_negative])
    #     print(str(pre)+" class {:d} False Positive Rate: {:.3f}".format(i, cur_fpr.item()))
    #
    #     pre_num = pre_num + class_num_list[i]

    # ipdb.set_trace()
    if labels.max() > 1:
        auc_score = roc_auc_score(labels.detach(), F.softmax(output, dim=-1).detach(), average='macro',
                                  multi_class='ovr')
    else:
        auc_score = roc_auc_score(labels.detach(), F.softmax(output, dim=-1)[:, 1].detach(), average='macro')

    macro_F = f1_score(labels.detach(), torch.argmax(output, dim=-1).detach(), average='macro')
    print(str(pre) + ' current auc-roc score: {:f}, current macro_F score: {:f}'.format(auc_score, macro_F))

    return


def accuracy(output, labels):
    # max(1)是返回每一行最大值组成的一维数组
    # [0]是最大值；[1]是最大值的索引
    preds = output.max(1)[1].type_as(labels)
    correct = preds.eq(labels).double()
    correct = correct.sum()
    return correct / len(labels)


def get_degree_cora():
    # 得到节点的度
    # 返回一个2708 * 1的张量
    path = "/Users/yutaoming/PycharmProjects/Rare-Category-Detection/data/cora/"
    dataset = "cora"
    idx_features_labels = np.genfromtxt("{}{}.content".format(path, dataset),
                                        dtype=np.dtype(str))

    labels = idx_features_labels[:, -1]
    classes_dict = {'Neural_Networks': 0, 'Reinforcement_Learning': 1, 'Probabilistic_Methods': 2, 'Case_Based': 3,
                    'Theory': 4, 'Rule_Learning': 5, 'Genetic_Algorithms': 6}
    labels = np.array(list(map(classes_dict.get, labels)))

    # build graph
    idx = np.array(idx_features_labels[:, 0], dtype=np.int32)
    idx_map = {j: i for i, j in enumerate(idx)}
    edges_unordered = np.genfromtxt("{}{}.cites".format(path, dataset),
                                    dtype=np.int32)
    edges = np.array(list(map(idx_map.get, edges_unordered.flatten())),
                     dtype=np.int32).reshape(edges_unordered.shape)
    # Constructing a matrix with duplicate indices
    # row = np.array([0, 0, 1, 3, 1, 0, 0])
    # col = np.array([0, 2, 1, 3, 1, 0, 0])
    # data = np.array([1, 1, 1, 1, 1, 1, 1])
    # coo = coo_matrix((data, (row, col)), shape=(4, 4))
    # Duplicate indices are maintained until implicitly or explicitly summed
    # np.max(coo.data)
    #
    # coo.toarray()
    # array([[3, 0, 1, 0],
    #        [0, 2, 0, 0],
    #        [0, 0, 0, 0],
    #        [0, 0, 0, 1]])
    adj = sp.coo_matrix((np.ones(edges.shape[0]), (edges[:, 0], edges[:, 1])),
                        shape=(labels.shape[0], labels.shape[0]),
                        dtype=np.float32)
    adj = adj.tocoo().astype(np.float32)
    indices = torch.from_numpy(np.vstack((adj.row, adj.col)).astype(np.int64))
    # cora 数据集一条边只算了一次 indices.shape = [2, 2708]
    degrees = [0] * 2708
    for i in range(indices.shape[0]):
        for j in range(indices.shape[1]):
            degrees[indices[i][j]] += 1

    degrees = torch.tensor(degrees, dtype=int)
    return degrees


def get_degree_blog():
    mat = loadmat('/Users/yutaoming/PycharmProjects/Rare-Category-Detection/data/BlogCatalog/blogcatalog.mat')
    adj = mat['network']
    adj = adj.tocoo().astype(np.float32)
    indices = torch.from_numpy(np.vstack((adj.row, adj.col)).astype(np.int64))
    print(indices.shape)
    # 10312是blog的节点数
    degrees = [0] * 10312
    for i in range(indices.shape[0]):
        for j in range(indices.shape[1]):
            degrees[indices[i][j]] += 1
    # blog 数据集一条边被算了两次 indices.shape = [2, 667966]
    # 所以这里需要除以2
    for i in range(10312):
        degrees[i] /= 2

    degrees = torch.tensor(degrees, dtype=int)
    return degrees


def main():
    adj, features, labels = load_data_blog()
    train_mask, val_mask, test_mask, candidate_mask, c_num_mat, imbalance_ratio = split_mask(labels)
    print(imbalance_ratio)


if __name__ == '__main__':
    main()