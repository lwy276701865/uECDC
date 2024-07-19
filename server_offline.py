from parameters import number_of_hashes, bin_capacity, alpha, plain_modulus,slice_number,VBF_hash_seeds,omega,cuckoo_hash_seeds,output_bits,dummy_msg_server
from simple_hash import Simple_hash
from auxiliary_functions import coeffs_from_roots,split_integers_unique_first_block,split_string_into_n_parts,cal_polycoeef_pax
from oprf import server_prf_offline_parallel, order_of_generator, G
from time import time
from hashlib import blake2b
from bitarray import bitarray
from math import ceil,log2
from multiprocessing import Pool
import numpy as np
import pickle,rrokvs,mmh3
from functools import partial
#server's PRF secret key
oprf_server_key = 1234567891011121314151617181920
table_size=2**output_bits
# key * generator of elliptic curve
server_point_precomputed = (oprf_server_key % order_of_generator) * G

server_set = []
with open('server_set.csv', 'r') as f:
    lines = f.readlines()
    for line in lines:
        item,label=line[:-1].split(",")
        binary_item = bin(int(item))[2:]
        binary_label = bin(int(label))[2:]
        for i in range(len(binary_label)):
            # 拼接binary_item的二进制字符串和binary_label的当前位  
            binary_item = binary_item + binary_label[i]  
            # 将拼接后的二进制字符串转换回十进制  
            decimal_value = int(binary_item, 2)  
            # 将十进制值添加到结果数组中  
            server_set.append(decimal_value)  

t0 = time()
#The PRF function is applied on the set of the server, using parallel computation
PRFed_server_set = server_prf_offline_parallel(server_set, server_point_precomputed)
PRFed_server_set = set(PRFed_server_set)
t1 = time()
print("OPRF结束，花费时间为：{:.2f}s".format(t1 - t0))

minibin_capacity = int(bin_capacity / alpha)
#VBF编码
VBF_PRFed_server_set=set()
# VBF_PRF_link={} #将数据与VBF编码建立关系，方便定位数据
for item in PRFed_server_set:
    # VBF_PRF_link[item]=[mmh3.hash(str(item), VBF_hash_seeds[i], signed=False) for i in range(2)]
    for i in range(2):
        # VBF_PRFed_server_set.add(int(blake2b(item.encode('utf-8'),digest_size=6,person=VBF_hash_seeds[i]).hexdigest(),16)>>2)#为了得到46位长度的输出
        VBF_PRFed_server_set.add(mmh3.hash(str(item), VBF_hash_seeds[i], signed=False))
# The OPRF-processed database entries are simple hashed
SH = Simple_hash(cuckoo_hash_seeds)
# for item_list in list(VBF_PRF_link.values()): #item_list=[]
#     for item in item_list:
#         for i in range(number_of_hashes): #range(3)=[0,1,2]
#             SH.insert(item, i)
for item in VBF_PRFed_server_set:
    for i in range(number_of_hashes): #range(3)=[0,1,2]
        SH.insert(item, i)
# simple_hashed_data is padded with dummy_msg_server
for i in range(table_size):
    for j in range(bin_capacity):
        if SH.simple_hashed_data[i][j] == None:
            SH.simple_hashed_data[i][j] = dummy_msg_server

# Here we perform the partitioning:
# Namely, we partition each bin into alpha minibins with B/alpha items each
# We represent each minibin as the coefficients of a polynomial of degree B/alpha that vanishes in all the entries of the mininbin
# Therefore, each minibin will be represented by B/alpha + 1 coefficients; notice that the leading coeff = 1
# 分区之后我们会切分每一个子桶中的每个元素，将一个元素切为多个小的数据分片，并将他们链接起来
t2 = time()
print("构造simple哈希表结束，花费时间为：{:.2f}s".format(t2 - t1))
poly_coeffs = []
link_slice_matrix={}
number_of_processes = 2
arr = np.arange(table_size)  
bin_array = np.array_split(arr, number_of_processes)
bin_lists = [list(bin) for bin in bin_array]
outputs=[]
partial_func = partial(cal_polycoeef_pax, SH=SH)  
with Pool(number_of_processes) as p:
    outputs = p.map(partial_func, bin_lists)
for output in outputs:
    poly_coeffs+=output[0]
    link_slice_matrix.update(output[1])
t3 = time()
data_to_save = (poly_coeffs,link_slice_matrix)
with open('server_preprocessed.pkl', 'wb') as f:
    pickle.dump(data_to_save, f)
t4 = time()
#print('OPRF preprocessing time {:.2f}s'.format(t1 - t0))
#print('Hashing time {:.2f}s'.format(t2 - t1))
#print('Poly coefficients from roots time {:.2f}s'.format(t3 - t2))
print('polynomial and okvs time {:.2f}s'.format(t3 - t2))
print('write file time {:.2f}s'.format(t4 - t3))
print('Server OFFLINE time {:.2f}s'.format(t4 - t0))
